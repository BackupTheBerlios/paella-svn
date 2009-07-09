import os
import subprocess
import pwd

from repserve.base import NoArchiveKeyError
from repserve.path import path

def get_fullname(username=None):
    if username is None:
        username = os.environ['USER']
    ptuple = pwd.getpwnam(username)
    gecos = ptuple.pw_gecos
    fullname = gecos.split(',')[0]
    return fullname

def get_email(username=None):
    if username is None:
        username = os.environ['USER']
    domain = file('/etc/mailname').read().strip()
    return '%s@%s' % (username, domain)


def generate_gpg_key(batchinfo):
    keygen_proc = subprocess.Popen(['gpg', '--gen-key', '--batch'],
                                   stdin=subprocess.PIPE)
    keygen_proc.stdin.write(batchinfo)
    keygen_proc.stdin.close()
    print "You will need to move the mouse around or keep pressing shift/ctrl/alt randomly"
    
    retcode = keygen_proc.wait()
    if retcode:
        raise RuntimeError , "GPG returned %d" % retcode
    
gpg_keygen_batchfile = """Key-Type: DSA
Key-Length: 1024
Subkey-Type: ELG-E
Subkey-Length: 2048
Name-Real: %(fullname)s
Name-Email: %(email)s
Expire-Date: 0
%%commit
"""


def make_default_signing_key(fullname=None, email=None):
    if fullname is None:
        fullname = get_fullname()
    if email is None:
        email = get_email()
    template_data = dict(fullname=fullname, email=email)
    batchinfo = gpg_keygen_batchfile % template_data
    generate_gpg_key(batchinfo)

#gpg --fingerprint "GPG User" | grep ^pub | cut -f2 -d/ | cut -f1 -d' '
def get_gpg_keyid(username):
    cmd = ['gpg', '--list-key', username]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    pub_line = None
    for line in proc.stdout:
        if line.startswith('pub'):
            pub_line = line.strip()
            pub, size_id, kdate = pub_line.split()
            keyid = size_id.split('/')[1]
    if pub_line is None:
        raise RuntimeError , 'gpg key not found'
    return keyid

# we don't care about bad sigs
# we just want to extract the keyid's
# from the signature
# The subprocess should return 1
def get_keyids_from_sig(fileobj):
    keyids = []
    fileobj.seek(0)
    cmd = ['gpg', '--verify', '-', '-']
    proc = subprocess.Popen(cmd, stdin=fileobj, stderr=subprocess.PIPE)
    proc.wait()
    for line in proc.stderr:
        if line.startswith('gpg: Signature made'):
            parts = line.split()
            if parts[-3] == 'key' and parts[-2] == 'ID':
                keyid = parts[-1]
                keyids.append(keyid)
            else:
                raise RuntimeError, "unable to parse line: %s" % line
    return keyids


class KeyHelper(object):
    def __init__(self, config):
        self.config = config

    
    def _pushd_home(self):
        here = path.getcwd()
        homedir = path('~/').expand()
        os.chdir(homedir)
        return here

    def initialize(self):
        outparent = self.config.getpath('DEFAULT', 'reprepro_parent_outdir')
        here = self._pushd_home()
        gnupg_confdir = path('.gnupg')
        if gnupg_confdir.isdir():
            print "It appears that repserve's ~/.gnupg has already been initialized"
            return
        fullname = self.config.get('DEFAULT', 'fullname')
        email = self.config.get('DEFAULT', 'email')
        if not email:
            email = None
        make_default_signing_key(fullname=fullname, email=email)
        keyid = get_gpg_keyid(fullname)
        #print "found key id", keyid
        self.config.set('DEFAULT', 'signwith', keyid)
        self.config.write_file()
        self.export_archive_key(keyid=keyid, outdir=outparent)
        os.chdir(here)
        
    def export_archive_key(self, keyid=None, outdir=None, overwrite=False):
        if keyid is None:
            if not self.config.has_option('DEFAULT', 'signwith'):
                raise NoArchiveKeyError , "Unable to find archive key"
            keyid = self.config.get('DEFAULT', 'signwith')
        if outdir is None:
            outdir = self.config.getpath('DEFAULT', 'reprepro_parent_outdir')
        filename = outdir / 'archive.gpg'
        if not filename.isfile() or overwrite:
            # change umask to make sure public key is world readable
            oldmask = os.umask(022)
            here = self._pushd_home()
            command = ['gpg', '--export', '--armour']
            if overwrite:
                command.append('--yes')
            command += ['--output', str(filename), keyid]
            #print "DEBUG: %s" % ' '.join(command)
            subprocess.check_call(command)
            os.umask(oldmask)
            os.chdir(here)
        else:
            print "%s already exists" % filename



if __name__ == '__main__':
    pass


    
