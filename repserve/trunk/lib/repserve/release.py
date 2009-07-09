import subprocess
from subprocess import CalledProcessError
import tempfile

import apt_pkg

from repserve.base import Url
from repserve.path import path
from repserve.gpg import get_keyids_from_sig

class ReleaseParser(object):
    def __init__(self):
        pass

    def _urlopen_to_tempfile(self, addinfourl):
        tfile = tempfile.TemporaryFile()
        tfile.write(addinfourl.read())
        tfile.seek(0)
        return tfile
    
    def retrieve_release_file(self, url, codename, gpg=False):
        url = Url(url)
        ext = ''
        if gpg:
            ext = '.gpg'
        relpath = 'dists/%s/Release%s' % (codename, ext)
        url.path = url.path / relpath
        return url.open()

    def parse_release_file(self, fileobj):
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
        
    def retrieve_and_parse_release_file(self, url, codename):
        ufile = self.retrieve_release_file(url, codename)
        tfile = self._urlopen_to_tempfile(ufile)
        release = self.parse_release_file(tfile)
        return release

    def handle_release(self, url, codename):
        release = self.retrieve_and_parse_release_file(url, codename)
        # this will fail if there is no Release.gpg file
        # when I figure out the exception that is raised, this
        # will be wrapped in a try: statement
        relgpg = self.retrieve_release_file(url, codename, gpg=True)
        relgpg = self._urlopen_to_tempfile(relgpg)
        keyids = get_keyids_from_sig(relgpg)
        release['keyids'] = '|'.join(keyids)
        return release
    

if __name__ == '__main__':
    url = Url('http://10.1.0.1/debrepos/debian')
    parser = ReleaseParser()
    #r = retrieve_release_file(url, 'lenny').read()
    #rel = retrieve_and_parse_release_file(url, 'lenny')
    rel = parser.handle_release(url, 'lenny')
    

    
