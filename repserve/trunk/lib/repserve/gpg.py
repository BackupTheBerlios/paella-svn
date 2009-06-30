import os
import subprocess
import pwd



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


if __name__ == '__main__':
    pass


    
