from xml.dom.minidom import Element

from useless.base.xmlfile import TextElement

class ProfileVariableElement(BaseVariableElement):
    def __init__(self, trait, name, value):
        BaseVariableElement.__init__(self, 'profile_variable',
                                     trait, name, value)

class ProfileElement(Element):
    def __init__(self, name, suite):
        Element.__init__(self, 'profile')
        self.setAttribute('name', name)
        self.setAttribute('suite', suite)
        self.traits = Element('traits')
        self.appendChild(self.traits)
        self.families = Element('families')
        self.appendChild(self.families)
        self.environ = Element('environ')
        self.appendChild(self.environ)

    def append_traits(self, trait_rows):
        for trait in trait_rows:
            telement = TextElement('trait', trait.trait)
            telement.setAttribute('ord', str(trait.ord))
            self.traits.appendChild(telement)

    def append_families(self, rows):
        for row in rows:
            felement = TextElement('family', row.family)
            self.families.appendChild(felement)
            
    def append_variables(self, rows):
        for row in rows:
            velement = ProfileVariableElement(row.trait, row.name, row.value)
            self.environ.appendChild(velement)

if __name__ == '__main__':
    pass
