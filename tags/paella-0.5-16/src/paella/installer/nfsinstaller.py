import os
from os.path import join

from paella.base import Error
from paella.base.util import makepaths, runlog
from paella.debian.base import debootstrap
from paella.profile.base import PaellaConnection, get_suite, PaellaConfig
from paella.db.midlevel import StatementCursor
from paella.sqlgen.clause import Eq, Gt
from paella.machines.machine import MachineHandler


from base import CurrentEnvironment
from util import ready_base_for_install, make_filesystem
from util import install_kernel

from profile import ProfileInstaller
from fstab import HdFstab

    
class NewInstaller(object):
    def __init__(self, conn, cfg):
        object.__init__(self)
        self.conn = conn
        self.cfg = cfg
        self.machine = MachineHandler(self.conn)
        self.cursor = StatementCursor(self.conn)
        self.target = None
        self.installer = None
        self._mounted = None
        self._bootstrapped = None
        self.debmirror = self.cfg.get('debrepos', 'http_mirror')
                
    def _check_target(self):
        if not self.target:
            raise Error, 'no target specified'

    def _check_installer(self):
        if not self.installer:
            raise Error, 'no installer available'

    def _check_mounted(self):
        self._check_target()
        if not self._mounted:
            raise Error, 'target not mounted'

    def _check_bootstrap(self):
        self._check_mounted()
        if not self._bootstrapped:
            raise Error, 'target not bootstrapped'
        
    def set_machine(self, machine):
        self.machine.set_machine(machine)
        try:
            logfile = os.environ['LOGFILE']
        except KeyError:
            logfile = '/var/log/paella-install-%s.log' % machine
        os.environ['LOGFILE'] = logfile

    def make_filesystems(self):
        device = self.machine.array_hack(self.machine.current.machine_type)
        all_fsmounts = self.machine.get_installable_fsmounts()
        env = CurrentEnvironment(self.conn, self.machine.current.machine)
        for row in all_fsmounts:
            pdev = device + str(row.partition)
            if row.mnt_name in env.keys():
                print '%s held' % row.mnt_name
            else:
                print 'making filesystem for', row.mnt_name
                make_filesystem(pdev, row.fstype)

    def set_target(self, target):
        self.target = target

    def _pdev(self, device, partition):
        return device + str(partition)

    def ready_target(self):
        self._check_target()
        makepaths(self.target)
        device = self.machine.array_hack(self.machine.current.machine_type)
        clause = Eq('filesystem', self.machine.current.filesystem)
        clause &= Gt('partition', '0')
        table = 'filesystem_mounts natural join mounts'
        mounts = self.cursor.select(table=table, clause=clause, order='mnt_point')
        if mounts[0].mnt_point != '/':
            raise Error, 'bad set of mounts', mounts
        pdev = self._pdev(device, mounts[0].partition)
        print 'mounting target', pdev, self.target
        runlog('mount %s %s' % (pdev, self.target))
        for mnt in mounts[1:]:
            tpath = os.path.join(self.target, mnt.mnt_point[1:])
            makepaths(tpath)
            pdev = self._pdev(device, mnt.partition)
            runlog('mount %s %s' % (pdev, tpath))
        self._mounted = True
        
    def apt_update_target(self):
        raise Error, "deprecated --don't do this anymore"
        os.system('chroot %s apt-get -y update' % self.target)

    def setup_installer(self):
        profile = self.machine.current.profile
        self.installer = ProfileInstaller(self.conn, self.cfg)
        self.installer.set_profile(profile)
        self.suite = self.installer.suite
                        
    def partition_disks(self):
        clause = Eq('machine_type', self.machine.current.machine_type)
        disk_rows = self.cursor.select(table='machine_disks', clause=clause)
        for row in disk_rows:
            print 'partitioning', row.diskname, row.device
            dump = self.machine.make_partition_dump(row.diskname, row.device)
            i, o = os.popen2('sfdisk %s' % row.device)
            i.write(dump)
            i.close()

    def bootstrap_target(self):
        self._check_mounted()
        self._check_installer()
        runlog(debootstrap(self.suite, self.target, self.debmirror))
        self._bootstrapped = True
        
    def ready_base_for_install(self):
        self._check_bootstrap()
        self._check_installer()
        fstab = self.machine.make_fstab()
        ready_base_for_install(self.target, self.cfg, self.suite, fstab)
        
    def install_to_target(self):
        os.environ['DEBIAN_FRONTEND'] = 'noninteractive'
        self._check_target()
        self._check_installer()
        self.installer.set_target(self.target)
        self.installer.process()        

    def post_install(self):
        print 'post_install'
        kernel = self.machine.current.kernel
        print 'installing kernel', kernel
        install_kernel(kernel, self.target)
        print 'kernel installed'
        
    
    def install(self, machine, target):
        self.set_machine(machine)
        self.partition_disks()
        self.make_filesystems()
        self.setup_installer()
        self.set_target(target)
        self.ready_target()
        self.bootstrap_target()
        self.ready_base_for_install()
        self.install_to_target()
        self.post_install()
        

if __name__ == '__main__':
    pass
    
