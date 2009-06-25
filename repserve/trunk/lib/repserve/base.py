import subprocess
import tempfile

from repserve.path import path

BLOCK_SIZE = 1024

def get_architecture():
    proc = subprocess.Popen(['dpkg', '--print-architecture'],
                            stdout=subprocess.PIPE)
    arch = proc.stdout.read().strip()
    retcode = proc.wait()
    if retcode:
        raise RuntimeError , "dpkg returned %d" % retcode
    return arch

def unzip_list_file(filename):
    filename = path(filename)
    cmd = ['gzip', '-cd', filename]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    tmpfile = tempfile.TemporaryFile()
    block = proc.stdout.read(BLOCK_SIZE)
    while block:
        tmpfile.write(block)
        block = proc.stdout.read(BLOCK_SIZE)
    retval = proc.wait()
    if retval:
        raise RuntimeError , "Problem reading/unzipping %s" % filename
    tmpfile.seek(0)
    return tmpfile

    
if __name__ == '__main__':
    pass

    
