import os
import subprocess

from repserve.path import path

from repserve.base import use_stdin_instead_of_filename
from repserve.config import sources_to_config
from repserve.gpg import make_default_signing_key
from repserve.gpg import get_gpg_keyid
from repserve.reprepro import RepRepRo
from repserve.filterlist import FilterListManager

REPSERVE_COMMANDS = []
# add/remove filterlists
REPSERVE_COMMANDS += ['addfilterlist', 'removefilterlist']
# add apt sources
REPSERVE_COMMANDS += ['addsources']
# initialize repserve
REPSERVE_COMMANDS += ['initialize']
# control reprepro
REPSERVE_COMMANDS += ['update', 'export', 'reconfigure']
# gpg stuff
REPSERVE_COMMANDS += ['addkeyring', 'importkey']



class RepserveHandler(object):
    def __init__(self, config):
        self.config = config
        self.flmanager = FilterListManager(self.config)
        self.reprepro = RepRepRo(self.config)
        self._handle_map = dict(
            addsources=self.add_apt_sources,
            initialize=self.initialize_repserve,
            update=self.update_reprepro,
            export=self.export_reprepro,
            reconfigure=self.reconfigure_reprepro
            )
        
    def handle(self, command, opts, args):
        if command not in self._handle_map:
            self.unhandled(command, opts, args)
        self._handle_map[command](opts, args)
        

    def unhandled(self, command, opts, args):
        print "Command %s is not being handled" % command
        raise RuntimeError , "Unhandled command"
    
    def add_apt_sources(self, opts, args):
        arch = opts.arch
        filename = None
        if args:
            filename = args[0]
        if filename is None:
            filename = use_stdin_instead_of_filename()
        sources_to_config(filename=filename, arch=arch,
                          config=self.config, output='')
        # write config
        self.config.write_file()

    def initialize_repserve(self, opts, args):
        here = self._pushd_home()
        # create parent directories
        baseparent = self.config.getpath('DEFAULT', 'reprepro_parent_dir')
        outparent = self.config.getpath('DEFAULT', 'reprepro_parent_outdir')
        for dirname in [baseparent, outparent]:
            if not dirname.isdir():
                dirname.makedirs()
        gnupg_confdir = path('.gnupg')
        if gnupg_confdir.isdir():
            print "It appears that repserve has already been initialized"
            return
        fullname = self.config.get('DEFAULT', 'fullname')
        email = self.config.get('DEFAULT', 'email')
        if not email:
            email = None
        make_default_signing_key(fullname=fullname, email=email)
        keyid = get_gpg_keyid(fullname)
        #print "found key id", keyid
        self.config.set('DEFAULT', 'signwith', keyid)
        self.config.write_file()
        self._export_archive_key(keyid=keyid, outdir=outparent)
        os.chdir(here)
        
    def _pushd_home(self):
        here = path.getcwd()
        homedir = path('~/').expand()
        os.chdir(homedir)
        return here
    
    def _export_archive_key(self, keyid=None, outdir=None, overwrite=False):
        if keyid is None:
            keyid = self.config.get('DEFAULT', 'signwith')
        if outdir is None:
            outdir = self.config.getpath('DEFAULT', 'reprepro_parent_outdir')
        filename = outdir / 'archive.gpg'
        if not filename.isfile() or overwrite:
            here = self._pushd_home()
            command = ['gpg', '--export', '--armour', '--output', str(filename), keyid]
            subprocess.check_call(command)
            os.chdir(here)
        else:
            print "%s already exists" % filename
            
        
    def update_reprepro(self, opts, args):
        for section in self.config.sections():
            self.reprepro.update(section)

    def export_reprepro(self, opts, args):
        for section in self.config.sections():
            self.reprepro.export(section)
        self._export_archive_key()
        
    def reconfigure_reprepro(self, opts, args):
        self.reprepro.rconfig.create_config()

    def add_filterlist(self, opts, args):
        pass

    def remove_filterlist(self, opts, args):
        pass
    
