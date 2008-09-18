from os.path import join
from xml.dom.minidom import parseString

from useless.base import NoExistError
from useless.base.path import path

from useless.db.midlevel import StatementCursor
from useless.sqlgen.clause import Eq

from paella.db.family import Family

from base import DiskConfigHandler
from base import BaseMachineHandler
from relations import MachineRelations
from xmlparse import MachineDatabaseParser
from xmlgen import MachineDatabaseElement

class MachineHandler(BaseMachineHandler):
    def __init__(self, conn):
        BaseMachineHandler.__init__(self, conn)
        self.rel = MachineRelations(self.conn)
        self.family = Family(self.conn)
        self.parent = None
        self.diskconfig = None
        self.kernel = None
        
    def set_machine(self, machine):
        BaseMachineHandler.set_machine(self, machine)
        self.rel.set_machine(machine)
        
    def add_new_kernel(self, kernel):
        if self._check_kernel_exists(kernel):
            self.rel.kernels.insert(data=dict(kernel=kernel))
        else:
            msg = "There's no kernel named %s in the package list" % kernel
            raise RuntimeError , msg
            
    def make_a_machine(self, machine):
        data = dict(machine=machine)
        self.cursor.insert(table='machines', data=data)
    

    ############################
    # old methods below --
    # either replace or rework
    ############################
    def insert_parsed_element(self, element):
        for kernel in element.kernels:
            self.add_new_kernel(kernel)
        return None

    def old_insert_parsed_element(self, element):
        map(self.add_new_kernel, element.kernels)
        for mtype in element.mtypes:
            print 'mtype is', mtype
            #self.mtype.insert_parsed_element(mtype)
            self.mtype.import_machine_type(element, mtype)
            
        for machine in element.machines:
            data = {}
            data.update(machine)
            del data['name']
            data['machine'] = machine['name']
            self.cursor.insert(table='machines', data=data)

    def parse_xmlfile(self, filename):
        filename = path(filename).abspath()
        element = parseString(file(filename).read())
        dirname = filename.dirname()
        return MachineDatabaseParser(dirname, element.firstChild)
    
    def restore_machine_database(self, dirname):
        mdbfilename = path(dirname) /  'machine_database.xml'
        parsed = self.parse_xmlfile(mdbfilename)
        self.insert_parsed_element(parsed)
        
    def export_machine_database(self, dirname):
        me = MachineDatabaseElement(self.conn)
        mdfilename = path(dirname) / 'machine_database.xml'
        mdfile = file(mdfilename, 'w')
        machine_dirname = dirname / 'machines'
        mdfile.write(me.toprettyxml())
        mdfile.close()
        for machine in me.machines:
            name = machine.getAttribute('name')
            self.set_machine(name)
            self.export_machine(name, machine_dirname)
            
    def list_all_kernels(self):
        return [r.kernel for r in self.kernels.select()]

    def list_all_profiles(self):
        """convenience method for helping select a profile
        for a machine in the gui"""
        rows = self.cursor.select(table='profiles')
        return [r.profile for r in rows]

if __name__ == '__main__':
    from os.path import join
    from paella.db import PaellaConnection
    conn = PaellaConnection()
