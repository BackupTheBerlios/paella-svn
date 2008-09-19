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
        self.relation = MachineRelations(self.conn)
        self.family = Family(self.conn)
        self.parent = None
        self.diskconfig = None
        self.kernel = None
        
    def set_machine(self, machine):
        BaseMachineHandler.set_machine(self, machine)
        self.relation.set_machine(machine)
        self.parent = self.relation.parents.get_parent()
        
    def add_new_kernel(self, kernel):
        if self._check_kernel_exists(kernel):
            self.relation.kernels.insert(data=dict(kernel=kernel))
        else:
            msg = "There's no kernel named %s in the package list" % kernel
            raise RuntimeError , msg
            
    def make_a_machine(self, machine):
        data = dict(machine=machine)
        self.cursor.insert(table='machines', data=data)

    def set_parent(self, parent):
        self._check_machine_set()
        self.relation.parents.set_parent(parent)
        # reset the attributes here
        self.set_machine(self.current_machine)

    def _get_attribute(self, attribute, show_inheritance=False):
        self._check_machine_set()
        attribute_value = getattr(self, attribute)
        if attribute_value is None:
            return self.relation.get_attribute(attribute, show_inheritance=show_inheritance)
        if show_inheritance:
            return attribute_value, None
        else:
            return attribute_value

    #########################
    # for these methods, inheritance
    # is presumed, if you only need
    # the values set for the current
    # machine, just use the attribute
    # values -> self.attribute
    #########################
    def get_diskconfig(self, show_inheritance=False):
        return self._get_attribute('diskconfig', show_inheritance=show_inheritance)

    def get_kernel(self, show_inheritance=False):
        return self._get_attribute('kernel', show_inheritance=show_inheritance)

    def get_profile(self, show_inheritance=False):
        return self._get_attribute('profile', show_inheritance=show_inheritance)

    #########################
    #########################
    
    def get_diskconfig_content(self):
        diskconfig = self.get_diskconfig()
        content = self.relation.diskconfig.get(diskconfig).content
        return content
    
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
