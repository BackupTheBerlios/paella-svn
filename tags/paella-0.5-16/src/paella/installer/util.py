import os

from paella.base import Error
from paella.base.util import makepaths, runlog, echo
from paella.debian.base import RepositorySource



def make_interfaces_simple(target):
    i = file(os.path.join(target, 'etc/network/interfaces'), 'w')
    i.write('auto lo eth0\n')
    i.write('iface lo inet loopback\n')
    i.write('iface eth0 inet dhcp\n')
    i.write('\n\n')
    i.close()

def mount_tmp():
    os.system('mount -t tmpfs tmpfs /tmp')

def backup_target_command(target, tarball):
    exclude = "--exclude './proc/*'"
    tarcmd = 'bash -c "tar -c %s ' % exclude
    tarcmd += '-C %s . > %s"' % (target, tarball)
    return tarcmd

def remove_debs(target):
    archives = 'var/cache/apt/archives'
    debs = os.path.join(target, archives, '*.deb')
    pdebs = os.path.join(target, archives, 'partial', '*.deb')
    runlog('rm %s %s -f' % (debs, pdebs))
    
def extract_tarball(target, tarball):
    here = os.getcwd()
    print 'extracting with tar'
    os.chdir(target)
    if tarball[-2:] == 'gz':
        opts = 'xzf'
    elif tarball[-3:] == 'bz2':
        opts = 'xjf'
    else:
        opts = 'xf'
    runlog('tar %s %s' % (opts, tarball))
    os.chdir(here)

#password is 'a'
myline = 'root:$1$IImobcMx$4Lsn4oHhM7L9pNYZNP7zz/:0:0:root:/root:/bin/bash'

def make_sources_list(cfg, target, suite):
    section = 'debrepos'
    aptdir = os.path.join(target, 'etc', 'apt')
    makepaths(aptdir)
    sources_list = file(os.path.join(aptdir, 'sources.list'), 'w')
    source = RepositorySource()
    source.uri = cfg.get(section, 'http_mirror')
    source.suite = suite
    source.set_path()
    sources_list.write(str(source) +'\n')
    source.type = 'deb-src'
    sources_list.write(str(source) +'\n')
    source.type = 'deb'
    if suite == 'woody' or cfg.has_option(section, '%s_nonus' % suite):
        source.suite += '/non-US'
        sources_list.write(str(source) +'\n')
        source.type = 'deb-src'
        sources_list.write(str(source) +'\n')
    loption = suite + '_local'
    if cfg.has_option(section, loption) and cfg[loption] == 'true':
        sources_list.write('deb %s/local %s/\n' % (source.uri, suite))
        sources_list.write('deb-src %s/local %s/\n' % (source.uri, suite))
    coption = suite + '_common'
    if cfg.has_option(section, coption) and cfg[coption] == 'true':
        sources_list.write('deb %s/local common/\n' % source.uri)
        sources_list.write('deb-src %s/local common/\n' % source.uri)
    sources_list.write('\n')
    sources_list.close()


def set_root_passwd(target, rootline):
    p = file(os.path.join(target, 'etc/passwd'))
    lines = [rootline + '\n']
    for line in p:
        if line[:6] != 'root::':
            lines.append(line)
    p.close()
    p = file(os.path.join(target, 'etc/passwd'), 'w')
    p.writelines(lines)
    p.close()

def make_fstab(fstabobj, target):
    fstab = file(os.path.join(target, 'etc/fstab'), 'w')
    fstab.write(str(fstabobj))
    fstab.close()

def install_kernel(package, target):
    script = "#!/bin/bash\n"
    script += 'umount /proc\n'
    script += 'umount /proc\n'
    script += 'mount -t proc proc /proc\n'
    script += 'touch /boot/vmlinuz-fake\n'
    script += 'ln -s boot/vmlinuz-fake vmlinuz\n'
    script += 'apt-get -y install %s\n' % package
    script += 'echo "kernel %s installed"\n' % package
    script += 'umount /proc\n'
    script += '\n'
    sname = 'install_kernel.sh'
    full_path = os.path.join(target, sname)
    sfile = file(full_path, 'w')
    sfile.write(script)
    sfile.close()
    runlog('chmod a+x %s' % full_path)
    runlog('chroot %s ./%s' % (target, sname))
    os.remove(full_path)

def make_filesystem(device, fstype):
    if fstype == 'reiserfs':
        cmd = 'mkreiserfs -f -q %s' % device
    elif fstype == 'ext3':
        cmd = 'mkfs.ext3 -F -q %s' % device
    elif fstype == 'ext2':
        cmd = 'mkfs.ext2 -F -q %s' % device
    else:
        raise Error,  'unhandled fstype %s '  % fstype
    echo(cmd)
    runlog(cmd, keeprunning=True)
        

#this is done after bootstrap or
#this is done after extracting the base tar
def ready_base_for_install(target, cfg, suite, fstabobj):
    set_root_passwd(target, myline)
    make_sources_list(cfg, target, suite)
    make_interfaces_simple(target)
    make_fstab(fstabobj, target)
    
