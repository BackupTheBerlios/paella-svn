import os
#from os.path import join
#from sets import Set

#from paella.gtk.base import right_click_pressed, FlavoredTargets
#from paella.gtk.base import rowpacker, set_receive_targets
#from paella.gtk.simple import SimpleMenu, MyCombo, SimpleMenuBar
#from paella.gtk import dialogs
from paella.gtk.middle import ListNoteBook, ScrollCList
#from paella.gtk.windows import CommandBoxWindow
#from paella.gtk.helpers import make_menu, right_click_menu, HasDialogs

#from gtk import mainloop, mainquit
#from gtk import MenuBar

#from gtk.gdk import ACTION_COPY, ACTION_MOVE
#from gtk.gdk import BUTTON1_MASK

#from paella.base import debug
#from paella.base.util import ujoin, makepaths
#from paella.db.midlevel import StatementCursor, TableDict
#from paella.sqlgen.statement import Statement
#from paella.sqlgen.select import SimpleClause
#from paella.sqlgen.clause import one_many, Eq, In, NotIn

#from paella.profile.base import PaellaConnection, PaellaConfig
#from paella.profile.trait import TraitPackage, TraitParent
#from paella.profile.trait import Trait

from traitgen import DragListWindow

def substring(field, substr):
    return 'substring(%s from 1 for %s)' %(field, len(substr))
def substring_clause(section):
    return "%s = '%s'" %(substring('section', section), section)


class FamilyBrowser(ListNoteBook):
    def __init__(self, conn, suite):
        self.menu = make_menu(['delete'], self.modify_family)
        ListNoteBook.__init__(self)
        self.conn = conn
        self.suite = suite
        self.trait = Trait(self.conn, self.suite)
        self.package_menu = make_menu(['install', 'remove', 'purge', 'drop'],
                              self.set_package)
        self.parent_menu = make_menu(['drop'], self.modify_parent)
        self.reset_rows()
        self.append_page(ScrollCList(rcmenu=self.package_menu), 'environment')
        self.append_page(ScrollCList(rcmenu=self.parent_menu), 'parents')
        self.set_size_request(400, 300)

    def modify_parent(self, menuitem, action):
        if action == 'drop':
            parents = self._get_listbox('parents', 'family')
            self.trait.delete_parents(parents)
            self.__set_pages(self.current_family)

    def modify_family(self, menuitem, action):
        if action == 'delete':
            trait = self.listbox.get_selected_data()[0].family
            self.trait.delete_family(family)
            self.reset_rows()
            
    def reset_rows(self):
        self.set_rows(self.trait.get_traits())
        self.set_row_select(self.trait_selected)

    def __set_droptargets__(self, pages):
        set_receive_targets(pages['packages'].listbox,
                            self.drop_package, TARGETS.get('package', self.suite))
        set_receive_targets(pages['parents'].listbox,
                            self.drop_trait, TARGETS.get('trait', self.suite))

    def set_package(self, menu_item, action):
        packages = self._get_listbox('packages', 'package')
        trait = self.current_trait
        self.trait.set_action(action, packages)
        self.__set_pages(self.current_trait)

    def pop_mymenu(self, widget, event, menu):
        if right_click_pressed(event):
            menu.popup(None, None, None, event.button, event.time)

    def trait_selected(self, listbox, row, column, event):
        trait = listbox.get_selected_data()[0].trait
        self.select_trait(trait)
        
    def select_trait(self, trait):
        self.current_trait = trait
        self.trait.set_trait(trait)
        self.__set_pages(self.current_trait)

    def __set_pages(self, trait):
        pages = dict(self.pages)
        pages['packages'].set_rows(self.trait.packages(action=True))
        pages['packages'].set_select_mode('multi')
        pages['parents'].set_rows(self.trait.parents(), ['trait'])
        pages['parents'].set_select_mode('multi')
        #self.__set_droptargets__(pages)

    def drop_package(self, listbox, context, x, y, selection, targettype, time):
        packages = Set(selection.data.split('^&^'))
        self.trait.insert_packages(packages)
        self.__set_pages(self.current_trait)

    def drop_trait(self, listbox, context, x, y, selection, targettype, time):
        traits = selection.data.split('^&^')
        self.trait.insert_parents(traits)
        self.__set_pages(self.current_trait)

    def _get_listbox(self, page, field):
        pages = dict(self.pages)
        return [row[field] for row in pages[page].listbox.get_selected_data()]
    
    def change_suite(self, suite):
        self.suite = suite
        self.trait = Trait(self.conn, self.suite)
        self.reset_rows()
        
class TraitGenWin(CommandBoxWindow, HasDialogs):
    def __init__(self, conn, suite, name=None):
        if name is None:
            name = '.'.join([suite, 'traits'])
        CommandBoxWindow.__init__(self, name=name)
        self.conn = conn
        self.suite = suite
        self.set_title(name)
        self.browser = TraitBrowser(self.conn, self.suite)
        self.__make_menus__()
        self.vbox.pack_start(self.menu_bar, 0, 0, 0)
        self.vbox.add(self.browser)
        self.dialogs = {}.fromkeys(['create'])


    def __make_menus__(self):
        self.menu_bar = SimpleMenuBar()
        self.main_menu = SimpleMenu()
        self.tbar.add_button('create', 'create trait', self.ask_dialog)
        self.tbar.add_button('packages', 'show all packages', self.create_package_list)
        self.tbar.add_button('traits', 'show all traits', self.create_package_list)
        self.main_menu.add('create', self.ask_dialog)
        self.main_menu.add('packages', self.create_package_list)
        self.main_menu.add('traits', self.create_package_list)
        self.menu_bar.append(self.main_menu, 'main')
        
    def ask_dialog(self, button, data):
        if not self.dialogs[data]:
            if data == 'create':
                self.dialogs[data] = dialogs.Entry('create trait', name='create')
                self.dialogs[data].set_ok(self.create_trait)
            self.dialogs[data].set_cancel(self.destroy_dialog)

    def create_trait(self, button):
        name = button.get_name()
        debug(name)
        if name == 'create':
            trait = self.dialogs[name].get()
            try:
                self.browser.trait.create_trait(trait)
            except ExistsError:
                dialogs.Message('trait %s already exists' % trait)
                self.browser.traits.insert(data=insert_data)
            self.destroy_dialog(self.dialogs['create'])
            self.browser.reset_rows()

    def create_package_list(self, button, data):
        if data == 'packages':
            PackagesWindow(self.conn, self.browser.suite)
        elif data == 'traits':
            TraitsWindow(self.conn, self.browser.suite)

    def make_suite_menu(self):
        self.suite_menu = SimpleMenu()
        suites = self.cmd.as_dict('suites', 'suite')
        for suite in suites:
            self.suite_menu.add(suite, self.browser.change_suite)
        self.menu_bar.append(self.suite_menu, 'suite')
        self.suite = suite
        
if __name__ == '__main__':
    c = PaellaConnection()
    win = TraitGenWin(c, 'woody')
    win.connect('destroy', mainquit)
    
    
    def dtable():
        cmd.execute('drop table themebase')
    def dtables():
        for t in cmd.tables():
            if t not in  ['footable']:
                cmd.execute('drop table %s' %t)
    #dtables()
    mainloop()
    
