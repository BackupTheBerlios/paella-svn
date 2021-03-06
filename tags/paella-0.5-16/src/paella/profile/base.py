import os
from os.path import isdir, isfile, join, basename, dirname
from sets import Set
from operator import or_ as U

from kjbuckets import kjGraph, kjSet

from paella.base.util import ujoin, makepaths
from paella.base.objects import Parser

from paella.sqlgen.clause import one_many, Eq, In, NotIn

from paella.base.config import Configuration, list_rcfiles
from paella.base.template import Template as _Template

from paella.db.lowlevel import QuickConn
from paella.db.midlevel import StatementCursor
from paella.db.midlevel import Environment, TableDict
from paella.db.midlevel import SimpleRelation


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

class ProfileStruct(object):
    name = 'myprofile'
    suite = 'sid'
    traits = ['admin']
    environ = {}
    template = 'path_to_template'

class TraitStruct(object):
    name = 'mytrait'
    suite = 'sid'
    parents = ['another_trait', 'maybe_another_trait']
    packages = dict.fromkeys(['bash', 'apache', 'python'], 'install')
    environ = {'name' : 'value'}
    templates = ['rel_path_to_template1',
                 'rel_path_to_template2']


class Suites(StatementCursor):
    def __init__(self, conn):
        StatementCursor.__init__(self, conn, name='Suites')
        self.set_table('suites')
        self.current = None

    def list(self):
        return [x.suite for x in self.select()]

    def set(self, suite):
        if suite not in self.list():
            raise Error, 'bad suite'
        self.current = suite

class AllTraits(StatementCursor):
    def __init__(self, conn):
        StatementCursor.__init__(self, conn, name='AllTraits')
        self.set_table('traits')

    def list(self):
        return [x.trait for x in self.select()]

class Traits(StatementCursor):
    def __init__(self, conn, suite):
        StatementCursor.__init__(self, conn, name='AllTraits')
        self.set_suite(suite)
        
        
    def set_suite(self, suite):
        self.suite = suite
        self.set_table(ujoin(self.suite, 'traits'))
        

    def list(self):
        return [x.trait for x in self.select()]
    

class TraitEnvironment(Environment):
    def __init__(self, conn, suite, trait):
        self.suite = suite
        table = ujoin(suite, 'variables')
        Environment.__init__(self, conn, table, 'trait')
        self.set_main(trait)

class TraitEnvironments(Environment):
    def __init__(self, conn, suite):
        self.suite = suite
        table = ujoin(suite, 'variables')
        Environment.__init__(self, conn, table, 'trait')

    def set_trait(self, trait):
        self.set_main(trait)

class _TraitRelation(SimpleRelation):
    def __init__(self, conn, suite, table, name='_TraitRelation'):
        SimpleRelation.__init__(self, conn, table, 'trait', name=name)
        self.suite = suite
        self.current_trait = None

    def set_trait(self, trait):
        self.set_current(trait)
        self.current_trait = self.current
        

    def delete_trait(self, trait):
        self.delete(trait)
        
    
class _CommonTemplate(object):
    def template_filename(self, template):
        tpath = join(self.template_path, self.suite, self.trait)
        return join(tpath, template + '.template')

    def suite_template_path(self, filesel=False):
        path = join(self.template_path, self.suite)
        if filesel:
            path += '/'
        return path

    def trait_temp_path(self, filesel=False):
        path = join(self._tmp_path, self.suite, self.trait)
        if filesel:
            path += '/'
        return path

    def set_suite(self, suite):
        self.suite = suite


class Template(_Template):
    def __init__(self, data={}):
        _Template.__init__(self, data)
        self.template_path = None

    def set_path(self, path):
        self.template_path = path
        
    #this returns the path from the root
    #of the trait tarfile to the template
    def _template_filename(self, suite, trait, package, template):
        tpath = join(self.template_path, suite, trait, package)
        return join(tpath, template + '.template')

    def _filesel(self, filesel, path):
        if filesel:
            path += '/'
        return path

    def _suite_template_path(self, suite, filesel=False):
        return self._filesel(filesel, join(self.template_path, suite))

    def _trait_temp_path(self, tmp_path, suite, trait, filesel=False):
        return self._filesel(filesel, join(tmp_path, suite, trait))
    
    def set_template(self, templatefile):
        _Template.set_template(self, templatefile.read())
        templatefile.close()

    def set_suite(self, suite):
        self.suite = suite

    def set_trait(self, trait):
        self.trait = trait
        

def get_traits(conn, profile):
    cursor = StatementCursor(conn)
    cursor.set_table('profile_trait')
    cursor.set_clause([('profile', profile)])
    return [r.trait for r in cursor.select()]

def get_suite(conn, profile):
    cursor = StatementCursor(conn)
    cursor.set_table('profiles')
    cursor.set_clause([('profile', profile)])
    return [r.suite for r in cursor.select()][0]



              
if __name__ == '__main__':
    c = PaellaConnection
    tp = TraitParent(c, 'woody')
    pp = TraitPackage(c, 'woody')
    ct = ConfigTemplate()
    p = Parser('var-table.csv')
    
