import os
from os.path import join
from time import sleep

from paella.base import Error
from paella.base.util import makepaths, runlog
from paella.debian.base import debootstrap
from paella.profile.base import PaellaConnection, get_suite, PaellaConfig
from paella.db.midlevel import StatementCursor
from paella.sqlgen.clause import Eq, Gt
from paella.machines.machine import MachineHandler


from base import CurrentEnvironment
from util import ready_base_for_install, make_filesystem
from util import install_kernel, setup_modules

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
            logfile = '/paellalog/paella-install-%s.log' % machine
        os.environ['LOGFILE'] = logfile
        os.environ['PAELLA_MACHINE'] = machine
        
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
        
    def setup_installer(self):
        profile = self.machine.current.profile
        self.installer = ProfileInstaller(self.conn, self.cfg)
        self.installer.set_profile(profile)
        self.suite = self.installer.suite

    def organize_disks(self):
        return self.machine.check_machine_disks(self.machine.current.machine_type)
                            
    def partition_disks(self):
        disks = self.organize_disks()
        for diskname in disks:
            for device in disks[diskname]:
                self._partition_disk(diskname, device)
            if len(disks[diskname]) > 1:
                ndev = len(disks[diskname])
                print 'doing raid setup on %s' % diskname
                fs = self.machine.current.filesystem
                print fs
                pnums = [r.partition for r in self.machine.get_installable_fsmounts(fs)]
                for p in pnums:
                    mdadm = 'mdadm --create /dev/md%d' % p
                    mdadm = '%s --force -l1 -n%d ' % (mdadm, ndev)
                    devices = ['%s%s' % (d, p) for d in disks[diskname]]
                    command = mdadm + ' '.join(devices)
                    print command
                    yesman = 'bash -c "yes | %s"' % command
                    print yesman
                    os.system(yesman)
                print 'doing raid setup on %s' % str(disks[diskname])
                mdstat = file('/proc/mdstat').read()
                while mdstat.find('resync') > -1:
                    sleep(10)
                    mdstat = file('/proc/mdstat').read()                    
                    
            
    def _partition_disk(self, diskname, device):
        print 'partitioning', diskname, device
        dump = self.machine.make_partition_dump(diskname, device)
        i, o = os.popen2('sfdisk %s' % device)
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
        modules = self.machine.get_modules()
        print 'installing modules', modules
        setup_modules(self.target, modules)
        print 'modules installed'
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
    
