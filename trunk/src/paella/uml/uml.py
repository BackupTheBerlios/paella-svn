import os
from os.path import isfile, join, dirname
import tarfile

from paella.base.defaults import MB
from paella.base.util import makepaths
from paella.base.tarball import make_tarball

from paella.debian.base import RepositorySource, debootstrap
from paella.profile.base import get_suite

from paella.installer.base import InstallerConnection

from paella.installer.fstab import UmlFstab
from paella.installer.profile import ProfileInstaller

from base import Uml, create_root_filesystem

print "don't bother me i'm deprecated"

if __name__ == '__main__':
    pass
