import os
from ConfigParser import RawConfigParser
import tempfile

from paella.gtk.base import right_click_pressed, keysplitter, set_receive_targets
from paella.gtk.simple import SimpleMenu, MyCombo, SimpleMenuBar
from paella.gtk import dialogs
from paella.gtk.middle import ListNoteBook, ScrollCList
from paella.gtk.windows import CommandBoxWindow
from paella.gtk.helpers import make_menu, HasDialogs
from paella.gtk.dialog_helpers import get_single_row

from gtk import mainloop, mainquit
from gtk import MenuBar

from gtk.gdk import ACTION_COPY, ACTION_MOVE
from gtk.gdk import BUTTON1_MASK

from paella.base import debug
from paella.base.util import ujoin

from paella.db.midlevel import StatementCursor
from paella.db.midlevel import TableRowDict, TableDict
from paella.db.midlevel import Environment
from paella.sqlgen.statement import Statement
from paella.sqlgen.select import SimpleClause
from paella.sqlgen.clause import Eq, In

from paella.profile.base import PaellaConnection
from paella.profile.profile import Profiles, ProfileTrait, PaellaDatabase
from paella.profile.profile import ProfileEnvironment

from traitgen import TraitGenWin, TraitsWindow
from traitgen import PackagesWindow, TARGETS

class ProfileVariablesConfig(RawConfigParser):
    def __init__(self, conn, profile):
        self.conn = conn
        self.profile = profile
        self.env = ProfileEnvironment(self.conn)
        self.env.set_profile(self.profile)
        RawConfigParser.__init__(self)
        for row in self.env.get_rows():
            if row.trait not in self.sections():
                self.add_trait(row.trait)
            self.set(row.trait, row.name, row.value)
        
    def add_trait(self, trait):
        self.add_section(trait)

    

class ProfileBrowser(ListNoteBook, HasDialogs):
    def __init__(self, conn, suites, name='ProfileBrowser'):
        self.menu = self.__make_mainmenu_(suites)
        ListNoteBook.__init__(self, name=name)
        self.conn = conn
        self.profiles = Profiles(self.conn)
        self.profiletrait = ProfileTrait(self.conn)
        self.trait_menu = make_menu(['drop', 'order'], self.trait_command)
        self.pdata_menu = make_menu(['edit', 'drop'], self.variable_command)
        self.reset_rows()
        self.append_page(ScrollCList(rcmenu=self.trait_menu), 'traits')
        self.append_page(ScrollCList(rcmenu=self.pdata_menu), 'variables')
        self.dialogs = {}.fromkeys(['order'])
        
    def __make_mainmenu_(self, suites):
        suite_commands = ['change to %s' %suite for suite in suites]
        profile_commands = ['drop', 'set defaults', 'append defaults']
        commands = suite_commands + profile_commands
        return make_menu(commands, self.profile_command)

    def reset_rows(self):
        self.set_rows(self.profiles.select(fields=['profile', 'suite'], order='profile'))
        self.set_row_select(self.profile_selected)

    def profile_selected(self, listbox, row, column, event):
        row = listbox.get_selected_data()[0]
        self.current = row
        self.select_profile(self.current.profile)

    def select_profile(self, profile):
        self.variables = ProfileEnvironment(self.conn, profile)
        self.profiletrait.set_profile(profile)
        self.__set_pages(profile)

    def __set_pages(self, profile):
        pages = dict(self.pages)
        #set traits for profile
        pages['traits'].set_rows(self.profiletrait.trait_rows())
        pages['traits'].set_select_mode('multi')
        self.__set_droptargets__(pages)
        clause = Eq('profile', self.current.profile)
        cursor = self.variables.env.cursor
        pages['variables'].set_rows(cursor.select(clause=clause), ['trait'])
        pages['variables'].set_select_mode('multi')

    def __set_droptargets__(self, pages):
        set_receive_targets(pages['traits'].listbox,
                            self.drop_trait, TARGETS.get('trait', self.current.suite))
                    

    def trait_command(self, menuitem, action):
        traits = self._get_listbox('traits', 'trait')
        if action == 'drop':
            clause = In('trait', traits) & Eq('profile', self.current.profile)
            self.profiletrait.cmd.delete(clause=clause)
            self.__set_pages(self.current.profile)
        elif action == 'order':
            if not self.dialogs['order']:
                self.dialogs['order'] = dialogs.Entry('enter order', name='order')
                self.dialogs['order'].set_ok(self.set_order)
                self.dialogs['order'].set_cancel(self.destroy_dialog)


    def variable_command(self, menuitem, action):
        rows = self.pages['variables'].get_selected_data()
        cursor = self.variables.env.cursor
        if action == 'drop':
            for row in rows:
                clause = Eq('profile', self.current.profile) & Eq('trait', row.trait)
                clause &= Eq('name', row.name)
                cursor.delete(clause=clause)
        elif action == 'edit':
            self.edit_profilevars()

    def edit_profilevars(self):
        config = ProfileVariablesConfig(self.conn, self.current.profile)
        tmp, path = tempfile.mkstemp('variable', 'paella')
        tmp = file(path, 'w')
        config.write(tmp)
        tmp.close()
        os.system('$EDITOR %s' %path)
        tmp = file(path, 'r')
        newconfig = RawConfigParser()
        newconfig.readfp(tmp)
        tmp.close()
        os.remove(path)
        cursor = self.variables.env.cursor
        pclause = Eq('profile', self.current.profile)
        for trait in config.sections():
            tclause = pclause & Eq('trait', trait)
            if not newconfig.has_section(trait):
                cursor.delete(clause=tclause)
            else:
                for name, value in newconfig.items(trait):
                    nclause = tclause & Eq('name', name)
                    if config.has_option(trait, name):
                        if value != config.get(trait, name):
                            cursor.update(data={'value' : value}, clause=nclause)
                    else:
                        idata = { 'profile' : self.current.profile,
                                  'trait' : trait,
                                  'name' : name,
                                  'value' : value}
                        cursor.insert(data=idata)
                    if config.has_section(trait):
                        for name, value in config.items(trait):
                            if not newconfig.has_option(trait, name):
                                cursor.delete(clause=tclause & Eq('name', name))
        self.select_profile(self.current.profile)
        
                            
    def set_order(self, button):
        dialog = self.dialogs['order']
        ord = dialog.get()
        rows = self.pages['traits'].get_selected_data()
        pclause = Eq('profile', self.current.profile)
        for row in rows:
            clause = pclause & Eq('trait', row.trait)
            self.profiletrait.update(data=dict(ord=ord), clause=clause)
        
    def drop_trait(self, listbox, context, x, y, selection,
                   targettype, time):
        traits = keysplitter(selection)
        self.profiletrait.insert_traits(traits)
        self.__set_pages(self.current.profile)

    def _get_listbox(self, page, field):
        pages = dict(self.pages)
        return [row[field] for row in pages[page].listbox.get_selected_data()]

    def profile_command(self, menu, command):
        if command[:10] == 'change to ':
            self.change_suite(command[10:])
        elif command == 'drop':
            self.profiletrait.drop_profile(self.current.profile)
            self.profiles.drop_profile(self.current.profile)
            self.current = None
            self.reset_rows()
        elif command == 'set defaults':
            self.variables.set_defaults()
        elif command == 'append defaults':
            self.variables.append_defaults()
        else:
            raise Error, 'bad command %s' %command
            
    def change_suite(self, suite):
        clause = Eq('profile', self.current.profile)
        self.profiles.update(data={'suite' : suite}, clause=clause)        
        print 'changing suite to ', suite
        self.current_suite = suite
        self.reset_rows()


class ProfileGenWin(CommandBoxWindow):
    def __init__(self, conn, name='ProfileGenWin'):
        actions = ['create', 'copy', 'export', 'import']
        CommandBoxWindow.__init__(self, name=name)
        self.set_title(name)
        self.conn = conn
        self.cmd = StatementCursor(conn, name)
        self.suites = [x.suite for x in self.cmd.select(table='suites')]
        self.profiles = StatementCursor(conn, 'profiles')
        self.profiles.set_table('profiles')
        self.menu_bar = SimpleMenuBar()
        self.vbox.pack_start(self.menu_bar, 0, 0, 0)
        self.dialogs = {}.fromkeys(actions)
        self.add_menu(actions, 'main', self.ask_dialog)
        self.add_menu(self.suites, 'traits', self.show_traits)
        self.add_menu(self.suites, 'traitgen', self.show_traitgen)
        self.browser = ProfileBrowser(self.conn, self.suites)
        self.vbox.add(self.browser)
        self.set_size_request(400, 300)
        
    def ask_dialog(self, button, data):
        if not self.dialogs[data]:
            if data == 'create':
                self.dialogs[data] = dialogs.Entry('create profile', name='create')
                self.dialogs[data].set_ok(self.create_profile)
            elif data == 'copy':
                self.dialogs[data] = dialogs.CList('copy profile', name='copy')
                dialog = self.dialogs[data]
                dialog.set_rows(self.profiles.select(fields='profile', order='profile'))
                dialog.set_ok(self.src_profile_selected)
            elif data == 'export':
                pdb = PaellaDatabase(self.conn)
                profiles = pdb.profiles
            self.dialogs[data].set_cancel(self.destroy_dialog)

    def destroy_dialog(self, dying):
        name = dying.get_name()
        self.dialogs[name] = None
        dying.destroy()

    def create_profile(self, button):
        name = button.get_name() 
        debug(name)
        if name == 'create':
            profile = self.dialogs[name].get()
            if profile not in [p.profile for p in self.profiles.select()]:
                self.profiles.insert(data={'profile' : profile,
                                           'suite' : 'woody'})
                self.destroy_dialog(self.dialogs[name])
                self.browser.reset_rows()
            else:
                dialogs.Dialog('there was a problem')
                
    def src_profile_selected(self, button):
        row = get_single_row(self.dialogs['copy'], 'profile')
        
    
    def show_packages(self, button, data):
        PackagesWindow(self.conn, data)

    def show_traits(self, button, data):
        TraitsWindow(self.conn, data)

    def show_traitgen(self, button, data):
            TraitGenWin(self.conn, data)

if __name__ == '__main__':
    c = PaellaConnection()
    win = ProfileGenWin(c)
    win.connect('destroy', mainquit)
    
    
    def dtable():
        cmd.execute('drop table themebase')
    def dtables():
        for t in cmd.tables():
            if t not in  ['footable']:
                cmd.execute('drop table %s' %t)
    #dtables()
    mainloop()
    
