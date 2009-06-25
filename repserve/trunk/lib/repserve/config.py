from ConfigParser import ConfigParser

DEFAULT_CONFIG = """# default config file for repserve
[DEFAULT]
basedir: /srv/reprepro
outdir:  %(basedir)s
confdir: %(basedir)s/conf
distdir: %(outdir)s/dists
logdir:  %(basedir)s/logs
dbdir:   %(basedir)s/db
listdir: %(basedir)s/lists

# example
#[lenny]
#codename: lenny
#components: main contrib non-free
#archs:  amd64 source
#ignore_release:  True
#method:  http://ftp.us.debian.org/debian

[section]
# another section
"""

class BaseConfig(ConfigParser):
    # allow for uppercase options
    optionxform = str
    
    def __init__(self):
        ConfigParser.__init__(self)
        filename = '/etc/apt/repserve.conf'
        
    def getlist(self, section, option, sep=' '):
        value = self.get(section, option)
        return [p.strip() for p in value.split(sep)]

    




