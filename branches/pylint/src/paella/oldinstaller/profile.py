import os
from os.path import isdir, isfile, join, basename, dirname
import logging

from useless.base import UnbornError, Log
from useless.base.util import ujoin, makepaths

from useless.db.midlevel import Environment

from paella.debian.base import RepositorySource
from paella.debian.debconf import install_debconf

from paella.base import PaellaConfig

from paella.db import PaellaConnection
from paella.db.base import get_traits, get_suite
from paella.db.trait.relations.parent import TraitParent
from paella.db.trait.relations.package import TraitPackage

from paella.db.profile import Profile
from paella.db.profile.main import ProfileTrait, ProfileEnvironment

from base import InstallerConnection, CurrentEnvironment
from base import Installer
from trait import TraitInstaller
        

class ProfileInstaller(Installer):
    def __init__(self, conn):
        os.environ['DEBIAN_FRONTEND'] = 'noninteractive'
        Installer.__init__(self, conn)
        self.profiletrait = ProfileTrait(self.conn)
        self.profile = None
        self.installer = None
        self._profile = Profile(self.conn)
        if hasattr(self, 'log'):
            self.log.info('profile installer initialized')
        else:
            self.set_logfile()
            self.log.info('profile installer initialized')
        self.mtypedata = {}
        
        
    def set_profile(self, profile):
        self.profile = profile
        self._profile.set_profile(profile)
        os.environ['PAELLA_PROFILE'] = profile
        self.profiletrait.set_profile(profile)
        self.traits = self.profiletrait.trait_rows()
        self.env = ProfileEnvironment(self.conn, self.profile)
        self.familydata = self._profile.get_family_data()
        self.profiledata = self._profile.get_profile_data()
        self.suite = get_suite(self.conn, profile)
        self.installer = TraitInstaller(self.conn, self.suite)
        self.installer.log = self.log
        self.installer.familydata = self.familydata
        self.installer.profiledata = self.profiledata
        self.installer.mtypedata = self.mtypedata
        self.traitparent = TraitParent(self.conn, self.suite)
        self.log.info('profile set to %s' % profile)
        traitlist = self.make_traitlist()
        self.setup_initial_paellainfo_env(traitlist)
        
    def get_profile_data(self):
        return self.env.ProfileData()
    
    def set_logpath(self, logpath):
        Installer.set_logpath(self, logpath)
        if hasattr(self, 'installer'):
            self.installer.set_logpath(logpath)
        
    def make_traitlist(self):
        listed = [x.trait for x in self.profiletrait.trait_rows()]
        #log = self.log
        log = None
        return self._profile.make_traitlist_with_traits(listed, log=log)

    def setup_initial_paellainfo_files(self, traits):
        makepaths(self.paelladir)
        traitlist = file(join(self.paelladir, 'traitlist'), 'w')
        for trait in traits:
            traitlist.write('%s\n' % trait)
        traitlist.close()
        itraits = file(join(self.paelladir, 'installed_traits'), 'w')
        itraits.write('Installed Traits:\n')
        itraits.close()

    def setup_initial_paellainfo_env(self, traits):
        if os.environ.has_key('PAELLA_MACHINE'):
            machine = os.environ['PAELLA_MACHINE']
            curenv = CurrentEnvironment(self.conn, machine)
            curenv['current_profile'] = self.profile
            curenv['traitlist'] = ', '.join(traits)
            curenv['installed_traits'] = ''
            
    def process(self):
        traits = self.make_traitlist()
        self.setup_initial_paellainfo_files(traits)
        self.setup_initial_paellainfo_env(traits)
        self.processed = []
        for trait in traits:
            self.process_trait(trait)
            self.log.info('currently processed %s' % ','.join(self.processed))
        self.log.info('all traits processed for profile %s' % self.profile)
        self.log.info('------------------------------------')
        
    def _append_installed_traits_file(self, trait):
        itraits = file(join(self.paelladir, 'installed_traits'), 'a')
        itraits.write(trait + '\n')
        itraits.close()

    def _append_installed_traits_db(self, trait):
        if os.environ.has_key('PAELLA_MACHINE'):
            machine = os.environ['PAELLA_MACHINE']
            curenv = CurrentEnvironment(self.conn, machine)
            line = curenv['installed_traits']
            traits = [t.strip() for t in line.split(',')]
            traits.append(trait)
            curenv['installed_traits'] = ', '.join(traits)
            
            
        
    def process_trait(self, trait):
        self.traitparent.set_trait(trait)
        self.installer.set_trait(trait)
        parents = [r.parent for r in self.traitparent.parents()]
        for p in parents:
            if p not in self.processed:
                raise UnbornError
        self.log.info('processing trait %s' % trait)
        self.installer.process()
        self.processed.append(trait)
        self.log.info('processed:  %s' % ', '.join(self.processed))
        self.append_installed_traits(trait)

    def set_template_path(self, path):
        self.installer.set_template_path(path)

    def set_target(self, target, update=False):
        Installer.set_target(self, target)
        self.installer.set_target(target)
        if update:
            os.system(self.command('apt-get update'))

    def install_kernel(self, package):
        os.system(self.command('touch /boot/vmlinuz-fake'))
        os.system(self.command('ln -s boot/vmlinuz-fake vmlinuz'))
        os.system(self.command('apt-get -y install %s' % package))
        print 'kernel %s installed' % package

    def append_installed_traits(self, trait):
        self._append_installed_traits_file(trait)
        self._append_installed_traits_db(trait)
        
def get_profile_packages(conn, suite, profile):
    traits = get_traits(conn, profile)
    tp = TraitParent(conn, suite)
    pp = TraitPackage(conn, suite)
    packages = [p.package for p in pp.all_packages(traits, tp)]
    return packages


def parse_package_rows(packages):
    grouped = {}
    package_count = 0
    for action in actions:
        grouped[action] = [ p.package for p in packages if p.action == action]
        package_count += len(grouped[action])
    if package_count != len(packages):
        raise Error, 'SOMETHING WENT WRONG in parse_package_rows'
    return grouped




def install_packages_uml(conn, suite, profile, target):
    traits = get_traits(conn, profile)
    tp = TraitParent(conn, suite)
    pp = TraitPackage(conn, suite)
    packages = ' '.join([p.package for p in pp.all_packages(traits, tp)])
    os.system('chroot %s apt-get update' % target)
    os.system('chroot %s apt-get -y install %s' % (target, packages))
              
if __name__ == '__main__':
    from useless.db.midlevel import StatementCursor
    from useless.db.midlevel import Environment, TableDict
    from base import PaellaConnection
    c = PaellaConnection()
    cfg = PaellaConfig()
    p = ProfileInstaller(c, cfg)
    p.set_profile('bard')
    pl = p.make_traitlist()
