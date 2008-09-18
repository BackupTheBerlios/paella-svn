import os
from os.path import join
from xml.dom.minidom import parseString

from useless.base.xmlfile import ParserHelper
from useless.base import Error

from base import Machine

def get_child(element):
    return element.firstChild.data.encode().strip()

def get_attribute(attribute, element):
    return element.getAttribute(attribute).encode().strip()

def parse_module(element):
    module = get_child(element)
    order = get_attribute('order', element)
    return int(order), module

def parse_machine(element):
    name = get_child(element)
    mtype = get_attribute('machine_type', element)
    kernel = get_attribute('kernel', element)
    profile = get_attribute('profile', element)
    return Machine(name, mtype, kernel, profile)

class MachineParser(ParserHelper):
    def __init__(self, element):
        ParserHelper.__init__(self)
        self.name = element.getAttribute('name')
        self.machine = Machine(self.name)
        for attr in ['parent', 'diskconfig', 'kernel', 'profile']:
            setattr(self, attr, None)
            if element.hasAttribute(attr):
                setattr(self, attr, element.getAttribute(attr))
            setattr(self.machine, attr, getattr(self, attr))
        mods = element.getElementsByTagName('module')
        fams = element.getElementsByTagName('family')
        scripts = element.getElementsByTagName('script')
        vars_ = element.getElementsByTagName('machine_variable')
        
        for f in fams:
            family = get_child(f)
            self.machine.append_family(family)
        for s in scripts:
            name = s.getAttribute('name')
            self.machine.append_script(name, name)
        for v in vars_:
            trait = v.getAttribute('trait')
            name = v.getAttribute('name')
            value = get_child(v)
            self.machine.append_variable(trait, name, value)
            
class MachineDatabaseParser(ParserHelper):
    def __init__(self, path, element):
        ParserHelper.__init__(self)
        self.path = path
        self.mtypepath = join(path, 'machine_types')
        
        name = element.tagName.encode()
        get_em = self.get_elements_from_section
        self.kernels = map(get_child, get_em(element, 'kernels', 'kernel'))
        self.machines = map(parse_machine, get_em(element, 'machines', 'machine'))
        

if __name__ == '__main__':
    pass

