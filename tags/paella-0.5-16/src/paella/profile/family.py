#import os
#from os.path import join, dirname, isdir
from sets import Set
from kjbuckets import kjGraph

#from xml.dom.minidom import Element
#from xml.dom.minidom import parse as parse_file
#from xml.dom.minidom import parseString as parse_string

#from paella.base import UnbornError, Error, debug
#from paella.base.xmlfile import TextElement
#from paella.base.util import ujoin, makepaths

#from paella.sqlgen.clause import Eq
from paella.db.midlevel import StatementCursor, SimpleRelation
from paella.db.midlevel import Environment
#from paella.db.lowlevel import OperationalError

#from paella.schema.paellascheme import insert_packages, make_suite
#from paella.schema.paellascheme import start_schema

#from base import TraitEnvironment, get_suite
#from trait import TraitParent, TraitDebconf
#from trait import TraitPackage, TraitTemplate
#from trait import TraitsElement, Trait

#from xmlparse import PaellaParser, ProfilesParser, ProfileParser
#from xmlgen import EnvironElement, SuitesElement
#from xmlgen import SuiteElement, ProfileElement
#from xmlgen import ProfileVariableElement


class Family(object):
    def __init__(self, conn):
        object.__init__(self)
        self.conn = conn
        self.cursor = StatementCursor(self.conn)
        self.current = None
        self.parent = SimpleRelation(self.conn, 'family_parent', 'family')
        self.env = Environment(self.conn, 'family_environment', 'family')
        
    def set_family(self, family):
        self.current = family
        self.parent.set_current(family)
        self.env.set_main(family)
        
    def add_family(self, family, type='general'):
        pass

    def get_families(self, families=[]):
        rows = self.cursor.select(table='family_parent')
        graph = kjGraph([(r.family, r.parent) for r in rows])
        dfamilies = Set()
        for fam in families:
            dfamilies |= Set([fam]) | Set(graph.reachable(fam).items())
        return dfamilies

    def parents(self, family=None):
        if family is None:
            family = self.current
        self.parent.set_clause(family)
        rows = self.parent.cmd.select(fields=['parent'], order='parent')
        self.parent.reset_clause()
        return [x.parent for x in rows]
    
if __name__ == '__main__':
    import os
    conn = PaellaConnection()
    path = g['db_bkup_path']
    #db = XmlDatabase(conn, path)
    #p = ProfileStruct
    #t = _Trait_(conn, 'woody')
    #ts = Traits(conn, 'woody')
    #t.set('default')
    #ss = parse_string(t.toxml())
    #tp = TraitParser(ss.firstChild)
    #pd = PaellaDatabase(conn, path)
    pp = PaellaProcessor(conn)
    pp.parse_xml('foo.xml')
    

    #cmd = CommandCursor(c, 'dsfsdf')
    cmd = StatementCursor(conn)
    def dtable():
        cmd.execute('drop table ptable')

    def dtables():
        for t in cmd.tables():
            if t != 'footable':
                cmd.execute('drop table %s' %t)


