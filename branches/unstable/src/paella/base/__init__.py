#import os
#from os.path import isdir, isfile, join, basename, dirname
#from sets import Set
#from ConfigParser import RawConfigParser
#import tempfile

#from kjbuckets import kjGraph, kjSet

#from useless.base import Error, NoExistError
#from useless.base.util import ujoin, makepaths, md5sum, strfile
#from useless.base.objects import Parser

#from useless.sqlgen.clause import one_many, Eq, In, NotIn

from useless.base.config import Configuration, list_rcfiles
#from useless.base.template import Template as _Template

from useless.db.lowlevel import QuickConn
#from useless.db.midlevel import StatementCursor
#from useless.db.midlevel import Environment, TableDict
#from useless.db.midlevel import SimpleRelation

class PaellaConfig(Configuration):
    def __init__(self, section=None, files=list_rcfiles('paellarc')):
        if section is None:
            section = 'database'
        Configuration.__init__(self, section=section, files=files)
        

class PaellaConnection(QuickConn):
    def __init__(self, cfg=None):
        if cfg is None:
            cfg = PaellaConfig('database')
        if type(cfg) is not dict:
            dsn = cfg.get_dsn()
        else:
            dsn = cfg
        if os.environ.has_key('PAELLA_DBHOST'):
            dsn['dbhost'] = os.environ['PAELLA_DBHOST']
        if os.environ.has_key('PAELLA_DBNAME'):
            dsn['dbname'] = os.environ['PAELLA_DBNAME']
        QuickConn.__init__(self, dsn)

if __name__ == '__main__':
    c = PaellaConnection()
    #tp = TraitParent(c, 'woody')
    #pp = TraitPackage(c, 'woody')
    #ct = ConfigTemplate()
    #p = Parser('var-table.csv')
    vc = VariablesConfig(c, 'family_environment', 'trait',
                         'family', 'test2')
    
