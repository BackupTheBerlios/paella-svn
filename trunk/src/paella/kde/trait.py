import os
from qt import SLOT, SIGNAL, Qt

from kdeui import KMainWindow
from kdeui import KPopupMenu
from kdeui import KMessageBox
from kdeui import KListView, KListViewItem

from paella.profile.base import PaellaConfig
from paella.profile.base import PaellaConnection
from paella.profile.trait import Trait
from paella.db.midlevel import StatementCursor
from paella.kde.base import MainWindow, SimpleSplitWindow
from paella.kde.base import ViewBrowser, ViewWindow
from paella.kde.xmlgen import TraitDoc



class TraitView(ViewBrowser):
    def __init__(self, app, parent):
        ViewBrowser.__init__(self, app, parent, TraitDoc)

    def set_trait(self, trait):
        self.doc.set_trait(trait)
        self.setText(self.doc.toxml())

    def set_suite(self, suite):
        self.doc.suite = suite
        self.doc.trait = Trait(self.app.conn, suite=suite)

    def setSource(self, url):
        action, context, id = str(url).split('.')
        if action == 'show':
            if context == 'parent':
                win = TraitMainWindow(self.app, self.parent(), self.doc.suite)
                win.view.set_trait(id)
            elif context == 'template':
                fid = id.replace(',', '.')
                package, template = fid.split('...')
                win = ViewWindow(self.app, self.parent(), TraitView, 'TemplateView')
                templatefile = self.doc.trait._templates.templatedata(package, template)
                win.view.setText(templatefile)
                win.resize(600, 800)
            elif context == 'script':
                scriptfile = self.doc.trait._scripts.scriptdata(id)
                win = ViewWindow(self.app, self.parent(), TraitView, 'ScriptView')
                win.view.setText(scriptfile)
                win.resize(600, 800)
                
        else:
            KMessageBox.information(self, 'called %s' % url)
        
        
class TraitMainWindow(SimpleSplitWindow):
    def __init__(self, app, parent, suite):
        SimpleSplitWindow.__init__(self, app, parent, TraitView, 'TraitMainWindow')
        self.app = app
        self.initActions()
        self.initMenus()
        self.initToolbar()
        self.conn = app.conn
        self.suite = suite
        self.cfg = app.cfg
        self.cursor = StatementCursor(self.conn)
        self.trait = Trait(self.conn, suite=suite)
        self.refreshListView()
        self.view.set_suite(suite)
        self.resize(600, 800)
        self.setCaption('%s traits' % suite)
        
    def initActions(self):
        collection = self.actionCollection()
        
    def initMenus(self):
        mainMenu = KPopupMenu(self)
        menus = [mainMenu]
        self.menuBar().insertItem('&Main', mainMenu)
        self.menuBar().insertItem('&Help', self.helpMenu(''))

    def initToolbar(self):
        toolbar = self.toolBar()

    def initlistView(self):
        self.listView.setRootIsDecorated(True)
        self.listView.addColumn('group')
        
    def refreshListView(self):
        trait_folder = KListViewItem(self.listView, 'traits')
        for trait in self.trait.get_trait_list():
            item = KListViewItem(trait_folder, trait)
            item.trait = trait
            for widget in ['trait', 'template', 'environ', 'scripts']:
                w = KListViewItem(item, widget)
                w.trait = item.trait
                w.widget = widget
                
    def selectionChanged(self):
        current = self.listView.currentItem()
        if hasattr(current, 'trait'):
            print 'trait is', current.trait
            self.view.set_trait(current.trait)
        if hasattr(current, 'suite'):
            print 'suite is', current.suite
            if hasattr(current, 'widget'):
                print 'widget is', current.widget


if __name__ == '__main__':
    cfg = PaellaConfig()
    conn = PaellaConnection(cfg)
    t = Trait(conn, suite='kudzu')
