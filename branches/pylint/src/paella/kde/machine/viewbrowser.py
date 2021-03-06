from qt import SIGNAL

from kdeui import KMessageBox

from useless.base.util import strfile
from useless.kdebase import get_application_pointer
from useless.kdebase.dialogs import BaseRecordDialog

from paella.kde.base import split_url
from paella.kde.base.viewbrowser import ViewBrowser

# import document objects
from paella.kde.docgen.machine import MachineDoc
from paella.kde.docgen.machine import MachineTypeDoc
from paella.kde.docgen.machine import FilesystemDoc
from paella.kde.docgen.machine import MountDoc
from paella.kde.docgen.machine import DiskDoc

from base import NewMachineDialog
from base import EditMachineDIalog
from base import NewMTScriptDialog

class MachineView(ViewBrowser):
    def __init__(self, parent):
        ViewBrowser.__init__(self, parent, MachineDoc)

    def set_machine(self, machine):
        self.doc.set_machine(machine)
        self.setText(self.doc.output())

    def setSource(self, url):
        action, context, ident = split_url(url)
        if action == 'new':
            if context == 'machine':
                handler = self.doc.machine
                dialog = NewMachineDialog(self, handler)
                dialog.show()
                self._dialog = dialog
            else:
                KMessageBox.error(self, '%s not supported' % url)
        elif action == 'edit':
            if context == 'machine':
                handler = self.doc.machine
                dialog = EditMachineDIalog(self, handler, ident)
                dialog.show()
                self._dialog = dialog
                print 'edit machine', dialog.machine
        else:
            KMessageBox.error(self, '%s not supported' % url)

class MachineTypeView(ViewBrowser):
    def __init__(self, parent):
        ViewBrowser.__init__(self, parent, MachineTypeDoc)
        self._dialog = None

    def set_machine_type(self, machine_type):
        self.doc.set_machine_type(machine_type)
        self.setText(self.doc.output())

    def resetView(self):
        self.set_machine_type(self.doc.mtype.current)

    def setSource(self, url):
        action, context, ident = split_url(url)
        fields = []
        dialog_message = 'We need a message here'
        if context == 'Disks':
            fields = ['diskname', 'device']
            dialog_message = 'Add a new disk.'
        elif context == 'Families':
            fields = ['family']
            dialog_message = 'Add a new family.'
        elif context == 'Variables':
            fields = ['trait', 'name', 'value']
            dialog_message = 'Add a new variable.'
        elif context == 'machine_type':
            fields = ['name']
            dialog_message = 'Add a new machine type.'
        if action == 'new':
            if context == 'Scripts':
                dialog = NewMTScriptDialog(self)
                dialog.connect(dialog, SIGNAL('okClicked()'), self.insertNewScript)
                self._dialog = dialog
            elif fields:
                dialog = BaseRecordDialog(self, fields)
                dialog.context = context
                dialog.connect(dialog, SIGNAL('okClicked()'), self.insertNewRecord)
                dialog.frame.setText(dialog_message)
                self._dialog = dialog
            else:
                KMessageBox.error(self, 'problem with %s' % url)
        elif action == 'edit':
            self._perform_edit_action(context, ident)
        elif action == 'delete':
            self._perform_delete_action(context, ident)
        else:
            msg = 'Problem with action in url %s' % url
            KMessageBox.error(self, msg)
        if self._dialog is not None:
            self._dialog.connect(self._dialog, SIGNAL('cancelClicked()'), self._destroy_dialog)
            self._dialog.show()
        self.resetView()

    def _perform_delete_action(self, context, ident):
        if context == 'Families':
            self.doc.mtype.delete_family(ident)
            self.resetView()
        elif context == 'Variables':
            self.doc.mtype.edit_variables()
        elif context == 'Scripts':
            ans = KMessageBox.questionYesNo(self, "really delete this script?")
            if ans == KMessageBox.Yes:
                self.doc.mtype.delete_script(ident)
        elif context == 'Modules':
            msg = 'Deleting modules is not supported.'
            KMessageBox.information(self, msg)
        elif context == 'machine_type':
            msg = "Can't delete machine types yet."
            KMessageBox.information(self, msg)
        else:
            msg = 'Problem with delete - context %s id %s' % (context, ident)
            KMessageBox.error(self, msg)

    def _perform_edit_action(self, context, ident):
        if context == 'Variables':
            self.doc.mtype.edit_variables()
        elif context == 'Scripts':
            self.doc.mtype.edit_script(ident)
        elif context == 'machine_type':
            KMessageBox.information(self, 'Editing of machine types is unimplemented')
        else:
            msg = 'edit context %s id %s is unsupported' % (context, ident)
            KMessageBox.error(self, msg)

    def insertNewRecord(self):
        dialog = self._dialog
        context = dialog.context
        data = dialog.getRecordData()
        if context == 'Disks':
            self.doc.mtype.add_disk(data['diskname'], data['device'])
        elif context == 'Families':
            self.doc.mtype.append_family(data['family'])
        elif context == 'Variables':
            self.doc.mtype.append_variable(data['trait'], data['name'],
                                           data['value'])
        elif context == 'machine_type':
            self.doc.mtype.add_new_type(data['name'])
        else:
            KMessageBox.error(self, 'Error handling context %s' % context)
        self._dialog = None
        self.resetView()
        
    def updateRecord(self):
        raise NotImplementedError, 'updateRecord not implemented'

    def insertNewScript(self):
        dialog = self._dialog
        data = dialog.getRecordData()
        mtype = self.doc.mtype
        mtype.insert_script(data['name'], strfile(data['data']))
        self._dialog = None
        self.resetView()

    def _destroy_dialog(self):
        del self._dialog
        self._dialog = None
        
class FilesystemView(ViewBrowser):
    def __init__(self, parent):
        ViewBrowser.__init__(self, parent, FilesystemDoc)

    def set_filesystem(self, filesystem):
        self.doc.set_filesystem(filesystem)
        self.setText(self.doc.output())

    def setSource(self, url):
        KMessageBox.error(self, 'setSource unsupported now %s' % url)
    
class MountView(ViewBrowser):
    def __init__(self, parent):
        ViewBrowser.__init__(self, parent, MountDoc)

    def set_mount(self, mount):
        self.doc.set_mount(mount)
        self.setText(self.doc.output())

    def setSource(self, url):
        KMessageBox.error(self, 'setSource unsupported now %s' % url)
        

class DiskView(ViewBrowser):
    def __init__(self, parent):
        ViewBrowser.__init__(self, parent, DiskDoc)

    def set_disk(self, diskname):
        self.doc.set_disk(diskname)
        self.setText(self.doc.output())

    def setSource(self, url):
        KMessageBox.error(self, 'setSource unsupported now %s' % url)
        
