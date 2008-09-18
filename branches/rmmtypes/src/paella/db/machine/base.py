from useless.base import NoExistError
from useless.sqlgen.clause import Eq

from paella.base.util import edit_dbfile


def Table_cursor(conn, table):
    cursor = conn.cursor(statement=True)
    cursor.set_table(table)
    return cursor

class Machine(object):
    def __init__(self, name):
        object.__init__(self)
        self.name = name
        self.parent = None
        self.kernel = None
        self.diskconfig = None
        self.scripts = []
        self.families = []
        self.variables = []

    def __repr__(self):
        return '<Machine:  %s>' % self.name

    def append_modules(self, modules):
        self.modules = modules

    def append_script(self, name, data):
        self.scripts.append((name, data))

    def append_family(self, family):
        self.families.append(family)

    def append_variable(self, trait, name, value):
        self.variables.append((trait, name, value))
        
class DiskConfigHandler(object):
    def __init__(self, conn):
        self.conn = conn
        self.cursor = self.conn.cursor(statement=True)
        self.cursor.set_table('diskconfig')

    def get(self, name):
        clause = Eq('name', name)
        return self.cursor.select_row(clause=clause)

    def set(self, name, data=None):
        if data is None:
            data = {}
        insert = False
        try:
            self.get(name)
        except NoExistError:
            insert = True
        if insert:
            data['name'] = name
            self.cursor.insert(data=data)
        else:
            clause = Eq('name', name)
            self.cursor.update(data=data, clause=clause)

    def delete(self, name):
        clause = Eq('name', name)
        self.cursor.delete(clause=clause)

    def edit_diskconfig(self, name):
        row = self.get(name)
        content = row.content
        if content is None:
            content = ''
        data = edit_dbfile(name, content, 'diskconfig')
        if data is not None:
            self.set(name, data=dict(content=data))
            

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

    def _machine_clause_(self, machine=None):
        if machine is None:
            self._check_machine_set()
            machine = self.current_machine
        return Eq('machine', machine)
    
class BaseMachineHandler(BaseMachineDbObject):
    def __init__(self, conn):
        BaseMachineDbObject.__init__(self, conn, table='machines')
        self.kernels = Table_cursor(self.conn, 'kernels')
        self.diskconfig = DiskConfigHandler(self.conn)
        
    def approve_machine_ids(self):
        self._check_machine_set()
        machine = self.current_machine
        table = 'current_environment'
        clause = "name like 'hwaddr_%'" + " and value='%s'" % machine
        fields = ["'machines' as section", 'name as option', 'value']
        rows = self.cursor.select(fields=fields, table=table, clause=clause)
        for row in rows:
            self.cursor.insert(table='default_environment', data=row)

    def set_autoinstall(self, auto=True):
        self._check_machine_set()
        if auto:
            value = 'True'
        else:
            value = 'False'
        machine = self.current_machine
        table = 'default_environment'
        data = dict(section='autoinstall', option=machine, value=value)
        clause = Eq('section', 'autoinstall') & Eq('option', machine)
        rows = self.cursor.select(table=table, clause=clause)
        if not len(rows):
            self.cursor.insert(table=table, data=data)
        elif len(rows) == 1:
            self.cursor.update(table=table, data=dict(value=value),
                               clause=clause)
        else:
            raise Error, 'too many rows for this machine: %s' % machine
        
        
    def _update_row(self, data):
        self._check_machine_set()
        self.cursor.update(data=data, clause=self._machine_clause_())
        
    def set_profile(self, profile):
        data = dict(profile=profile)
        self._update_row(data)

    def set_kernel(self, kernel):
        kernels = [r.kernel for r in self.kernels.select()]
        data = dict(kernel=kernel)
        if kernel not in kernels:
            self.kernels.insert(data=data)
        self._update_row(data)

    def set_diskconfig(self, diskconfig):
        data = dict(diskconfig=diskconfig)
        self._update_row(data)
        

if __name__ == '__main__':
    pass

    
