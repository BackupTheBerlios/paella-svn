import sys
import subprocess
import tempfile
import urlparse
import urllib2

import apt_pkg

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



# taken from useless
class Url(str):
    """This class is useful for parsing and unparsing
    urls, and having attribute access to a parsed url.
    attributes are protocol, host, path, parameters, query, and frag_id.
    """
    
    def __init__(self, url=''):
        str.__init__(self, str(url))
        self.url_orig = url
        self.seturl(url)
        
    def seturl(self, url):
        """Uses urlparse to set the attributes for url"""
        url = str(url)
        protocol, host, path_, parameters, query, frag_id = urlparse.urlparse(url)
        self.protocol = protocol
        self.host = host
        self.path = path(path_)
        self.parameters = parameters
        self.query = query
        self.frag_id = frag_id

    def astuple(self):
        """return url as tuple from urlparse"""
        return (self.protocol, self.host, self.path, self.parameters,
                self.query, self.frag_id)

    def asdict(self):
        """return url as a dictionary where the url attributes are keys"""
        return dict(protocol=self.protocol, host=self.host, path=self.path,
                    parameters=self.parameters, query=self.query, frag_id=self.frag_id)

    def set_path(self, path_):
        """Method for setting the path attribute, and coercing it to be
        a path instance."""
        if not isinstance(path_, path):
            path_ = path(path_)            
        self.path = path_
        
    def output(self):
        return str(urlparse.urlunparse(self.astuple()))

    def __repr__(self):
        return 'Url(%s)' % self.output()

    def __str__(self):
        return self.output()

    def __eq__(self, other):
        return other.__eq__(self.output())
    
    # this method is not in useless
    def open(self):
        return urllib2.urlopen(str(self))
    

def parse_aptsource_line(line):
    line = line.strip()
    parts = line.split()
    debtype = parts[0]
    uri = Url(parts[1])
    if uri.startswith('cdrom:'):
        print "WARNING: cdrom sources aren't parsed properly"
        print "cdrom methods are ignored with repserve"
    dist = parts[2]
    components = parts[3:]
    parsed = dict(arch=debtype, uri=uri, dist=dist,
                  components=components)
    return parsed


def parse_sources_list(filename='/etc/apt/sources.list', arch=None):
    if arch is None:
        arch = get_architecture()
    debarch = {'deb':arch, 'deb-src':'source'}
    parsed_sources = []
    source_lines = path(filename).lines()
    for line in source_lines:
        line = line.strip()
        if line.startswith('deb'):
            parsed = parse_aptsource_line(line)
            if parsed['arch'] in debarch:
                parsed['arch'] = debarch[parsed['arch']]
            else:
                raise RuntimeError , "can't handle debtype %s" % parsed['arch']
            parsed_sources.append(parsed)
    return parsed_sources

def retrieve_release_file(url, codename):
    url = Url(url)
    relpath = 'dists/%s/Release' % codename
    url.path = url.path / relpath
    return url.open()

def parse_release_file(fileobj):
    parsed = apt_pkg.ParseTagFile(fileobj)
    # There should only be one section
    if parsed.Step() != 1:
        raise RuntimeError , "There was a problem parsing the Release file"
    section = parsed.Section
    keys = section.keys()
    release = dict()
    for key in keys:
        release[key.lower()] = section[key]
    return release

def retrieve_and_parse_release_file(url, codename):
    ufile = retrieve_release_file(url, codename)
    tfile = tempfile.TemporaryFile()
    tfile.write(ufile.read())
    tfile.seek(0)
    release = parse_release_file(tfile)
    return release

# This is a helper function to use stdin for
# the contents of a file, for functions
# that require filename arguments.
# Returns a filename to use as an argument
# to the function.
def use_stdin_instead_of_filename(self):
    infile = sys.stdin
    ignore, filename = tempfile.mkstemp('infile', 'repserve')
    outfile = file(filename, 'wb')
    block = sys.stdin.read(BLOCK_SIZE)
    while block:
        outfile.write(block)
        block = sys.stdin.read(BLOCK_SIZE)
    outfile.close()
    return filename
    
    


if __name__ == '__main__':
    url = Url('http://10.1.0.1/debrepos/debian')
    r = retrieve_release_file(url, 'lenny').read()
    rel = retrieve_and_parse_release_file(url, 'lenny')
    

    
