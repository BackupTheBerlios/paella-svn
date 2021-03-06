import os

from useless.base.util import echo
from useless.base.util import makepaths

from paella import deprecated

from paella.installer.base import runlog

def mount_tmp(target='/tmp'):
    deprecated('mount_tmp is deprecated use mount_tmpfs instead')
    os.system('mount -t tmpfs tmpfs %s' % target)

def mount_tmpfs(target='/tmp'):
    os.system('mount -t tmpfs tmpfs %s' % target)

def make_fstab(fstabobj, target):
    fstab = file(os.path.join(target, 'etc/fstab'), 'w')
    fstab.write(str(fstabobj))
    fstab.close()

def make_filesystem(device, fstype):
    if fstype == 'reiserfs':
        cmd = 'mkreiserfs -f -q %s' % device
    elif fstype == 'ext3':
        cmd = 'mkfs.ext3 -F -q %s' % device
    elif fstype == 'ext2':
        cmd = 'mkfs.ext2 -F -q %s' % device
    else:
        raise RuntimeError,  'unhandled fstype %s '  % fstype
    echo(cmd)
    return runlog(cmd)

def make_filesystems(device, fsmounts, env):
    mddev = False
    if device == '/dev/md':
        mdnum = 0
        mddev = True
    for row in fsmounts:
        if mddev:
            pdev = '/dev/md%d' % mdnum
            mdnum += 1
        else:
            pdev = device + str(row.partition)
        if row.mnt_name in env.keys():
            echo('%s held' % row.mnt_name)
        elif row.fstype == 'swap':
            runlog('echo making swap on %s' % pdev)
            runvalue = runlog('mkswap %s' % pdev)
            if runvalue:
                raise RuntimeError, 'problem making swap on %s' % pdev
        else:
            echo('making filesystem for %s' % row.mnt_name)
            make_filesystem(pdev, row.fstype)
            
def mount_target(target, mounts, device):
    mounts = [m for m in mounts if int(m.partition)]
    if mounts[0].mnt_point != '/':
        raise RuntimeError, 'bad set of mounts', mounts
    mddev = False
    mdnum = 0
    if device == '/dev/md':
        mddev = True
        pdev = '/dev/md0'
        mdnum += 1
    else:
        pdev = '%s%d' % (device, mounts[0].partition)
    runlog('echo mounting target %s to %s' % (pdev, target))
    runlog('mount %s %s' % (pdev, target))
    mounts = mounts[1:]
    mountable = [m for m in mounts if m.fstype != 'swap']
    for mnt in mountable:
        tpath = os.path.join(target, mnt.mnt_point[1:])
        makepaths(tpath)
        if mddev:
            pdev = '/dev/md%d' % mdnum
        else:
            pdev = '%s%d' % (device, mnt.partition)
        mdnum += 1
        runlog('echo mounting target %s to %s' % (pdev, tpath))
        runlog('mount %s %s' % (pdev, tpath))
        
def mount_target_proc(target, umount=False):
    tproc = os.path.join(target, 'proc')
    cmd = 'mount --bind /proc %s' % tproc
    if umount:
        cmd = 'umount -l %s' % tproc
    return runlog(cmd)
    
