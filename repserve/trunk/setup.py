#!/usr/bin/python
# this file modified from dosbox-pykde
import os, sys, glob
import commands
from distutils.core import setup


from distutils.command.clean import clean as _clean
from distutils.command.build import build as _build

def get_version(astuple=False):
    topline = file('debian/changelog').next()
    VERSION = topline[topline.find('(')+1 :topline.find(')')].split('.')
    print "VERSION", VERSION
    for character in '-+':
        if character in VERSION[1]:
            VERSION = VERSION[0:1] + [VERSION[1].split(character)[0]]
    print 'VERSION is', VERSION
    if astuple:
        return tuple(VERSION)
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
        # remove html docs
        os.system('rm -fr docs/html')
        
        
class build(_build):
    def run(self):
        _build.run(self)
        # add extra build commands below

# taken from paella and modified
class builddocs(_build):
    def run(self):
        _build.run(self)
        here = os.getcwd()
        os.chdir('docs')
        print "building docs"
        exclude = ['.svn', 'images', 'html']
        files = [f for f in os.listdir('.') if f not in exclude]
        files = [f for f in files if not f.endswith('~')]
        files = [f for f in files if '#' not in f]
        files = [f for f in files if not f.startswith('.')]
        files = [f for f in files if not f.endswith('.css')]
        print "source doc files:", ', '.join(files)
        if os.path.exists('html'):
            print "found html directory, removing it"
            os.system('rm -fr html')
        if os.path.exists('html'):
            raise RuntimeError , "failed to remove docs/html"
        os.mkdir('html')
        data_tuple = ('html', [])
        data_files.append(data_tuple)
        # add the stylesheet
        data_tuple[1].append('docs/default.css')
        for srcfile in files:
            print "building", srcfile
            htmlfile = 'html/%s.html' % srcfile
            cmd = 'rst2html --stylesheet=default.css --link-stylesheet'
            os.system('%s %s %s' % (cmd, srcfile, htmlfile))
            data_tuple[1].append('docs/%s' % htmlfile)
        # no images
        if False:
            # add screenshots
            images_tuple = ('html/images', [])
            data_files.append(images_tuple)
            for image in os.listdir('images'):
                if image.endswith('.png'):
                    print "adding %s to data_files" % image
                    images_tuple[1].append('docs/images/%s' % image)
        os.chdir(here)

# start running here
name = 'repserve'
what = sys.argv[1]
docs = False
scripts = []
packages = []
package_dir = {}
cmdclass = dict(clean=clean, build=build)
# generate setup options
if what == 'doc':
    name = 'repserve-doc'
    docs = True
    cmdclass = dict(clean=clean, build=builddocs)
    del sys.argv[1]
elif what == 'main':
    name = 'repserve'
    scripts = ['repserve']
    packages = ['repserve']
    package_dir = {'' : 'lib'}
    cmdclass = dict(clean=clean, build=build)
    del sys.argv[1]
else:
    print "ignoring", what
    
    


version = get_version()
description = 'Reprepro frontend for Debian written in Python'
author = 'Joseph Rawson'
author_email = 'umeboshi3@gmail.com'
url = 'file://.'



#data_files = [
#    (docs_directory, ['README']),
#    (applnk, ['data/dosbox-pykde.desktop'])
#    ]
data_files = []

setup(name=name,
      version=version,
      description=description,
      author=author,
      author_email=author_email,
      url=url,
      packages=packages,
      package_dir=package_dir,
      scripts=scripts,
      data_files=data_files,
      cmdclass=cmdclass
      )

      
