import os
import subprocess
import tempfile

from repserve.path import path

# archs is a list of architectures
# components is a list
# updaterules is a list, and should normally start with a '-'
# to invoke reprepro's magic delete rule
# version should be a string
# **kw is ignored
def make_dist_stanza_lines(codename, archs, components,
                     suite=None, version=None, origin=None, label=None,
                     description=None, updaterules=[], signwith=None,
                     log=None, **kw):
    lines = []
    if origin is not None:
        lines.append('Origin: %s' % origin)
    if label is not None:
        lines.append('Label: %s' % label)
    if suite is not None:
        lines.append('Suite: %s' % suite)
    if version is not None:
        lines.append('Version: %s' % version)
    lines.append('Codename: %s' % codename)
    lines.append('Architectures: %s' % ' '.join(archs))
    lines.append('Components: %s' % ' '.join(components))
    if description is not None:
        lines.append('Description: %s' % description)
    if log is not None:
        lines.append('Log: %s' % log)
    if updaterules:
        lines.append('Update: %s' % ' '.join(updaterules))
    if signwith is not None:
        lines.append('SignWith: %s' % signwith)
    return lines

def make_update_stanza_lines(name, method, components,
                             archs, verify=None, ignore=False, filterlist_cmd='deinstall',
                             filterlist=[], listhook=None, fallback=None, **kw):
    lines = []
    lines.append('Name: %s' % name)
    lines.append('Method: %s' % method)
    if fallback is not None:
        lines.append('Fallback: %s' % fallback)
    if ignore:
        lines.append('IgnoreRelease: yes')
    if verify is not None:
        lines.append('VerifyRelease: %s' % verify)
    lines.append('Architectures: %s' % ' '.join(archs))
    lines.append('Components: %s' % ' '.join(components))
    if filterlist:
        items = [filterlist_cmd] + filterlist
        lines.append('FilterList: %s' % ' '.join(items))
    if listhook is not None:
        lines.append('ListHook: %s' % listhook)
    return lines


# This class was split from the RepRepRo class
# because it was getting large.  This class helps
# prepare and update the config files for the reprepro
# backend.
class RepRepConfig(object):
    def __init__(self, config):
        self.config = config
        
    def _get_repdirs(self, option):
        dirs = []
        for section in self.config.sections():
            cdir = self.config.get(section, option)
            if cdir not in dirs:
                dirs.append(cdir)
        return dirs
    
    def _get_confdirs(self):
        return self._get_repdirs('confdir')

    def _get_basedirs(self):
        return self._get_repdirs('basedir')
        
    def _generate_config(self, section):
        # get required options
        codename = self.config.get(section, 'codename')
        components = self.config.getlist(section, 'components')
        archs = self.config.getlist(section, 'archs')
        method = self.config.get(section, 'method')
        # get optional options
        optional_options = ['suite', 'version', 'origin',
                            'label', 'description', 'signwith',
                            'log', 'verify', 'listhook', 'fallback']
        optdict = {}.fromkeys(optional_options)
        for opt in optdict:
            if self.config.has_option(section, opt):
                optdict[opt] = self.config.get(section, opt)
        # options unhandled so far:
        # updaterules for dist stanza (use name of section)
        optdict['updaterules'] = ['-', section]
        # ignore, filterlist_cmd, and filterlist for update stanza
        optdict['ignore'] = False
        if self.config.has_option(section, 'ignore_release'):
            optdict['ignore'] = self.config.getboolean(section, 'ignore_release')
        filterlist_cmd = 'deinstall'
        if self.config.has_option(section, 'filterlist_cmd'):
            filterlist_cmd = self.config.get(section, 'filterlist_cmd')
        optdict['filterlist_cmd'] = filterlist_cmd
        if self.config.has_option(section, 'filterlist'):
            flists = self.config.getlist(section, 'filterlist')
        optdict['filterlist'] = flists
        distlines = make_dist_stanza_lines(codename, archs, components,
                                           **optdict)
        # still need to figure out what to do about filterlist
        updatelines = make_update_stanza_lines(section, method, components,
                                               archs, **optdict)
        return distlines, updatelines

    # this is for sections in the config file that share
    # the same reprepro confdir
    def _generate_section_configs(self, sections):
        distlines = []
        updatelines = []
        for section in sections:
            newdist, newupdate = self._generate_config(section)
            if distlines:
                distlines.append('')
            distlines += newdist
            if updatelines:
                updatelines.append('')
            updatelines += newupdate
        return distlines, updatelines

    # use these comment lines to separate the repserve
    # generated config from the locally modified sections
    def _comment_lines(self):
        lines = ["# WARNING: don't remove these comments",
                 "# Add your specific configuration below",
                 ''
                 ]
        return lines

    def _update_configfile(self, filename, lines):
        configfile = path(filename)
        origlines = configfile.lines()
        marker = self._comment_lines()[0]
        line = origlines.pop(0)
        while not line.startswith(marker):
            line = origlines.pop(0)
        all_lines = lines + ['', line] + origlines
        configfile.write_lines(all_lines)
        
        
    def _new_configfile(self, filename, lines):
        configfile = path(filename)
        all_lines = lines + [''] + self._comment_lines()
        configfile.write_lines(all_lines)
        
    def _write_config(self, confdir, distlines, updatelines):
        confdir = path(confdir)
        distfile = confdir / 'distributions'
        updatesfile = confdir / 'updates'
        if not distfile.isfile():
            print "creating new distributions file: %s" % distfile
            self._new_configfile(distfile, distlines)
        else:
            self._update_configfile(distfile, distlines)
        if not updatesfile.isfile():
            print "creating new updates file: %s" % updatesfile
            self._new_configfile(updatesfile, updatelines)
        else:
            self._update_configfile(updatesfile, updatelines)
            
    def create_config(self):
        basedirs = self._get_basedirs()
        for basedir in basedirs:
            bd = path(basedir)
            if not bd.isdir():
                bd.makedirs()
        confdirs = self._get_confdirs()
        for confdir in confdirs:
            cfd = path(confdir)
            if not cfd.isdir():
                cfd.makedirs()
        # handling too many confdirs is irritating
        # the commented line below uses the same list
        # for all the keys.  This is not immediately apparent
        # and was the cause of much confusion.
        #confdir_map = dict().fromkeys(confdirs, [])
        confdir_map = dict().fromkeys(confdirs)
        # use another method to initialize the dictionary
        # with *separate* empty lists
        for confdir in confdir_map:
            confdir_map[confdir] = []
        for section in self.config.sections():
            confdir = self.config.get(section, 'confdir')
            confdir_map[confdir].append(section)
        for confdir in confdir_map:
            sections = confdir_map[confdir]
            distlines, updatelines = self._generate_section_configs(sections)
            self._write_config(confdir, distlines, updatelines)
            
        
        
class RepRepRo(object):
    def __init__(self, config):
        self.config = config
        self.rconfig = RepRepConfig(self.config)

    def _get_dir_opts(self, section):
        if section is None:
            section = 'DEFAULT'
        opts = []
        for opt in ['basedir', 'outdir', 'confdir', 'distdir',
                    'logdir', 'dbdir', 'listdir']:
            opts.append('--%s' % opt)
            optdir = self.config.get(section, opt)
            opts.append(optdir)
        return opts

    def _build_command(self, section, options, command, *args):
        diropts = self._get_dir_opts(section)
        return ['reprepro'] + diropts + [command] + list(args)
        
    def _run_command(self, command):
        subprocess.check_call(command)

    def _runcmd(self, command, section, options):
        cmd = self._build_command(section, options, command)
        self._run_command(cmd)
        
    def update(self, section, options=[]):
        self._runcmd('update', section, options)

    def export(self, section, options=[]):
        self._runcmd('export', section, options)

    def createsymlinks(self, section, options=[]):
        self._runcmd('createsymlinks', section, options)

    def checkupdate(self, section, options=[]):
        cmd = self._build_command(section, options, 'checkupdate')
        outfile = tempfile.TemporaryFile()
        proc = subprocess.Popen(cmd, stdout=outfile)
        retval = proc.wait()
        if retval:
            raise RuntimeError , "%s returned %d" % (' '.join(cmd), retval)
        outfile.seek(0)
        return outfile

    
        


            
    
if __name__ == '__main__':
    pass


     
