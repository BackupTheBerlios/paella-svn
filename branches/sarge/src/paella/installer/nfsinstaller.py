import os
from os.path import join, basename, dirname
from time import sleep
import commands
import tempfile

from useless.base import Error, Log
from useless.base.util import makepaths, runlog
from useless.db.midlevel import StatementCursor
from useless.sqlgen.clause import Eq, Gt, Neq

from paella.base import PaellaConfig
from paella.debian.base import debootstrap
from paella.db import PaellaConnection, DefaultEnvironment
from paella.db.base import get_suite
from paella.db.machine import MachineHandler

from base import CurrentEnvironment
from base import BaseChrootInstaller
from base import InstallError
from util import ready_base_for_install, make_filesystem
from util import install_kernel, setup_modules

from profile import ProfileInstaller
from fstab import HdFstab

class NewInstaller(object):
    def __init__(self, conn, cfg):
        object.__init__(self)
        self.conn = conn
        self.cfg = cfg
        self.defenv = DefaultEnvironment(self.conn)
        self.machine = MachineHandler(self.conn)
        self.cursor = StatementCursor(self.conn)
        self.target = None
        self.installer = None
        self._mounted = None
        self._bootstrapped = None
        self.debmirror = self.cfg.get('debrepos', 'http_mirror')
        self._raid_setup = False
        self._raid_drives = {}
        self._enable_bad_hacks = False
        if self.cfg.is_it_true('installer', 'enable_bad_hacks'):
            self._enable_bad_hacks = True
        
    def set_logfile(self, logfile):
        env = os.environ
        if logfile is None:
            if env.has_key('PAELLA_LOGFILE'):
                self.logfile = env['PAELLA_LOGFILE']
            elif env.has_key('LOGFILE'):
                self.logfile = env['LOGFILE']
            elif self.defenv.has_option('installer', 'default_logfile'):
                self.logfile = self.defenv.get('installer', 'default_logfile')
            else:
                raise InstallSetupError, 'There is no log file defined, giving up.'
        else:
            self.logfile = logfile
        logdir = os.path.dirname(self.logfile)
        if logdir:
            makepaths(os.path.dirname(self.logfile))
        format = '%(name)s - %(asctime)s - %(levelname)s: %(message)s'
        self.log = Log('paella-installer', self.logfile, format)
        
    def _check_target(self):
        if not self.target:
            raise Error, 'no target specified'

    def _check_installer(self):
        if not self.installer:
            raise Error, 'no installer available'

    def _check_mounted(self):
        self._check_target()
        if not self._mounted:
            raise InstallError, 'target not mounted'

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
        disklogpath = join(dirname(logfile), 'disklog')
        if not os.path.isdir(disklogpath):
            makepaths(disklogpath)
        self.disklogpath = disklogpath
        self.curenv = CurrentEnvironment(self.conn, self.machine.current.machine)
        self.set_logfile(logfile)
        
    def check_if_mounted(self, device):
        mounts = file('/proc/mounts')
        for line in file:
            if line.startswith(device):
                return True
        return False

    def unmount_device(self, device):
        mounted = os.system('umount %s' % device)
        
    def make_filesystems(self):
        device = self.machine.array_hack(self.machine.current.machine_type)
        mddev = False
        if device == '/dev/md':
            mdnum = 0
            mddev = True
        all_fsmounts = self.machine.get_installable_fsmounts()
        env = CurrentEnvironment(self.conn, self.machine.current.machine)
        for row in all_fsmounts:
            if mddev:
                pdev = '/dev/md%d' % mdnum
                mdnum += 1
            else:
                pdev = device + str(row.partition)
            if row.mnt_name in env.keys():
                print '%s held' % row.mnt_name
            elif row.fstype == 'swap':
                runlog('echo making swap on %s' % pdev)
                runlog('mkswap %s' % pdev)
            else:
                print 'making filesystem for', row.mnt_name
                make_filesystem(pdev, row.fstype)

    def set_target(self, target):
        self.target = target

    def _pdev(self, device, partition):
        return device + str(partition)

    def _mount_target_proc(self):
        self._check_bootstrap()
        tproc = join(self.target, 'proc')
        cmd = 'mount --bind /proc %s' % tproc
        runvalue = runlog(cmd)
        if runvalue:
            raise InstallError, 'problem mounting target /proc at %s' % tproc
        else:
            self._proc_mounted = True

    def _umount_target_proc(self):
        tproc = join(self.target, 'proc')
        cmd = 'umount %s' % tproc
        runvalue = runlog(cmd)
        if runvalue:
            raise InstallError, 'problem unmounting target /proc at %s' % tproc
        else:
            self._proc_mounted = False
            
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
        mddev = False
        mdnum = 0
        if device == '/dev/md':
            mddev = True
            pdev = '/dev/md0'
            mdnum += 1
        else:
            pdev = self._pdev(device, mounts[0].partition)
        runlog('echo mounting target %s to %s ' % (pdev, self.target))
        clause &= Neq('mnt_point', '/')
        mounts = self.cursor.select(table=table, clause=clause, order='ord')
        mountable = [mount for mount in mounts if mount.fstype != 'swap']
        runlog('mount %s %s' % (pdev, self.target))
        for mnt in mountable:
            tpath = os.path.join(self.target, mnt.mnt_point[1:])
            makepaths(tpath)
            if mddev:
                pdev = '/dev/md%d' % mdnum
            else:
                pdev = self._pdev(device, mnt.partition)
            mdnum += 1
            runlog('mount %s %s' % (pdev, tpath))
        self._mounted = True
        
    def setup_installer(self):
        profile = self.machine.current.profile
        self.installer = ProfileInstaller(self.conn)
        self.installer.log = self.log
        self.installer.set_profile(profile)
        self.suite = self.installer.suite

    def organize_disks(self):
        return self.machine.check_machine_disks(self.machine.current.machine_type)
                            
    def _setup_disks(self, diskname, disks=None):
        if disks is None:
            disks = self.organize_disks()
        devices = disks[diskname]

    def setup_disks(self):
        disks = self.organize_disks()
        disknames = disks.keys()
        if not len(disknames):
            self._setup_disk_fai('default', '/dev/hda')
        else:
            if len(disknames) > 1:
                #this isn't really handled yet
                self.partition_disks()
                self.make_filesystems()
            else:
                devices = disks[disknames[0]]
                if len(devices) > 1:
                    #this is a raid setup
                    self.partition_disks()
                    self.make_filesystems()
                elif len(devices) == 1:
                    self._setup_disk_fai(self.machine.current.filesystem, devices[0])
                else:
                    self._setup_disk_fai('default', '/dev/hda')
    
    def _setup_disk_fai(self, filesystem, device):
        disk_config = self.machine.make_disk_config_info(device)
        fileid, disk_config_path = tempfile.mkstemp('paella', 'diskinfo')
        disk_config_file = file(disk_config_path, 'w')
        disk_config_file.write(disk_config)
        disk_config_file.close()
        script = '/usr/lib/paella/scripts/setup_harddisks_fai'
        options = '-X -f %s' % disk_config_path
        env = 'env LOGDIR=%s diskvar=%s' % (self.disklogpath, join(self.disklogpath, 'diskvar'))
        command = '%s %s %s' % (env, script, options)
        runlog(command)
        
    def _setup_raid_drives(self, diskname, devices):
        self._raid_setup = True
        self._raid_drives[diskname] = devices
        for device in devices:
            self._partition_disk(diskname, device)
        ndev = len(devices)
        print 'doing raid setup on %s' % diskname
        fs = self.machine.current.filesystem
        print fs
        pnums = [r.partition for r in self.machine.get_installable_fsmounts(fs)]
        mdnum = 0 
        for p in pnums:
            mdadm = 'mdadm --create /dev/md%d' % mdnum
            mdadm = '%s --force -l1 -n%d ' % (mdadm, ndev)
            devices = ['%s%s' % (d, p) for d in devices]
            command = mdadm + ' '.join(devices)
            print command
            yesman = 'bash -c "yes | %s"' % command
            print yesman
            os.system(yesman)
            mdnum += 1
        print 'doing raid setup on %s' % str(devices)
        mdstat = file('/proc/mdstat').read()
        while mdstat.find('resync') > -1:
            sleep(10)
            mdstat = file('/proc/mdstat').read()                    
        
    def partition_disks(self):
        disks = self.organize_disks()
        for diskname in disks:
            for device in disks[diskname]:
                self._partition_disk(diskname, device)
            if len(disks[diskname]) > 1:
                self._raid_setup = True
                self._raid_drives[diskname] = disks[diskname]
                ndev = len(disks[diskname])
                print 'doing raid setup on %s' % diskname
                fs = self.machine.current.filesystem
                print fs
                pnums = [r.partition for r in self.machine.get_installable_fsmounts(fs)]
                mdnum = 0 
                for p in pnums:
                    mdadm = 'mdadm --create /dev/md%d' % mdnum
                    mdadm = '%s --force -l1 -n%d ' % (mdadm, ndev)
                    devices = ['%s%s' % (d, p) for d in disks[diskname]]
                    command = mdadm + ' '.join(devices)
                    print command
                    yesman = 'bash -c "yes | %s"' % command
                    print yesman
                    os.system(yesman)
                    mdnum += 1
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
            
    def extract_basebootstrap(self):
        self._check_mounted()
        self._check_installer()
        runlog('echo extracting premade base tarball')
        suite_path = self.cfg.get('installer', 'suite_storage')
        basefile = join(suite_path, '%s.tar' % self.suite)
        runvalue = runlog('tar -C %s -xf %s' % (self.target, basefile))
        if runvalue:
            raise Error, 'problems extracting %s' % basefile
        self._bootstrapped = True

    def bootstrap_target(self):
        self._check_mounted()
        self._check_installer()
        runlog(debootstrap(self.suite, self.target, self.debmirror))
        self._bootstrapped = True

    def _make_generic_devices(self, devices):
        here = os.getcwd()
        os.chdir(join(self.target, 'dev'))
        for dev in devices:
            runlog('echo making device %s with MAKEDEV' % dev)
            runlog('./MAKEDEV %s' % dev)
        os.chdir(here)

    def _extract_devices_tarball(self):
        dtball = self.cfg.get('installer', 'devices_tarball')
        devpath = join(self.target, 'dev')
        cmd = 'tar -C %s -xf %s' % (devpath, dtball)
        runvalue = runlog(cmd)
        if runvalue:
            raise Error, 'problem extracting devices tarball'
        

    def make_disk_devices(self):
        devices = map(basename, self.machine.get_disk_devices())
        self._make_generic_devices(devices)

    def make_tty_devices(self):
        self._make_generic_devices(['console'])

    def make_input_devices(self):
        self._make_generic_devices(['input'])

    def make_generic_devices(self):
        #devices = ['std', 'console', 'pty', 'tap', 'sg', 'input', 'audio']
        self._make_generic_devices(['generic'])
        
    def ready_base_for_install(self):
        self._check_bootstrap()
        self._check_installer()
        fstab = self.machine.make_fstab()
        ready_base_for_install(self.target, self.cfg, self.suite, fstab)
        if self.cfg.is_it_true('installer', 'use_devices_tarball'):
            runlog('echo extracting devices tarball')
            self._extract_devices_tarball()
        else:
            runlog('echo using MAKEDEV to make devices')
            self.make_generic_devices()
        self.make_disk_devices()
        if self._raid_setup:
            mdpath = join(self.target, 'etc/mdadm')
            makepaths(mdpath)
            mdconfname = join(mdpath, 'mdadm.conf')
            mdconf = file(mdconfname, 'w')
            for diskname in self._raid_drives:
                devices = ['%s*' % d for d in self._raid_drives[diskname]]
                line = 'DEVICE %s' % ' '.join(devices)
                mdconf.write(line + '\n')
            mdconf.close()
            mdconf = file(mdconfname, 'a')
            arrdata = commands.getoutput('mdadm -E --config=%s -s' % mdconfname)
            mdconf.write(arrdata + '\n')
            mdconf.write('\n')
            mdconf.close()
        self._mount_target_proc()
        
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
        if self._enable_bad_hacks:
            self.setup_disks()
        else:
            self.partition_disks()
            self.make_filesystems()
        self.setup_installer()
        self.set_target(target)
        self.ready_target()
        if self.cfg.is_it_true('installer', 'bootstrap_target'):
            self.bootstrap_target()
        else:
            self.extract_basebootstrap()
        self.ready_base_for_install()
        self.install_to_target()
        self.post_install()
        

if __name__ == '__main__':
    pass
    
