import os

from paella.base import Error, debug
from paella.base.util import ujoin

from paella.debian.repos import LocalRepos

from paella.sqlgen.classes import Column, Table
from paella.sqlgen.defaults import Text, DefaultNamed, Bool
from paella.sqlgen.defaults import PkBigname, Bigname, Name, Num
from paella.sqlgen.defaults import PkBignameTable, PkNameTable, PkName

from paella.sqlgen.statement import Statement
from paella.sqlgen.admin import grant_public

from paella.db.lowlevel import OperationalError
from paella.db.midlevel import StatementCursor

from paella_tables import suite_tables, primary_tables
from paella_tables import packages_columns, SCRIPTS

PRIORITIES = ['first', 'high', 'pertinent', 'none', 'postinstall', 'last']
SUITES = ['sid', 'woody'] 




plpgsql_delete_trait = """create or replace function delete_trait(varchar, varchar) returns integer as '
	begin
	execute ''delete from '' || $1 || ''_scripts where trait = '' || quote_literal($2) ;
	execute ''delete from '' || $1 || ''_templates where trait = ''|| quote_literal($2) ;
	execute ''delete from '' || $1 || ''_trait_package where trait = ''|| quote_literal($2) ;
	execute ''delete from '' || $1 || ''_trait_parent where trait = ''|| quote_literal($2) ;
	execute ''delete from '' || $1 || ''_debconf where trait = ''|| quote_literal($2) ;
	execute ''delete from '' || $1 || ''_variables where trait = ''|| quote_literal($2) ;
	execute ''delete from '' || $1 || ''_traits where trait = ''|| quote_literal($2) ;
	return 0 ;
	end ;
' language 'plpgsql';
"""

plpgsql_delete_profile = """create or replace function delete_profile(varchar)
returns integer as '
        begin
        execute ''delete from profile_variables where profile = ''|| quote_literal($1) ;
        execute ''delete from profile_trait where profile = ''|| quote_literal($1) ;
        execute ''delete from profiles where profile = ''|| quote_literal($1) ;
        return 0 ;
        end ;
' language 'plpgsql';
"""




def getcolumn(name, columns):
    ncols = [column for column in columns if column.name == name]
    if len(ncols) == 1:
        return ncols[0]
    else:
        raise Error, 'key not found'

def insert_list(cursor, table, field, list):
    for value in list:
        cursor.insert(table=table, data={field : value})

def isnonus(suite):
    if suite[-6:] == 'non-US':
        return True
    else:
        return False



def insert_more_packages(cursor, repos, suite=None):
        repos.source.set_path()
        repos.parse_release()
        table = ujoin(suite, 'packages')
        for package in repos.full_parse().values():
            try:
                cursor.insert(table, package_to_row(package))
            except OperationalError:
                pass
    
def package_to_row(packagedict, section='main'):
    pcolumns = packages_columns()
    newdict = {}.fromkeys([col.name for col in pcolumns])
    for f in ['package', 'priority', 'filename', 'md5sum',
              'version', 'description', 'size', 'maintainer']:
        try:
            newdict[f] = packagedict[f]
        except KeyError:
            newdict[f] = 'Not Applicable'
    newdict['installedsize'] = packagedict['installed-size']
    if section != 'main':
        newdict['section'] = '/'.join(section, packagedict['section'])
    else:
        newdict['section'] = packagedict['section']
    return newdict

def package_to_row_quick(packagedict, section='main'):
    newdict = {}.fromkeys([col.name for col in packages_columns])
    for f in ['package', 'priority',
              'version', 'size', 'maintainer']:
        newdict[f] = packagedict[f]
    for f in ['filename', 'md5sum', 'description']:
        newdict[f] = '_get_rid_of_me_'
    newdict['installedsize'] = packagedict['installed-size']
    if section != 'main':
        newdict['section'] = '/'.join(section, packagedict['section'])
    else:
        newdict['section'] = packagedict['section']
    return newdict

def insert_suite_packages(cursor, repos):
    suite = repos.source.suite
    if isnonus(suite):
        suite = suite.split('/')[0]
    table = ujoin(suite, 'packages')
    for section in repos.source.sections:
        for package in repos.full_parse(section).values():
            cursor.insert(table, package_to_row(package))


def make_suite(cursor, suite):
    tables = suite_tables(suite)
    map(cursor.create_table, tables)
    cursor.execute(grant_public([x.name for x in tables]))

def insert_packages(cursor, suite):
    source = 'deb file:/mirrors/debian %s main contrib non-free' %suite
    rp = LocalRepos(source)
    rp.parse_release()
    insert_suite_packages(cursor, rp)
    suites = cursor.as_dict('suites', 'suite')
    if suites[suite]['nonus'] == True:
        rp.source.suite += "/non-US"
        rp.source.set_path()
        rp.parse_release()
        insert_suite_packages(cursor, rp)
    if suites[suite]['local'] == True:
        rp = LocalRepos(source)
        rp.source.sections = []
        rp.source.uri = os.path.join(rp.source.uri, 'local')
        rp.source.suite += '/'
        insert_more_packages(cursor, rp, suite=suite)
    if suites[suite]['common'] == True:
        rp = LocalRepos(source)
        rp.source.sections = []
        rp.source.uri = os.path.join(rp.source.uri, 'local')
        rp.source.suite = 'common/'
        insert_more_packages(cursor, rp, suite=suite)

def start_schema(conn):
    cursor = StatementCursor(conn, 'start_schema')
    tables, mapping = primary_tables()
    map(cursor.create_table, tables)
    priorities_table = mapping['priorities']
    insert_list(cursor, priorities_table.name, 'priority', PRIORITIES)
    insert_list(cursor, 'scriptnames', 'script', SCRIPTS)
    cursor.execute(grant_public([x.name for x in tables]))
    cursor.execute(grant_public(['current_environment'], 'ALL'))
    cursor.execute(grant_public(['partition_workspace'], 'ALL'))
    cursor.execute(plpgsql_delete_profile)
    cursor.execute(plpgsql_delete_trait)
    

def create_database(cfg, default_traits):
    dsn = cfg.get_dsn()
    dsn['dbname'] = 'mishmash'
    conn = QuickConn(dsn)
    cmd = StatementCursor(conn, 'create_database')
    for table in cmd.tables():
        cmd.execute('drop table %s' %table)
    start_schema(conn, default_traits)
    make_suites(conn)
    cmd.execute(grant_public(cmd.tables()))
    cmd.execute(grant_public(['current_environment'], 'ALL'))
    
    
    
def doall(conn, filename):
    start_schema(conn, filename)
    parse_xmldb(conn, filename)


if __name__ == '__main__':
    from paella.db.lowlevel import QuickConn
    from paella.db.midlevel import StatementCursor
    from paella.debian.base import parse_packages, full_parse
    #cmd = CommandCursor(c, 'dsfsdf')
    def dtable():
        cmd.execute('drop table ptable')

    def dtables():
        for t in cmd.tables():
            if t != 'footable':
                cmd.execute('drop table %s' %t)


    #start_schema(cmd, traits)
    #rp = Repos('/mirrors/debian')
    #ps = rp.parse('contrib')
    #prows = [package_to_row(p) for p in ps.values()]
    from paella.profile.base import PaellaConnection
    from pyPgSQL.PgSQL import Connection, Cursor, PgLargeObject
    conn = PaellaConnection()
    cursor = StatementCursor(conn)

