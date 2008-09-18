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
from base import BaseMachineDbObject
from base import Table_cursor


import warnings
class NotReadyYetWarning(Warning):
    pass

warnings.simplefilter('always', NotReadyYetWarning)

class MachineVariablesConfig(VariablesConfig):
    def __init__(self, conn, machine):
        VariablesConfig.__init__(self, conn, 'machine_variables',
                                 'trait', 'machine', machine)


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
    
            
class MachineScripts(ScriptCursor, BaseMachineDbObject):
    def __init__(self, conn):
        msg = "MachineScripts is really ready yet"
        warnings.warn(msg, NotReadyYetWarning, stacklevel=3)
        ScriptCursor.__init__(self, conn, 'machine_scripts', 'machine')
        # we need this from BaseMachineDbObject
        # but we can't call BaseMachineDbObject.__init__
        # since this class is subclassed from a cursor
        self.current_machine = None
        # we hope that having this cursor in a cursor
        # doesn't cause problems.  We really need
        # to consider turning the ScriptCursor into
        # a subclass of object and including a cursor
        # member.
        self.cursor = conn.cursor(statement=True)
        self._parents = MachineParents(conn)
        

    def set_machine(self, machine):
        BaseMachineDbObject.set_machine(self, machine)
        self._parents.set_machine(machine)
        
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

class MachineFamily(BaseMachineDbObject):
    def __init__(self, conn):
        BaseMachineDbObject.__init__(self, conn, table='machine_family')
        self._parents = MachineParents(self.conn)
        
    def set_machine(self, machine):
        BaseMachineDbObject.set_machine(self, machine)
        self._parents.set_machine(machine)
        
    def family_rows(self, machine=None):
        if machine is None:
            self._check_machine_set()
            machine = self.current_machine
        clause = Eq('machine', machine)
        return self.cursor.select(clause=clause, order='family')

    def delete_family(self, family, machine=None):
        if machine is None:
            self._check_machine_set()
            machine = self.current_machine
        clause = Eq('machine', machine) & Eq('family', family)
        self.cursor.delete(clause=clause)

    def append_family(self, family, machine=None):
        if machine is None:
            self._check_machine_set()
            machine = self.current_machine
        data = dict(machine=machine, family=family)
        self.cursor.insert(data=data)

    def get_families(self, machine=None):
        rows = self.family_rows(machine=machine)
        return [row.family for row in rows]
        
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
    
class MachineRelations(BaseMachineDbObject):
    "Class to hold the relations"
    def __init__(self, conn):
        BaseMachineDbObject.__init__(self, conn, table='machines')
        self.parents = MachineParents(self.conn)
        self.scripts = MachineScripts(self.conn)
        self.family = MachineFamily(self.conn)
        self.environment = MachineEnvironment(self.conn)
        self.config = None
        # These aren't really actual relations in the
        # same sense that the above objects are
        # but they are objects the the machines
        # table relates to, and should fit nicely in this
        # class.
        self.diskconfig = DiskConfigHandler(self.conn)
        self.kernels = Table_cursor(self.conn, 'kernels')
        
    def set_machine(self, machine):
        BaseMachineDbObject.set_machine(self, machine)
        self.parents.set_machine(machine)
        self.scripts.set_machine(machine)
        self.family.set_machine(machine)
        self.diskconfig.set_machine(machine)
        self.environment.set_machine(machine)
        self.config = MachineVariablesConfig(self.conn, machine)

        
if __name__ == '__main__':
    from os.path import join
    from paella.db import PaellaConnection
    conn = PaellaConnection()
    pmtypes = ['ggf', 'gf', 'f', 's', 'gs', 'ggs']
    mp = MachineTypeParent(conn)
    mt = MachineTypeHandler(conn)
    
