import sys

from repserve.config import sources_to_config


class RepserveHandler(object):
    def __init__(self, config):
        self.config = config

    def add_apt_sources(self, filename=None, arch=None):
        if filename is None:
            infile = sys.stdin
        else:
            infile = file(filename)
        
        
