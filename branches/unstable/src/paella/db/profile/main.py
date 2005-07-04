#import os
#from os.path import join, dirname, isdir
#from sets import Set

#from xml.dom.minidom import Element
#from xml.dom.minidom import parse as parse_file
#from xml.dom.minidom import parseString as parse_string

#from useless.base import UnbornError, Error, debug
#from useless.base.xmlfile import TextElement
#from useless.base.util import ujoin, makepaths

#from useless.sqlgen.clause import Eq

#from useless.db.midlevel import StatementCursor, SimpleRelation
#from useless.db.midlevel import Environment
#from useless.db.lowlevel import OperationalError

#from paella.schema.paellascheme import insert_packages, make_suite
#from paella.schema.paellascheme import start_schema

#from base import TraitEnvironment, get_suite, make_deplist
#from trait import TraitParent, TraitDebconf
#from trait import TraitPackage, TraitTemplate
#from trait import TraitsElement, Trait
#from family import Family

#from xmlparse import PaellaParser, ProfilesParser, ProfileParser
#from xmlgen import EnvironElement, SuitesElement
#from xmlgen import SuiteElement, ProfileElement
#from xmlgen import ProfileVariableElement

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
        rows = self.cmd.select(fields=['trait', 'ord'], order=['ord', 'trait'])
        self.reset_clause()
        return rows
        
    def insert_trait(self, trait, ord='0'):
        idata = dict(profile=self.current, trait=trait, ord=ord)
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
            
        
    def _make_superdict__orig_(self):
        clause = Eq('profile', self.profile)
        superdict = {}
        traits = [row.trait for row in self.cursor.select(fields=['trait'], clause=clause)]
        for trait in traits:
            self.set_trait(trait)
            items = [(trait + '_' + key, value) for key, value in self.items()]
            superdict.update(dict(items))
        return superdict

    def _make_superdict_(self):
        clause = Eq('profile', self.profile)
        return Environment._make_superdict_(self, clause)
    
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

class Profile(StatementCursor):
    def __init__(self, conn):
        StatementCursor.__init__(self, conn)
        self.conn = conn
        self.set_table('profiles')
        self._traits = ProfileTrait(conn)
        self._env = ProfileEnvironment(conn)
        self._pfam = StatementCursor(conn)
        self._pfam.set_table('profile_family')
        self._fam = Family(conn)
        
    def drop_profile(self, profile):
        self.delete(clause=Eq('profile', profile))

    def set_profile(self, profile):
        self.clause = Eq('profile', profile)
        self.current = self.select_row(clause=self.clause)
        self._traits.set_profile(profile)
        self._env.set_profile(profile)
        
    def get_profile_data(self):
        return self._env.ProfileData()

    def get_family_data(self):
        families = self.get_families()
        return self._fam.FamilyData(families)
    
    def make_traitlist(self, log=None):
        tp = TraitParent(self.conn, self.current.suite)
        listed = [x.trait for x in self._traits.trait_rows()]
        all = list(tp.get_traitset(listed))
        setfun = tp.set_trait
        parfun = tp.parents
        return make_deplist(listed, all, setfun, parfun, log)

    def family_rows(self, profile=None):
        if profile is None:
            profile = self.current.profile
        return self._pfam.select(clause=Eq('profile', profile), order='family')
    

    def get_families(self, profile=None):
        return [r.family for r in self.family_rows(profile)]
    

    def get_trait_rows(self):
        return self._traits.trait_rows()
    
    def append_family(self, family):
        if family not in self.get_families():
            self._pfam.insert(data=dict(profile=self.current.profile, family=family))

    def append_trait(self, trait, ord):
        self._traits.insert_trait(trait, ord)
        
    def set_suite(self, suite):
        clause = Eq('profile', self.current.profile)
        self.update(data=dict(suite=suite), clause=clause)
        self.set_profile(self.current.profile)

    def copy_profile(self, src, dest):
        current = self.current
        self.set_profile(src)
        pfield = "'%s' as profile" % dest
        pclause = Eq('profile', src)
        pcursor = self
        tcursor = self._traits.cmd
        fcusor = self._pfam
        vcursor = self._env.env.cursor
        cursors = [ pcursor, tcursor, fcusor, vcursor]
        for cursor in cursors:
            sel = str(cursor.stmt.select(fields = [pfield] + cursor.fields()[1:], clause=pclause))
            cursor.execute('insert into %s (%s)' % (cursor.stmt.table, sel))
        self.set_profile(current.profile)
            

    def get_profile_list(self, suite=None):
        if suite is None:
            plist = [r.profile for r in self.select()]
        elif suite == 'all':
            plist = [(r.profile, r.suite) for r in self.select()]
        else:
            clause = Eq('suite', suite)
            plist = [r.profile for r in self.select(clause=clause)]
        return plist
    
    
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
        self._profile = Profile(self.conn)
        
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
        element.append_families(self._profile.family_rows(profile))
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
        idata = dict(profile=profile.name)
        for family in profile.families:
            idata['family'] = family
            self.stmt.insert(table='profile_family', data=idata)
        idata = dict(profile=profile.name)
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
        
        

if __name__ == '__main__':
    pass
