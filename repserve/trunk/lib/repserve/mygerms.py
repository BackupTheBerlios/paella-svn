import sys
import tempfile

import apt_pkg

from repserve.base import get_architecture
from repserve.base import unzip_list_file
from repserve.path import path

germsite = path('/usr/lib/germinate')
if not germsite.isdir():
    raise RuntimeError , "You need to have germinate installed to use this module."
sys.path.append(germsite)

from Germinate import Germinator
import Germinate.seeds

# a function to add " * " to each package
# and return a list of lines
def make_seed_contents(packages):
    lines = []
    for package in packages:
        lines.append(' * %s' % package)
    return lines

# a function to make simple seed files
# from a list of packages
# returns the path to the temporary directory
# it creates (which will be used as the
# --seed-dist option for the germinate command
def make_simple_seed_files(packages, listname='mypacks'):
    tmpdir = tempfile.mkdtemp('seeds', 'repserve')
    tmpdir = path(tmpdir)
    blacklist = tmpdir / 'blacklist'
    blacklist.write_bytes('')
    structure = tmpdir / 'STRUCTURE'
    structure.write_lines(['%s:' % listname])
    package_lines = make_seed_contents(packages)
    package_list = tmpdir / listname
    package_list.write_lines(package_lines)
    return tmpdir
    
    

def feed_seeds_to_germinator(germinator, packages):
    pass


class MyGerminator(Germinator):
    # here we initialize apt_pkg when we
    # instantiate the class
    def __init__(self, arch=None):
        Germinator.__init__(self)
        if arch is None:
            arch = get_architecture()
        apt_pkg.InitConfig()
        apt_pkg.Config.Set("APT::Architecture", arch)
        apt_pkg.InitSystem()



if __name__ == '__main__':
    g = MyGerminator()
    td = make_simple_seed_files(['iceweasel'])
    SEEDS, RELEASE = td.splitpath()
    if SEEDS.startswith('/'):
        print SEEDS
        SEEDS = 'file://%s' % SEEDS
        print "SEEDS url", SEEDS
    seednames, seedinherit, seedbranches = g.parseStructure(
        [SEEDS], RELEASE)
    seedtexts = dict()
    for seedname in seednames:
        try:
            seed_fd = Germinate.seeds.open_seed([SEEDS],
                                                seedbranches, seedname)
        except Germinate.seeds.SeedError:
            print "Seed Error", seedname
            sys.exit(1)
        seedtexts[seedname] = seed_fd.readlines()
        seed_fd.close()
        
    
