import os, sys
from os.path import join, dirname

from paella.base import Error, debug
from paella.db.midlevel import StatementCursor
from paella.profile.base import PaellaConfig, PaellaConnection
from paella.profile.profile import PaellaDatabase, PaellaProcessor
from paella.machines.xmlgen import MachineDatabaseElement
from paella.machines.machine import MachineHandler

from paella.gtk.middle import ListTextView

class DatabaseManager(object):
    def __init__(self, conn):
        object.__init__(self)
        self.cfg = PaellaConfig()
        self.conn = conn
        self.import_dir = self.cfg.get('database', 'import_path')
        self.export_dir = self.cfg.get('database', 'export_path')

    def backup(self, path):
        if not os.path.isdir(path):
            raise Error, 'arguement needs to be a directory'
        pdb = PaellaDatabase(self.conn, path)
        pdb.backup(path)
        mdbpath = join(path, 'machine_database.xml')
        me = MachineDatabaseElement(self.conn)
        mdfile = file(mdbpath, 'w')
        mdfile.write(me.toprettyxml())
        mdfile.close()

    def restore(self, path):
        if not os.path.isdir(path):
            raise Error, 'arguement needs to be a directory'
        dbpath = join(path, 'database.xml')
        mdbpath = join(path, 'machine_database.xml')
        pp = PaellaProcessor(self.conn)
        pp.create(dbpath)
        mh = MachineHandler(self.conn)
        md = mh.parse_xmlfile(mdbpath)
        mh.insert_parsed_element(md)    
        
class TextFileBrowser(ListTextView):
    def __init__(self, conn, name='TextFileBrowser'):
        ListTextView.__init__(self, name=name)
        self.conn = conn
        self.cursor = StatementCursor(self.conn)
        self.cursor.set_table('textfiles')

    def reset_rows(self):
        self.set_rows(self.cursor.select(fields=['fileid']))
        self.set_row_select(self.fileid_selected)

    def fileid_selected(self, listbox, row, column, event):
        pass
    

        
