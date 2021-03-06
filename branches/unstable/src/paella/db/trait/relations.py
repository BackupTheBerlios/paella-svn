from os.path import join
from sets import Set

from kjbuckets import kjGraph

from useless.base import Error
from useless.base.util import ujoin, RefDict, strfile, filecopy

from useless.sqlgen.clause import one_many, Eq, In
from useless.db.midlevel import Environment

from paella.base.objects import TextFileManager

from base import TraitRelation
from base import Template

class TraitEnvironment(Environment):
    def __init__(self, conn, suite, trait):
        self.suite = suite
        table = ujoin(suite, 'variables')
        Environment.__init__(self, conn, table, 'trait')
        self.set_main(trait)


class TraitParent(TraitRelation):
    def __init__(self, conn, suite):
        table = ujoin(suite, 'trait', 'parent')
        TraitRelation.__init__(self, conn, suite, table, name='TraitParent')
        self.graph = kjGraph([(r.trait, r.parent) for r in self.cmd.select()])

    def get_traitset(self, traits):
        dtraits = Set()
        for trait in traits:
            dtraits |=  Set([trait]) | Set(self.graph.reachable(trait).items())
        return dtraits

    def get_environment(self, traits):
        assoc_traits = list(self.get_traitset(traits))
        c, s = self.conn, self.suite
        return [(t, TraitEnvironment(c, s, t)) for t in assoc_traits]


    def get_superdict(self, traits, sep='_'):
        env = TraitEnvironment(self.conn, self.suite, traits[0])
        superdict = RefDict()
        for trait in traits:
            env.set_main(trait)
            items = [(trait+sep+key, value) for key, value in env.items()]
            superdict.update(dict(items))
        return superdict

    def Environment(self):
        traits = list(self.get_traitset([self.current_trait]))
        return self.get_superdict(traits)

    def parents(self, trait=None):
        if trait is None:
            trait = self.current_trait
        self.set_clause(trait)
        rows = self.cmd.select(fields=['parent'], order='parent')
        self.reset_clause()
        return rows
    
    def insert_parents(self, parents):
        self.insert('parent', parents)

    def delete(self, parents=[]):
        print parents, 'PARENTS'
        clause = In('parent', parents) & Eq('trait', self.current_trait)
        self.cmd.delete(clause=clause)
        self.reset_clause()

    def delete_trait(self, trait=None):
        if trait is None:
            trait = self.current_trait
        clause = Eq('trait', trait)
        self.cmd.delete(clause=clause)
        self.reset_clause()
        
        
class TraitTemplate(TraitRelation):
    def __init__(self, conn, suite):
        table = ujoin(suite, 'templates')
        TraitRelation.__init__(self, conn, suite, table, name='TraitTemplate')
        self.traitparent = TraitParent(conn, suite)
        self.template = Template()
        self.template.set_suite(suite)
        self.template_path = None
        self.textfiles = TextFileManager(self.conn)
        self._jtable = '%s as s join textfiles as t ' % table
        self._jtable += 'on s.templatefile = t.fileid' 

    def _clause(self, package, template, trait=None):
        if trait is None:
            trait = self.current_trait
        return Eq('trait', trait) & Eq('package', package) & Eq('template', template)
    
    def templates(self, trait=None, fields=['*']):
        if trait is None:
            trait = self.current_trait
            self.reset_clause()
            return self.cmd.select(fields=fields, order=['package', 'template'])
        else:
            self.set_clause(trait)
            rows = self.cmd.select(fields=fields, order=['package', 'template'])
            self.reset_clause()
            return rows

    def has_template(self, template):
        return self.has_it('template', template)

    def get_row(self, template):
        return _TraitRelation.get_row(self, 'template', template)

    def insert_template(self, data, templatefile):
        if type(data) is not dict:
            raise Error, 'Need to pass dict'
        if len(data) == 2 and 'template' in data and 'package' in data:
            data.update(dict(owner='root', grp_owner='root', mode='0100644'))
        insert_data = {'trait' : self.current_trait}
        insert_data.update(data)
        id = self.textfiles.insert_file(templatefile)
        insert_data['templatefile'] = str(id)
        self.cmd.insert(data=insert_data)

    def update_template(self, data, templatefile):
        clause = self._clause(data['package'], data['template'])
        id = self.textfiles.insert_file(templatefile)
        fields = ['owner', 'grp_owner', 'mode']
        update = {}.fromkeys(fields)
        for field in update:
            update[field] = data[field]
        update['templatefile'] = str(id)
        self.cmd.update(data=update, clause=clause)
        self.reset_clause()

    def update_templatedata(self, package, template, data):
        clause = self._clause(package, template)
        id = self.textfiles.insert_data(data)
        self.cmd.update(data=dict(templatefile=str(id)), clause=clause)
        

    def drop_template(self, package, template):
        clause = self._clause(package, template)
        self._drop_template(clause)
        
    def _drop_template(self, clause):
        self.cmd.delete(clause=clause)
        self.reset_clause()

    def set_trait(self, trait):
        TraitRelation.set_trait(self, trait)
        self.traitparent.set_trait(trait)
        self.template.set_trait(trait)
        
    def set_template(self, package, template):
        self.template.set_template(self.templatefile(package, template))
        self.template.update(self.traitparent.Environment())

    def set_template_path(self, path):
        self.template_path = join(path, self.suite, self.current_trait)
        
        
    def export_templates(self, bkup_path):
        n = 0
        for t in self.templates():
            npath = join(bkup_path, 'template-%d' % n)
            tfile = self.templatefile(t.package, t.template)
            filecopy(tfile, npath)
            tfile.close()
            n += 1
            
    def templatefile(self, package, template):
        return strfile(self.templatedata(package, template))
    
    def templatedata(self, package, template):
        return self._template_row(package, template).data

    def _template_row(self, package, template):
        table = self._jtable
        clause = self._clause(package, template)
        return self.cmd.select_row(fields=['data', 'templatefile'], table=table, clause=clause)

    def _template_id(self, package, template):
        return self._template_row(package, template).templatefile

    def save_template(self, package, template, templatefile):
        id = self.textfiles.insert_file(templatefile)
        clause = self._clause(package, template)
        self.cmd.update(data=dict(templatefile=str(id)), clause=clause)

class TraitScript(TraitRelation):
    def __init__(self, conn, suite):
        table = ujoin(suite, 'scripts')
        TraitRelation.__init__(self, conn, suite, table, name='TraitScript')
        self.textfiles = TextFileManager(self.conn)
        self._jtable = '%s as s join textfiles as t ' % table
        self._jtable += 'on s.scriptfile = t.fileid' 
        
    def scripts(self, trait=None):
        if trait is None:
            trait = self.current_trait
        self.set_clause(trait)
        rows = self.cmd.select(fields=['script'], order='script')
        self.reset_clause()
        return rows

    def scriptfile(self, name):
        return strfile(self.scriptdata(name))
            
    def _script_row(self, name):
        table = self._jtable
        clause = self._clause(name)
        return self.cmd.select_row(fields=['data'], table=table, clause=clause)
        
    def _script_id(self, name):
        return self._script_row(name).scriptfile
        
    def scriptdata(self, name):
        return self._script_row(name).data
        
    def save_script(self, name, scriptfile):
        id = self.textfiles.insert_file(scriptfile)
        clause = self._clause(name)
        self.cmd.update(data=dict(scriptfile=str(id)), clause=clause)

    def remove_scriptfile(self, name):
        print 'remove_scriptfile deprecated'

    def _clause(self, name, trait=None):
        if trait is None:
            trait = self.current_trait
        return Eq('trait', trait) & Eq('script', name)

    def get(self, name):
        clause = self._clause(name)
        rows = self.cmd.select(clause=clause)
        if len(rows) == 1:
            return self.scriptfile(name)
        else:
            return None

    def read_script(self, name):
        return self.scriptdata(name)
    
    def insert_script(self, name, scriptfile):
        insert_data = {'trait' : self.current_trait,
                       'script' : name}
        id = self.textfiles.insert_file(scriptfile)
        insert_data['scriptfile'] = str(id)
        self.cmd.insert(data=insert_data)

    def update_script(self, name, scriptfile):
        id = self.textfiles.insert_file(scriptfile)
        clause = self._clause(name)
        data = dict(scriptfile=str(id))
        self.cmd.update(data=data, clause=clause)

    def update_scriptdata(self, name, data):
        clause = self._clause(name)
        id = self.textfiles.insert_data(data)
        self.cmd.update(data=dict(scriptfile=str(id)), clause=clause)

    def export_scripts(self, bkup_path):
        for row in self.scripts():
            npath = join(bkup_path, 'script-%s' % row.script)
            nfile = self.scriptfile(row.script)
            filecopy(nfile, npath)
            nfile.close()

class TraitPackage(TraitRelation):
    def __init__(self, conn, suite):
        table = ujoin(suite, 'trait', 'package')
        TraitRelation.__init__(self, conn, suite, table, name='TraitPackage')
        self.cmd.set_fields(['package', 'action'])
        self.traitparent = TraitParent(conn, suite)
        
    def packages(self, traits=None):
        if traits is None:
            traits = [self.current_trait]
        #self.cmd.set_clause([('trait', trait) for trait in traits], join='or')
        clause = In('trait', traits)
        rows =  self.cmd.select(clause=clause, order='package')
        self.reset_clause()
        return rows
    
    def all_packages(self, traits, traitparent=None):
        if not traitparent:
            traitparent = self.traitparent
        return list(self.packages(traitparent.get_traitset(traits)))

    def set_action(self, action, packages, trait=None):
        if trait is None:
            trait = self.current_trait
        clause = Eq('trait', trait) & In('package', packages)
        if action == 'drop':
            self.cmd.delete(clause=clause)
        elif action in ['remove', 'install', 'purge']:
            self.cmd.set_data({'action' : action})
            self.cmd.update(clause=clause)
        else:
            raise Error, 'bad action in TraitPackage -%s-' % action

    def insert_package(self, package, action='install'):
        idata = {'trait' : self.current_trait,
                 'action' : action,
                 'package' : package}
        self.cmd.insert(data=idata)

    def insert_packages(self, packages):
        diff = self.diff('package', packages)
        for package in packages:
            if package in diff:
                self.insert_package(package)
        

    def set_trait(self, trait):
        TraitRelation.set_trait(self, trait)
        self.traitparent.set_trait(trait)

if __name__ == '__main__':
    #f = file('tmp/trait.xml')
    #tx = TraitXml(f)
    import sys
