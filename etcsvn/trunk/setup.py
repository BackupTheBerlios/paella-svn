#!/usr/bin/python
import os, sys
from distutils.core import setup

version = '0.1'
description = 'Etcsvn System Configuration Management Using Subversion'
author = 'Joseph Rawson'
author_email = 'umeboshi@gregscomputerservice.com'
url = 'http://developer.berlios.de/projects/etcsvn'

scripts = []
setup(version=version, description=description, author=author,
      author_email=author_email, url=url, packages=packages,
      package_dir=package_dir, scripts=scripts)
