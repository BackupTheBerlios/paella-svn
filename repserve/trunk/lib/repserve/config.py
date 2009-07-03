from ConfigParser import ConfigParser
from StringIO import StringIO

from repserve.base import parse_sources_list
from repserve.base import Url
from repserve.base import retrieve_and_parse_release_file
from repserve.path import path

DEFAULT_CONFIG = """# default config file for repserve
[DEFAULT]
# This is the parent directory for all
# repositories.  It's used when generating
# the default configuration, but isn't
# required.
reprepro_parent_dir: /var/lib/repserve/repos-db
# This is the parent directory for the
# public facing of the repositories
reprepro_parent_outdir: /var/www/repserve
# These options correspond to the
# reprepro options
basedir: %(reprepro_parent_dir)s/debian
outdir:  %(reprepro_parent_outdir)s/debian
confdir: %(basedir)s/conf
distdir: %(outdir)s/dists
logdir:  %(basedir)s/logs
dbdir:   %(basedir)s/db
listdir: %(basedir)s/lists

# The full name of the repserve user
fullname:  Automated Repository Manager
# email account of repserve user
# if left blank, it defaults to
# repserve@`cat /etc/mailname`
email:


# example
#[lenny]
#codename: lenny
#components: main contrib non-free
#archs:  amd64 source
#ignore_release:  True
#method:  http://ftp.us.debian.org/debian

"""

class BaseConfig(ConfigParser):
    # allow for uppercase options
    optionxform = str
    
    def __init__(self):
        ConfigParser.__init__(self)
        filename = '/etc/apt/repserve.conf'
        
    def getlist(self, section, option, sep=' '):
        value = self.get(section, option)
        return [p.strip() for p in value.split(sep)]

    def setlist(self, section, option, vlist, sep=' '):
        value = sep.join(vlist)
        self.set(section, option, value)
        
    def getUrl(self, section, option):
        return Url(self.get(section, option))

    def getpath(self, section, option):
        return path(self.get(section, option))

    def write_file(self):
        if not hasattr(self, 'configfilename'):
            raise RuntimeError , "The config file hasn't been set yet."
        self.write(file(self.configfilename, 'w'))
        

class RepserveConfig(BaseConfig):
    def add_filterlist_to_section(self, name, section):
        filterlists = self.getlist(section, 'filterlist')
        if name not in filterlists:
            filterlists.append(name)
            self.setlist(section, 'filterlist', filterlists)
        else:
            print "%s already in filterlists for section %s" % (name, section)
            

    def remove_filterlist_from_section(self, name, section):
        filterlists = self.getlist(section, 'filterlist')
        if name in filterlists:
            index = filterlists.index(name)
            ignore = filterlists.pop(index)
            self.setlist(section, 'filterlist', filterlists)
        else:
            print "%s not in filterlists for section %s" % (name, section)

    def get_filterlist_names(self, section):
        return self.getlist(section, 'filterlist')
    
            
    def search_for_filterlist(self, name):
        sections_containing_filterlist = []
        for section in self.sections():
            names = self.get_filterlist_names(section)
            if name in names:
                sections_containing_filterlist.append(section)
        return sections_containing_filterlist

    def get_confdir(self, section):
        return self.getpath(section, 'confdir')
    
    
# Here is an attempt to make better
# names for the sections in the config.
# At the moment, the uri is an integer
# and just makes repos1, repos2, etc.
# It is hoped that this function will parse
# the uri and assign a better name in the
# future, such as "debian", "security",
# "backports", or similar.
# index should be a unique integer
# so we can make a distinct name, in
# case we fail to make a guess.
def guess_name_for_uri(uri, index=None):
    print "Guessing name for", uri
    if uri.host == 'volatile.debian.org':
        return 'volatile'
    elif uri.host == 'security.debian.org':
        return 'security'
    elif 'debian-multimedia.org' in uri.host:
        return 'multimedia'
    elif 'backports.org' in uri.host:
        return 'backports'
    elif uri.host.endswith('debian.org'):
        return 'debian'
    # this hack is for the mirror that I use
    # but we should maybe look at netselect-apt
    # and download the complete mirror list and
    # make a guess based on that list
    elif uri.host == 'debian.mirrors.tds.net':
        return 'debian'
    else:
        return 'repos%d' % index

###################################
# Helper functions for sources_to_config function
###################################

def create_methods_dictionary(parsed_sources):
    # make a separate repository for each different
    # upstream uri
    methods = dict()
    for source in parsed_sources:
        uri = source['uri']
        # ignore file and cdrom methods
        if uri.protocol != 'file' and not uri.startswith('cdrom:'):
            if uri not in methods:
                methods[uri] = [source]
            else:
                methods[uri].append(source)
        else:
            print "Ignoring file: methods ->", str(uri)
    return methods

def create_names_dictionary(methods):
    # now we assign a name for each
    # uri.  Each uri will have it's own
    # basedir, and the section names
    # will be name-dist
    names = dict()
    index = 0
    for uri in methods:
        index += 1
        names[uri] = guess_name_for_uri(uri, index=index)
    return names

def handle_section(config, section, names, uri):
    if section not in config.sections():
        config.add_section(section)
        # create basedir option
        prefix = '%(reprepro_parent_dir)s'
        basedir = '%s/%s' % (prefix, names[uri])
        config.set(section, 'basedir', basedir)
        # create outdir option
        prefix = '%(reprepro_parent_outdir)s'
        outdir = '%s/%s' % (prefix, names[uri])
        config.set(section, 'outdir', outdir)
        
        
def handle_codename(config, section, dist):
    if config.has_option(section, 'codename'):
        cdist = config.get(section, 'codename')
        if cdist != dist:
            raise RuntimeError , "The dist values don't match %s,%s" % (cdist , dist)
    else:
        config.set(section, 'codename', dist)

def handle_archs(config, section, source):
    if config.has_option(section, 'archs'):
        archs = config.getlist(section, 'archs')
        arch = source['arch']
        #print "arch in source is" , arch
        #print "archs in config is", archs
        if arch in archs:
            print "%s already in arch option for %s" % (arch, section)
        else:
            archs.append(arch)
            config.setlist(section, 'archs', archs)
    else:
        config.setlist(section, 'archs', [source['arch']])

def handle_components(config, section, source):
    if config.has_option(section, 'components'):
        components = config.getlist(section, 'components')
        new_component = False
        for component in source['components']:
            if component not in components:
                print "adding new component", component, "to", section
                components.append(component)
                new_component = True
        if new_component:
            config.setlist(section, 'components', components)
    else:
        config.setlist(section, 'components', source['components'])

def handle_release(config, section, source):
    uri = source['uri']
    dist = source['dist']
    if section in config.ReleaseFiles:
        release = config.ReleaseFiles[section]
        print "Release already here for", section
    else:
        release = retrieve_and_parse_release_file(uri, dist)
        config.ReleaseFiles[section] = release
    for option in ['origin', 'description', 'label',
                   'suite', 'version']:
        if option in release:
            value = release[option]
            config.set(section, option, value)
            
        
###################################
# end of helper functions
###################################


# arguments
# -------------
# filename: Name of the file that contains the sources.list
# arch:  The arch that the "deb" lines specify
# output:  The file name of the generated config file
# input:  The file name of a previously generated config file (for
#            adding extra sources, or extra archs).  If None, we use
#            DEFAULT_CONFIG as a skeleton.
#            input and output can be the same file, which will overwrite
#            the previous config with the updated config.
# use_upstream_release: if True, we set the optional options in
#                                       the config file from the upstream Release
#                                       file.
# config: a previously instantiated config object ; If config is not
#             None, it will be used, and the input argument will be
#             ignored.
def sources_to_config(filename='/etc/apt/sources.list', arch=None,
                      output='repserve.conf', input=None,
                      use_upstream_release=True, config=None):
    parsed_sources = parse_sources_list(filename=filename, arch=arch)
    if config is None:
        config = BaseConfig()
        # initialize config with default skeleton
        if input is None:
            infile = StringIO(DEFAULT_CONFIG)
        else:
            infile = file(input)
        config.readfp(infile)
    else:
        #print "using previous config object"
        #print config.ReleaseFiles.keys()
        pass
    # use ReleaseFiles attribute to help
    # keep from retrieving the same Release
    # files over and over again
    if not hasattr(config, 'ReleaseFiles'):
        config.ReleaseFiles = dict()
    methods = create_methods_dictionary(parsed_sources)
    names = create_names_dictionary(methods)
    parent_dir = config.get('DEFAULT', 'reprepro_parent_dir')
    # now we start trying to fill out the config
    for uri in methods:
        repos_name = names[uri]
        for source in methods[uri]:
            dist = source['dist']
            #print "dist is", dist
            section = "%s-%s" % (repos_name, dist)
            #print "section will be", section
            handle_section(config, section, names, uri)
            if uri != source['uri']:
                # hopefully, this should never happen
                raise RuntimeError , "Something bad happened"
            config.set(section, 'method', uri)
            handle_codename(config, section, dist)
            handle_archs(config, section, source)
            handle_components(config, section, source)
            if use_upstream_release:
                handle_release(config, section, source)
    if output:
        config.write(file(output, 'w'))
    return config


if __name__ == '__main__':
    c = sources_to_config(filename='sources.list', output='test.conf')
    c.set('DEFAULT', 'reprepro_parent_dir', '/tmp/reprepro')
    c.write(file('test.conf', 'w'))
    
