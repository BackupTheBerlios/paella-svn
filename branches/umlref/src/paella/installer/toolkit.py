import os

from useless.base.util import str2list
from useless.base.path import path

from paella.base import PaellaConfig
from paella.base.template import TemplatedEnvironment

from paella.db import DefaultEnvironment
from paella.db.base import get_suite
from paella.db.trait import Trait
from paella.db.trait.relations.parent import TraitParent
from paella.db.family import Family
from paella.db.profile import Profile
from paella.db.profile.main import ProfileEnvironment

from base import InstallError, InstallerConnection, Modules
from util.main import setup_modules

#from trait import TraitInstaller
#from profile import ProfileInstaller

from paella.oldinstaller.profile import ProfileInstaller

class InstallerTools(object):
    def __init__(self):
        object.__init__(self)
        self.cfg = PaellaConfig()
        self.conn = InstallerConnection()
        self.profile = os.environ['PAELLA_PROFILE']
        self.target = path(os.environ['PAELLA_TARGET'])
        self.machine = None
        self.trait = None
        self.suite = get_suite(self.conn, self.profile)
        self.pr = Profile(self.conn)
        self.pr.set_profile(self.profile)
        self.traitlist = self.pr.make_traitlist()
        self.pe = ProfileEnvironment(self.conn, self.profile)
        self.tp = TraitParent(self.conn, self.suite)
        self.fm = Family(self.conn)
        self.tr = Trait(self.conn, self.suite)
        self.families = list(self.fm.get_related_families(self.pr.get_families()))
        self._envv = None
        self.default = DefaultEnvironment(self.conn)
        #self.installer = TraitInstaller(self.conn, self.suite)
        self.installer = ProfileInstaller(self.conn)
        self.installer.set_logfile()
        self.installer.set_profile(self.profile)
        self.installer.set_target(self.target)
        if os.environ.has_key('PAELLA_MACHINE'):
            self.machine = os.environ['PAELLA_MACHINE']
        if os.environ.has_key('PAELLA_TRAIT'):
            self.set_trait(os.environ['PAELLA_TRAIT'])
             

    # this needs updating for machine type data
    def env(self):
        env = TemplatedEnvironment(self.tp.Environment())
        env.update(self.pr.get_family_data())
        env.update(self.pr.get_profile_data())
        return env

    def set_trait(self, trait):
        self.trait = trait
        self.tp.set_trait(trait)
        self.tr.set_trait(trait)
        self.parents = self.tr.parents()
        self._envv = self.env()
        tinstaller = self.installer.installer
        tinstaller.set_trait(trait)
        self.packages = tinstaller.traitpackage.packages()
        self.templates = tinstaller.traittemplate.templates()
        
    def get(self, key):
        if self._envv is None:
            raise Error, 'need to set trait first'
        return self._envv.dereference(key)

    def lget(self, key):
        key = '_'.join([self.trait, key])
        return self.get(key)

    def install_modules(self, name):
        modules = str2list(self.get(name))
        print 'installing modules', modules, 'to %s/etc/modules' % self.target
        setup_modules(self.target, modules)

    def remove_packages(self, packages=None):
        if packages is None:
            packages = self.packages
        if len(packages):
            if hasattr(packages[0], 'package'):
                packages = [p.package for p in packages]
        package_list = ' '.join(packages)
        command = 'apt-get -y remove %s' % package_list
        self.installer.run('remove', command, proc=True)

    def chroot_command(self, cmd):
        return 'chroot %s %s' % (self.target, cmd)
    
        
if __name__ == '__main__':
    from paella.db import PaellaConnection
    conn = PaellaConnection()
    #tp = TraitParent(conn, 'gunny')
    os.environ['PAELLA_PROFILE'] = 'ztest'
    os.environ['PAELLA_TARGET'] = 'nowhere'
    os.environ['PAELLA_LOGFILE'] = 'mylog'
    it = InstallerTools()
    it.set_trait('base')
    
