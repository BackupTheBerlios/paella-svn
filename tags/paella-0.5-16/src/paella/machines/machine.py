from xml.dom.minidom import parseString

from paella.db.midlevel import StatementCursor
from paella.sqlgen.clause import Eq

from xmlparse import MachineDatabaseParser

def Table_cursor(conn, table):
    cursor = StatementCursor(conn, table)
    cursor.set_table(table)
    return cursor

class BaseMachineHandler(object):
    def __init__(self, conn):
        self.conn = conn
        self.cursor = Table_cursor(self.conn, 'machines')
        self.cursor.set_table('machines')
        self.kernels = Table_cursor(self.conn, 'kernels')
        self.mtypes = Table_cursor(self.conn, 'machine_types')
        self.mdisks = Table_cursor(self.conn, 'machine_disks')
        self.filesystems = Table_cursor(self.conn, 'filesystems')
        self.mounts = Table_cursor(self.conn, 'mounts')
        self.fsmounts = Table_cursor(self.conn, 'filesystem_mounts')
        self.disks = Table_cursor(self.conn, 'disks')
        self.partitions = Table_cursor(self.conn, 'partitions')
        self.current_machine = None
        
    def set_machine(self, machine):
        self._machine_clause_ = Eq('machine', machine)
        self.current = self.cursor.select_row(clause=self._machine_clause_)
        
        
    def _update_field_(self, name, value):
        self.cursor.update(data={name:value}, clause=self._machine_clause_)
        self.set_machine(self.current.machine)
        
    def set_profile(self, profile):
        self._update_field_('profile', profile)

    def set_kernel(self, kernel):
        kernels = [r.kernel for r in self.kernels.select()]
        if kernel not in kernels:
            self.kernels.insert(data={'kernel' : kernel})
        self._update_field_('kernel', kernel)

    def set_machine_type(self, mtype):
        mtypes = [r.machine_type for r in self.mtypes.select()]
        if mtype not in mtypes:
            self.mtypes.insert(data={'machine_type' : mtype})
        self._update_field_('machine_type', mtype)

    def rename_machine(self, newname):
        self._update_field_('machine', newname)
        self.set_machine(newname)

        
def add_disk_to_machine_type(conn,
                             diskname, mtype, device='/dev/hda'):
    cursor = StatementCursor(conn)
    data = dict(machine_type=mtype, diskname=diskname,
                device=device)
    cursor.insert(table='machine_disks', data=data)

def add_machine_type(conn, mtype):
    cursor = StatementCursor(conn)
    data = dict(machine_type=mtype)
    cursor.insert(table='machine_types', data=data)

def add_new_filesystem(conn, filesystem):
    cursor = StatementCursor(conn)
    data = dict(filesystem=filesystem)
    cursor.insert(table='filesystems', data=data)

def add_new_kernel(conn, kernel):
    cursor = StatementCursor(conn)
    data = dict(kernel=kernel)
    cursor.insert(table='kernels', data=data)

def add_new_mount(conn, name, mtpt, fstype, opts,
                  dump='0', pass_='0'):
    cursor = StatementCursor(conn)
    data = dict(mnt_name=name, mnt_point=mtpt,
                fstype=fstype, mnt_opts=opts,
                dump=dump)
    data['pass'] = pass_
    cursor.insert(table='mounts', data=data)

def add_mount_to_filesystem(conn, mnt_name, filesystem, ord, partition):
    cursor = StatementCursor(conn)
    data = dict(mnt_name=mnt_name, filesystem=filesystem,
                ord=str(ord), partition=partition)
    cursor.insert(table='filesystem_mounts', data=data)
    
def make_a_machine(conn, machine, mtype, profile, fs):
    cursor = StatementCursor(conn)
    data = dict(machine=machine, machine_type=mtype,
                profile=profile, filesystem=fs)
    cursor.insert(table='machines', data=data)
    

class MachineHandler(BaseMachineHandler):
    def add_disk_to_machine_type(self, diskname, mtype, device):
        self.mdisks.insert(data=dict(diskname=diskname, machine_type=mtype,
                                     device=device))
        
    def add_machine_type(self, mtype):
        self.mtypes.insert(data=dict(machine_type=mtype))
        
    def add_new_filesystem(self, filesystem):
        self.filesystems.insert(data=dict(filesystem=filesystem))

    def add_new_kernel(self, kernel):
        self.kernels.insert(data=dict(kernel=kernel))

    def add_new_mount(self, name, mtpt, fstype, opts, dump, pass_):
        data = dict(mnt_name=name, mnt_point=mtpt, fstype=fstype,
                    mnt_opts=mnt_opts, dump=dump)
        data['pass'] = pass_
        self.mounts.insert(data=data)
        
    def add_mount_to_filesystem(self, mnt_name, filesystem, ord, partition):
        self.fsmounts.insert(data=dict(mnt_name=mnt_name, filesystem=filesystem,
                                       ord=ord, partition=partition))
    def make_a_machine(self, machine, mtype, profile, fs):
        self.cursor.insert(table='machines',
                           data=dict(machine=machine,
                                     machine_type=machine_type,
                                     filesystem=fs, profile=profile))

    def insert_parsed_element(self, element):
        map(self.add_new_kernel, element.kernels)
        for mount in element.mounts:
            self.mounts.insert(data=mount)
        for filesystem in element.filesystems:
            self.add_new_filesystem(filesystem.name)
            for fsmount in filesystem.mounts:
                fsmount['filesystem'] = filesystem.name
                self.fsmounts.insert(data=fsmount)
        for disk in element.disks:
            self.disks.insert(data=dict(diskname=disk.name))
            for partition in disk.partitions:
                data = dict(diskname=disk.name)
                data.update(partition)
                print partition, data
                self.partitions.insert(data=data)
        for mtype in element.mtypes:
            self.add_machine_type(mtype.name)
            for mdisk in  mtype.disks:
                mdisk['machine_type'] = mtype.name
                self.mdisks.insert(data=mdisk)
        for machine in element.machines:
            data = {}
            data.update(machine)
            del data['name']
            data['machine'] = machine['name']
            self.cursor.insert(table='machines', data=data)

    def parse_xmlfile(self, path):
        element = parseString(file(path).read())
        return MachineDatabaseParser(element.firstChild)
    
    def check_machine_disks(self, machine_type):
        rows = self.mdisks.select(clause=Eq('machine_type', machine_type))
        dn_dict = {}
        for row in rows:
            if row.diskname not in dn_dict.keys():
                dn_dict[row.diskname] = []
            dn_dict[row.diskname].append(row.device)
        return dn_dict

    def make_partition_dump(self, diskname, device):
        rows = self.partitions.select(clause=Eq('diskname', diskname))
        firstline = '# partition table of %s' % device
        secondline = 'unit: sectors'
        blankline = ''
        plines = []
        for row in rows:
            line = '%s%s : start=%9d, size=%9d, Id=%d' % \
                   (device, row.partition, int(row.start), int(row.size), int(row.id))
            plines.append(line)
        return '\n'.join([firstline, secondline, blankline] + plines) + '\n'
    


    def array_hack(self, machine_type):
        dn_dict = self.check_machine_disks(machine_type)
        if len(dn_dict.keys()) == 1:
            diskname = dn_dict.keys()[0]
            if len(dn_dict[diskname]) > 1:
                device = '/dev/md'
            else:
                device = dn_dict[diskname][0]
        else:
            raise Error, "can't handle more than one disktype now"
        return device
        

    def make_fstab(self, filesystem=None, machine_type=None):
        if filesystem is None:
            filesystem = self.current.filesystem
        if machine_type is None:
            machine_type = self.current.machine_type
        fsmounts = self.get_all_fsmounts(filesystem=filesystem)
        device = self.array_hack(machine_type)
        fstab = []
        for row in fsmounts:
            fstype = row.fstype
            if int(row.partition) == 0:
                if fstype in ['tmpfs', 'proc']:
                    _dev = fstype
                else:
                    raise Error, 'unhandled fstype'
            else:                        
                _dev = '%s%s' % (device, row.partition)
            line = '%s\t%s\t%s' % (_dev, row.mnt_point, row.fstype)
            line += '\t%s\t%s\t%s' % (row.mnt_opts, row.dump, row['pass'])
            fstab.append(line)
        return '\n'.join(fstab) + '\n'

    def get_all_fsmounts(self, filesystem=None):
        if filesystem is None:
            filesystem = self.current.filesystem
        table = 'filesystem_mounts natural join mounts'
        clause = Eq('filesystem', filesystem)
        return self.cursor.select(table=table, clause=clause, order='ord')

    def get_installable_fsmounts(self, filesystem=None):
        fsmounts = self.get_all_fsmounts(filesystem=filesystem)
        return [r for r in fsmounts if int(r.partition)]

            
if __name__ == '__main__':
    from os.path import join
    from paella.profile.base import PaellaConfig, PaellaConnection
    cfg = PaellaConfig()
    conn = PaellaConnection(cfg)
    from xmlgen import MachineDatabaseElement
    from paella.installer.base import CurrentEnvironment
    ev = CurrentEnvironment(conn, 'bard')
    
    xfile = file(join(cfg['db_bkup_path'], 'concord', 'machine_database.xml'))
    mdata = xfile.read()
    xfile.close()
    
    element = parseString(mdata)

    me = MachineDatabaseElement(conn)
    md = MachineDatabaseParser(element.firstChild)
    mh = MachineHandler(conn)

    def quick_wipe(conn):
        cursor = StatementCursor(conn)
        cursor.delete(table='machines')
        cursor.delete(table='partition_workspace')
        cursor.delete(table='partitions')
        cursor.delete(table='filesystem_mounts')
        cursor.delete(table='filesystem_disks')
        cursor.delete(table='partition_mounts')
        cursor.delete(table='machine_disks')
        cursor.delete(table='machine_types')
        cursor.delete(table='mounts')
        cursor.delete(table='disks')
        cursor.delete(table='filesystems')
        cursor.delete(table='kernels')
        
