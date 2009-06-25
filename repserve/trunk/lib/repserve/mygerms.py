import sys

import apt_pkg

from repserve.base import get_architecture
from repserve.base import unzip_list_file
from repserve.path import path

germsite = path('/usr/lib/germinate')
if not germsite.isdir():
    raise RuntimeError , "You need to have germinate installed to use this module."
sys.path.append(germsite)

from Germinate import Germinator


class MyGerminator(Germinator):
    # here we initialize apt_pkg when we
    # instantiate the class
    def __init__(self):
        Germinator.__init__(self)
        ARCH = get_architecture()
        apt_pkg.InitConfig()
        apt_pkg.Config.Set("APT::Architecture", ARCH)
        apt_pkg.InitSystem()



if __name__ == '__main__':
    pass

    
