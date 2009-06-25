#!/usr/bin/python
# this file modified from dosbox-pykde
import os, sys, glob
import commands
from distutils.core import setup


from distutils.command.clean import clean as _clean
from distutils.command.build import build as _build

def get_version(astuple=False):
    orig_path = [p for p in sys.path]
    sys.path.insert(0, 'lib')
    from repserve import VERSION
    sys.path = orig_path
    if astuple:
        return VERSION
    else:
        return '.'.join(map(str, VERSION))


# override clean command to remove compiled modules
class clean(_clean):
    def run(self):
        _clean.run(self)
        here = os.getcwd()
        for root, dirs, files in os.walk(here):
            for afile in files:
                if afile.endswith('~'):
                    #print "removing backup file", os.path.join(root, afile)
                    os.remove(os.path.join(root, afile))
                if afile.endswith('.pyc'):
                    os.remove(os.path.join(root, afile))
        #os.chdir('data/doc')
        #map(os.remove, glob.glob('*.html'))
        # add extra clean commands below
        os.chdir(here)
        
class build(_build):
    def run(self):
        _build.run(self)
        # add extra build commands below
        

version = get_version()
description = 'Reprepro frontend for Debian written in Python'
author = 'Joseph Rawson'
author_email = 'umeboshi3@gmail.com'
url = 'file://.'

scripts = ['repserve']

# with the next lines we assume that this is being built with the --prefix /usr option
#docs_directory = 'share/doc/dosbox-pykde'
#applnk = 'share/applnk/Games/Emulator'
#docs_directory_html = os.path.join(docs_directory, 'html')
#_kde_html_parent = commands.getoutput('kde-config --path html').split(':')[1]
#kde_docs_directory_html = os.path.join(_kde_html_parent, 'en', 'dosbox-pykde')
#packages = ['dboxpykde']
packages = ['repserve']
#subpacks = ['common', 'contrib', 'filemanagement', 'kdelib', 'qtwin']
#kdelib_subpacks = ['dosboxcfg']
#packages += ['dboxpykde.%s' % p for p in subpacks]
#packages += ['dboxpykde.kdelib.%s' % p for p in kdelib_subpacks]

package_dir = {'' : 'lib'}


#data_files = [
#    (docs_directory, ['README']),
#    (applnk, ['data/dosbox-pykde.desktop'])
#    ]
data_files = []

setup(name='repserve',
      version=version,
      description=description,
      author=author,
      author_email=author_email,
      url=url,
      packages=packages,
      package_dir=package_dir,
      scripts=scripts,
      data_files=data_files,
      cmdclass=dict(clean=clean, build=build)
      )

      
