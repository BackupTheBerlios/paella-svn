import os
from os.path import join, dirname, isdir
from sets import Set

from xml.dom.minidom import Element
from xml.dom.minidom import parse as parse_file
from xml.dom.minidom import parseString as parse_string

from paella.base import UnbornError, Error, debug
from paella.base.xmlfile import TextElement
from paella.base.util import ujoin, makepaths

from paella.sqlgen.clause import Eq
from paella.db.midlevel import StatementCursor, SimpleRelation
from paella.db.midlevel import Environment
from paella.db.lowlevel import OperationalError

from paella.schema.paellascheme import insert_packages, make_suite
from paella.schema.paellascheme import start_schema

from base import TraitEnvironment, get_suite
from trait import TraitParent, TraitDebconf
from trait import TraitPackage, TraitTemplate
from trait import TraitsElement, Trait

from xmlparse import PaellaParser, ProfilesParser, ProfileParser
from xmlgen import EnvironElement, SuitesElement
from xmlgen import SuiteElement, ProfileElement
from xmlgen import ProfileVariableElement

class Profiles(StatementCursor):
    def __init__(self, conn):
        StatementCursor.__init__(self, conn)
        self.set_table('profiles')

    def drop_profile(self, profile):
        self.delete(clause=Eq('profile', profile))

class ProfileTrait(SimpleRelation):
    def __init__(self, conn):
        SimpleRelation.__init__(self, conn, 'profile_trait',
                                'profile', name='ProfileTrait')

    def set_profile(self, profile):
        self.set_current(profile)

    def traits(self, profile=None):
        if profile is None:
            profile = self.current
        self.set_clause(profile)
        rows = self.cmd.select(fields=['trait'], order=['ord', 'trait'])
        self.reset_clause()
        return rows

    def trait_rows(self, profile=None):
        if profile is None:
            profile = self.current
        self.set_clause(profile)
        rows = self.cmd.select(fields=['trait', 'ord'], order='ord')
        self.reset_clause()
        return rows
        
    def insert_trait(self, trait):
        idata = dict(profile=self.current, trait=trait, ord='0')
        self.cmd.insert(data=idata)

    def insert_traits(self, traits):
        diff = self.diff('trait', traits)
        for trait in diff:
            self.insert_trait(trait)

    def drop_profile(self, profile):
        self.cmd.delete(clause=Eq('profile', profile))

    def delete(self, trait):
        clause=Eq('profile', self.current) & Eq('trait', trait)
        self.cmd.delete(clause=clause)

    def update(self, *args, **kw):
        self.cmd.update(*args, **kw)
        
class _ProfileEnvironment(Environment):
    def __init__(self, conn, profile):
        self.suite = get_suite(conn, profile)
        self.profile = profile
        Environment.__init__(self, conn, 'profile_variables', 'trait')
        self.traitparent = TraitParent(self.conn, self.suite)
        
    def set_trait(self, trait):
        self.set_main(trait)
        self.traitparent.set_trait(trait)
        
    def _single_clause_(self):
        return Eq('profile', self.profile) & Eq('trait', self.__main_value__)
    
    def __setitem__(self, key, value):
        try:
            self.cursor.insert(data={'profile' : self.profile,
                                     'trait' : self.__main_value__,
                                     self.__key_field__ : key,
                                     self.__value_field__ : value})
        except OperationalError:
            self.cursor.update(data={self.__value_field__ : value},
                               clause=self._double_clause_(key))
            
        
    def _make_superdict_(self):
        clause = Eq('profile', self.profile)
        superdict = {}
        traits = [row.trait for row in self.cursor.select(fields=['trait'], clause=clause)]
        for trait in traits:
            self.set_trait(trait)
            items = [(trait + '_' + key, value) for key, value in self.items()]
            superdict.update(dict(items))
        return superdict

    def _get_defaults_(self, trait):
        return self.traitparent.get_environment([trait])

    def _update_defaults_(self, trait):
        for trait, data in self._get_defaults_(trait):
            self.set_trait(trait)
            self.update(data)

class ProfileEnvironment(object):
    def __init__(self, conn, profile=None):
        object.__init__(self)
        self.conn = conn
        self.profile = profile
        self.profiletraits = ProfileTrait(self.conn)
        self.env = None
        if profile is not None:
            self.env = _ProfileEnvironment(conn, profile)
            self.set_profile(profile)

    def set_profile(self, profile):
        self.profile = profile
        self.profiletraits.set_profile(profile)
        self.env = _ProfileEnvironment(self.conn, profile)
        
        
    def set_defaults(self):
        for trait in self.get_all_traits():
            self.env.set_trait(trait)
            data = TraitEnvironment(self.conn, self.env.suite, trait)
            self.env.update(data)        

    def get_all_traits(self):
        profile_traits = [row.trait for row in self.profiletraits.traits()]
        return list(self.env.traitparent.get_traitset(profile_traits))

    def ProfileData(self):
        return self.env._make_superdict_()

    def get_rows(self):
        clause = Eq('profile', self.profile)
        return self.env.cursor.select(clause=clause, order=['trait', 'name'])

    def get_traits(self):
        clause = Eq('profile', self.profile)
        rows =  self.env.cursor.select(fields=['distinct trait'], clause=clause)
        return [row.trait for row in rows]
    
    def append_defaults(self):
        for trait in self.get_all_traits():
            self.env.set_trait(trait)
            data = TraitEnvironment(self.conn, self.env.suite, trait)
            new_items = [(k,v) for k,v in data.items() if k not in self.env.keys()]
            self.env.update(dict(new_items))
            
    
    
#generate xml
class _Profile_(Element):
    def __init__(self, conn):
        self.conn = conn
        Element.__init__(self, 'profile')
        
#generate xml
class PaellaProfiles(Element):
    def __init__(self, conn):
        Element.__init__(self, 'profiles')
        self.conn = conn
        self.stmt = StatementCursor(self.conn)
        self.env = ProfileEnvironment(self.conn)
        self.profiletraits = ProfileTrait(self.conn)
        self._profiles = {}
        for row in self.stmt.select(table='profiles', order='profile'):
            self._append_profile(row.profile, row.suite)
                
    def _append_profile(self, profile, suite):
        element = self.export_profile(profile, suite)
        self._profiles[profile] = element
        self.appendChild(self._profiles[profile])

    def export_profile(self, profile, suite=None):
        if suite is None:
            row = self.stmt.select_row(table='profiles',clause=Eq('profile', profile))
            suite = row['suite']
        suite = str(suite)
        profile = str(profile)
        self.env.set_profile(profile)
        element = ProfileElement(profile, suite)
        element.append_traits(self.profiletraits.trait_rows(profile))
        element.append_variables(self.env.get_rows())
        return element

    def insert_profile(self, profile):
        idata = {'profile' : profile.name,
                 'suite' : profile.suite}
        self.stmt.insert(table='profiles', data=idata)
        idata = {'profile' : profile.name,
                 'trait' : None,
                 'ord' : 0}
        for trait, ord in profile.traits:
            print trait, ord
            idata['trait'] = trait
            idata['ord'] = ord #str(ord)
            self.stmt.insert(table='profile_trait', data=idata)
        idata = {'profile' : profile.name,
                 'trait' : None,
                 'name' : None,
                 'value': None}
        for trait, name, value in profile.vars:
            idata['trait'] = trait
            idata['name'] = name
            idata['value'] = value
            self.stmt.insert(table='profile_variables', data=idata)

    def export_profiles(self, path):
        rows = self.stmt.select(fields='profile', table='profiles', clause=None)
        for row in rows:
            self.write_profile(row.profile, path)
        
    def write_profile(self, profile, path):
        xmlfile = file(join(path, '%s.xml' % profile), 'w')
        data = self.export_profile(profile)
        data.writexml(xmlfile, indent='\t', newl='\n', addindent='\t')
        xmlfile.close()
        
        
        
#generate xml        
class PaellaDatabase(Element):
    def __init__(self, conn, path='/'):
        Element.__init__(self, 'paelladatabase')
        self.conn = conn
        self.stmt = StatementCursor(self.conn)
        self._profile_traits_ = ProfileTrait(self.conn)
        self.path = path
        self.suites = SuitesElement()
        self.appendChild(self.suites)
        for row in self._suite_rows():
            args = map(str, [row.suite, row.nonus, row.updates, row.local, row.common])
            element = SuiteElement(*args)
            self.suites.appendChild(element)
        self.profiles = PaellaProfiles(self.conn)
        suites = [x.suite for x in self._suite_rows()]
        for suite in suites:
            self.appendChild(TraitsElement(self.conn, suite))

    def _suite_rows(self):
        return self.stmt.select(table='suites', order='suite')

    def write(self, filename):
        path = join(self.path, filename)
        xmlfile = file(path, 'w')
        self.writexml(xmlfile, indent='\t', newl='\n', addindent='\t')

    def backup(self, path=None):
        if path is None:
            path = self.path
        if not isdir(path):
            raise Error, '%s not a directory' % path
        dbfile = file(join(path, 'database.xml'), 'w')
        self.writexml(dbfile, indent='\t', newl='\n', addindent='\t')
        dbfile.close()
        self.backup_profiles(path)
        suites = [x.suite for x in self._suite_rows()]
        for suite in suites:
            makepaths(join(path, suite))
            trait = Trait(self.conn, suite)
            for t in trait.get_trait_list():
                trait.set_trait(t)
                trait.backup_trait(join(path, suite))

    def backup_profiles(self, path=None):
        profiles_dir = join(path, 'profiles')
        makepaths(profiles_dir)
        self.profiles.export_profiles(profiles_dir)
        
        
class PaellaProcessor(object):
    def __init__(self, conn):
        object.__init__(self)
        self.conn = conn
        self.__set_cursors__()
        self.main_path = None
        
    def parse_xml(self, filename):
        self.dbdata = PaellaParser(filename)
        self.main_path = dirname(filename)

    def start_schema(self):
        start_schema(self.conn)
        self._sync_suites()

    def _sync_suites(self):
        self.main.set_table('suites')
        current_suites = [row.suite for row in self.main.select()]
        for suite in self.dbdata.suites:
            if suite.name not in current_suites:
                self.main.insert(data=suite)
                make_suite(self.main, suite.name)
                insert_packages(self.main, suite.name)
            else:
                self.main.update(data=suite)

    def insert_profiles(self):
        path = join(self.main_path, 'profiles')
        print 'path is in insert_profiles', path
        xmlfiles = [join(path, x) for x in os.listdir(path) if x[-4:] == '.xml']
        profiles = PaellaProfiles(self.conn)
        for xmlfile in xmlfiles:
            xml = parse_file(xmlfile)
            elements = xml.getElementsByTagName('profile')
            if len(elements) != 1:
                raise Error, 'bad profile number %s' % len(elements)
            element = elements[0]
            parsed = ProfileParser(element)
            profiles.insert_profile(parsed)
        

    def insert_profile(self, profile):
        idata = {'profile' : profile.name,
                 'suite' : profile.suite}
        self.main.insert(table='profiles', data=idata)
        idata = {'profile' : profile.name,
                 'trait' : None,
                 'ord' : 0}
        for trait, ord in profile.traits:
            print trait, ord
            idata['trait'] = trait
            idata['ord'] = ord #str(ord)
            self.main.insert(table='profile_trait', data=idata)
        idata = {'profile' : profile.name,
                 'trait' : None,
                 'name' : None,
                 'value': None}
        for trait, name, value in profile.vars:
            idata['trait'] = trait
            idata['name'] = name
            idata['value'] = value
            self.main.insert(table='profile_variables', data=idata)
    

    def insert_traits(self, suite):
        self.__set_suite_cursors__(suite)
        traits = [trait for trait in self.dbdata.get_traits(suite)]
        self._insert_traits_(traits, suite)

    def _clear_traits(self, suite):
        self.__set_suite_cursors__(suite)
        self.traitparent.cmd.delete()
        self.traitpackage.cmd.delete()
        self.main.delete(table=ujoin(suite, 'variables'))
        self.traits.delete()

    def _insert_traits_(self, traits, suite):
        while len(traits):
            trait = traits[0]
            print 'inserting %s' %trait, len(traits)
            try:
                self._insert_trait_(trait, suite)
            except UnbornError:
                traits.append(trait)
            del traits[0]
            
    def _insert_trait_(self, trait, suite):
        traitdb = Trait(self.conn, suite)
        path = join(self.main_path, suite, trait + '.tar')
        traitdb.insert_trait(path, suite)
        
        
    def __set_cursors__(self):
        self.main = StatementCursor(self.conn, 'main_paella_cursor')
        self.all_traits = StatementCursor(self.conn, 'all_traits')
        self.all_traits.set_table('traits')

    def __set_suite_cursors__(self, suite):
        self.traits = StatementCursor(self.conn, 'traits')
        self.traits.set_table(ujoin(suite, 'traits'))
        self.traitparent = TraitParent(self.conn, suite)
        self.traitpackage = TraitPackage(self.conn, suite)
        self.traittemplate = TraitTemplate(self.conn, suite)
        self.traitdebconf = TraitDebconf(self.conn, suite)
        

    def create(self, filename):
        for table in self.main.tables():
            self.main.execute('drop table %s' %table)
        self.parse_xml(filename)
        self.start_schema()
        for suite in self.dbdata.suites:
            self.insert_traits(suite.name)
        self.insert_profiles()


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


