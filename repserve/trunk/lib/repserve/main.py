import os
import subprocess

from repserve.path import path

from repserve.base import ImproperArgumentsError
from repserve.base import ImproperOptionsError
from repserve.base import UnhandledCommandError
from repserve.base import EmptyConfigError

from repserve.base import use_stdin_instead_of_filename
from repserve.config import sources_to_config
from repserve.gpg import KeyHelper
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
REPSERVE_COMMANDS += ['addkeyring', 'importkey', 'exportkey']



class RepserveHandler(object):
    def __init__(self, config):
        self.config = config
        self.flmanager = FilterListManager(self.config)
        self.reprepro = RepRepRo(self.config)
        self.keyhelper = KeyHelper(self.config)
        self._handle_map = dict(
            addsources=self.add_apt_sources,
            initialize=self.initialize_repserve,
            update=self.update_reprepro,
            export=self.export_reprepro,
            reconfigure=self.reconfigure_reprepro,
            exportkey=self.export_archive_key,
            addfilterlist=self.add_filterlist
            )
        
    def handle(self, command, opts, args):
        if command not in self._handle_map:
            self.unhandled(command, opts, args)
        self._handle_map[command](opts, args)
        

    def unhandled(self, command, opts, args):
        print "Command %s is not being handled" % command
        raise UnhandledCommandError , "Unhandled command %s" % command
    
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
        # create parent directories
        baseparent = self.config.getpath('DEFAULT', 'reprepro_parent_dir')
        outparent = self.config.getpath('DEFAULT', 'reprepro_parent_outdir')
        for dirname in [baseparent, outparent]:
            if not dirname.isdir():
                dirname.makedirs()
        # initialize gnupg
        self.keyhelper.initialize()
    
    def export_archive_key(self, opts, args):
        # no options handled yet
        # overwrites previously exported key
        self.keyhelper.export_archive_key(overwrite=True)
        
    def update_reprepro(self, opts, args):
        for section in self.config.sections():
            self.reprepro.update(section)

    def export_reprepro(self, opts, args):
        for section in self.config.sections():
            self.reprepro.export(section)
        self._export_archive_key()
        
    def reconfigure_reprepro(self, opts, args):
        self.reprepro.rconfig.create_config()


    def _determine_sections(self, opts):
        dist = opts.dist
        repos = opts.repos
        if dist is not None:
            if repos is None:
                raise ImproperOptionsError , "You must specify --repos if you specify --dist"
        # determine sections
        if repos is None:
            sections = self.config.sections()
            if not sections:
                raise EmptyConfigError , "There are no sections in the config file"
        else:
            sections = []
            for section in self.config.sections():
                if self.config.get(section, 'repos_name') == repos:
                    codename = self.config.get(section, 'codename')
                    if dist is None or dist == codename:
                        sections.append(section)
            if not sections:
                raise RuntimeError , "No sections found in config for repos %s" % repos
        return sections
    
    def add_filterlist(self, opts, args):
        sections = self._determine_sections(opts)
        filename = None
        if len(args) != 1:
            raise ImproperArgumentsError , "Need a name/filename argument"
        arg = path(args[0])
        if not arg.isfile():
            name = arg
            filename = use_stdin_instead_of_filename()
        else:
            name = arg.basename()
            filename = arg
        flist = self.flmanager.make_filterlist(name, filename=filename)
        self.flmanager.write_filterlist_to_confdirs(flist, sections)
        for section in sections:
            self.flmanager.add_filterlist_to_section(section, flist)
            

    def remove_filterlist(self, opts, args):
        sections = self._determine_sections(opts)
        if not args:
            msg = "You must specify the name of the filterlist(s)"
            msg += " on the command line."
            raise ImproperArgumentsError , msg
        raise UnhandledCommandError, "This command isn't handled"
    
        
    
