import os

from paella.profile.base import PaellaConnection, PaellaConfig
from paella.profile.base import get_suite
from paella.profile.trait import TraitParent
from paella.profile.profile import ProfileEnvironment


class InstallerTools(object):
    def __init__(self):
        object.__init__(self)
        self.cfg = PaellaConfig()
        self.conn = PaellaConnection()
        self.profile = os.environ['PAELLA_PROFILE']
        self.target = os.environ['PAELLA_TARGET']
        self.suite = get_suite(self.conn, self.profile)
        self.pe = ProfileEnvironment(self.conn, self.profile)
        self.tp = TraitParent(self.conn, self.suite)
        
    def env(self):
        env = self.tp.Environment()
        env.update(self.pe.ProfileData())
        return env

    def set_trait(self, trait):
        self.tp.set_trait(trait)

        
