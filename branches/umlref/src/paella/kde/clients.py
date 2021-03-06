from qt import SIGNAL

from kdeui import KMessageBox
from kdeui import KStdAction
from kdeui import KPopupMenu
from kdeui import KListView, KListViewItem

from paella.db.profile import Profile
from paella.db.family import Family

from useless.base.path import path
from useless.kdebase import get_application_pointer
from useless.kdebase.dialogs import BaseAssigner

from paella.kde.base import split_url
from paella.kde.base.viewbrowser import ViewBrowser
from paella.kde.base.mainwin import BasePaellaWindow


## NOTE: this looks like I copied the Profile Manager as
# a template for the ClientsMainWindow, but it looks like
# that's as far as I got

# I need to look a the old gtk widget before doing anything
# here

class ClientsMainWindow(BasePaellaWindow):
    def __init__(self, parent):
        BasePaellaWindow.__init__(self, parent, name='ClientsMainWindow')
        self.initPaellaCommon()
        self.initActions()
        self.initMenus()
        self.initToolbar()
        self.cursor = self.conn.cursor(statement=True)
        self.listView = KListView(self)
        self.setCentralWidget(self.listView)
        self.refreshListView()
        self.resize(600, 800)
        self.setCaption('Paella Profiles')

    def initActions(self):
        collection = self.actionCollection()
        self.quitAction = KStdAction.quit(self.close, collection)
        self.newClientAction = KStdAction.openNew(self.slotNewClient, collection)

    def initMenus(self):
        mainmenu = KPopupMenu(self)
        menubar = self.menuBar()
        menubar.insertItem('&Main', mainmenu)
        menubar.insertItem('&Help', self.helpMenu(''))
        self.newClientAction.plug(mainmenu)
        self.quitAction.plug(mainmenu)

    def initToolbar(self):
        toolbar = self.toolBar()
        self.newClientAction.plug(toolbar)
        self.quitAction.plug(toolbar)

    def initlistView(self):
        self.listView.setRootIsDecorated(False)
        self.listView.addColumn('profile')

    def refreshListView(self):
        self.listView.clear()
        for row in self.profile.select(fields=['profile', 'suite'], order=['profile']):
            item = KListViewItem(self.listView, row.profile)
            item.profile = row.profile

    def slotNewClient(self):
        KMessageBox.information(self, 'New Client not ready yet.')

    def selectionChanged(self):
        item = self.listView.currentItem()
        self.mainView.set_profile(item.profile)
        
