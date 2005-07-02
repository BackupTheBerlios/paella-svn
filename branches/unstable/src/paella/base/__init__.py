from useless.base.config import Configuration, list_rcfiles
from useless.db.lowlevel import QuickConn
from useless.db.midlevel import StatementCursor

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

    def cursor(self):
        return StatementCursor(self)
    
if __name__ == '__main__':
    c = PaellaConnection()
    #tp = TraitParent(c, 'woody')
    #pp = TraitPackage(c, 'woody')
    #ct = ConfigTemplate()
    #p = Parser('var-table.csv')
    
