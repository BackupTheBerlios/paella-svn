from os.path import join
from xml.dom.minidom import parseString

from useless import deprecated
from useless.base.util import strfile
from useless.base import NoExistError
from useless.db.midlevel import StatementCursor, Environment
from useless.sqlgen.clause import Eq

from paella.base.util import edit_dbfile
from paella.base.objects import VariablesConfig
from paella.db.base import ScriptCursor
from paella.db.family import Family

from base import DiskConfigHandler
from xmlgen import MachineTypeElement
from xmlparse import MachineTypeParser

class MachineVariablesConfig(VariablesConfig):
    def __init__(self, conn, machine):
        VariablesConfig.__init__(self, conn, 'machine_variables',
                                 'trait', 'machine', machine)

class BaseMachineDbObject(object):
    def __init__(self, conn, table=None):
        self.conn = conn
        self.cursor = self.conn.cursor(statement=True)
        self.current_machine = None
        if table is not None:
            self.cursor.set_table(table)
            
    def set_machine(self, machine):
        self.current_machine = machine

    def _check_machine_set(self):
        if self.current_machine is None:
            name = self.__class__.__name__
            raise RuntimeError , "Machine isn't set in %s" % name

# Unlike, traits and families, a machine
# can only have one parent.
class MachineParents(BaseMachineDbObject):
    def __init__(self, conn):
        BaseMachineDbObject.__init__(self, conn, table='machine_parent')
        
    def get_parent(self, machine=None):
        if machine is None:
            self._check_machine_set()
            machine = self.current_machine
        clause = Eq('machine', machine)
        try:
            row = self.cursor.select_row(clause=clause)
            return row.parent
        except NoExistError:
            return None
    
    def set_parent(self, parent, machine=None):
        data = dict(parent=parent)
        if machine is None:
            self._check_machine_set()
            machine = self.current_machine
        if parent == machine:
            raise RuntimeError , "Machine can't be it's own parent"
        if self.get_parent(machine=machine) is None:
            # if there's not already a parent we
            # insert a new one
            data['machine'] = machine
            self.insert(data=data)
        else:
            # else we update it
            clause = Eq('machine', machine)
            self.update(data=data, clause=clause)

    def get_parent_list(self, childfirst=True, machine=None):
        if machine is None:
            self._check_machine_set()
            machine = self.current_machine
        parents = []
        parent = self.get_parent(machine=machine)
        while parent is not None:
            parents.append(parent)
            parent = self.get_parent(machine=parent)
        if not childfirst:
            parents.reverse()
        return parents
    
            
class MachineScripts(ScriptCursor):
    def __init__(self, conn):
        raise RuntimeError , "MachineScripts is ready yet"
        ScriptCursor.__init__(self, conn, 'machine_scripts', 'machine')
        self.current_machine = None
        
    def _clause(self, name, machine=None):
        if machine is None:
            self._check_machine_set()
            machine = self.current_machine
        clause = Eq(self._keyfield, machine) & Eq('script', name)

    def insert_script(self, name, scriptfile, machine=None):
        if machine is None:
            self._check_machine_set()
            machine = self.current_machine
        self._insert_script(name, scriptfile, machine)

    def scripts(self, machine=None):
        if machine is None:
            self._check_machine_set()
            machine = self.current_machine
        clause  = Eq('machine', machine)
        return self.select(clause=clause)
    
class MachineEnvironment(BaseMachineDbObject, Environment):
    def __init__(self, conn):
        BaseMachineDbObject.__init__(self, conn, table='machine_variables')
        Environment.__init__(self, conn, 'machine_variables', 'machine')
        self._parents = MachineParents(self.conn)

    def set_machine(self, machine):
        BaseMachineDbObject.set_machine(self, machine)
        self._parents.set_machine(machine)
        
    def _single_clause_(self):
        return Eq('machine', self.current_machine) & Eq('trait', self.__main_value__)

    def _make_superdict_(self):
        self._check_machine_set()
        parents = self._parents.get_parent_list(childfirst=False)
        env = {}
        for parent in parents:
            clause = Eq('machine', parent)
            env.update(Environment._make_superdict_(self, clause))
        clause = self._mtype_clause()
        env.update(Environment._make_superdict_(self, clause))
        return env
    
        
if __name__ == '__main__':
    from os.path import join
    from paella.db import PaellaConnection
    conn = PaellaConnection()
    pmtypes = ['ggf', 'gf', 'f', 's', 'gs', 'ggs']
    mp = MachineTypeParent(conn)
    mt = MachineTypeHandler(conn)
    
