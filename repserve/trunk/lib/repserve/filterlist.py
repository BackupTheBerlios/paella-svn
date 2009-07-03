from repserve.path import path

class FilterList(list):
    def __init__(self, name, iterable=[]):
        list.__init__(self, iterable)
        self.name = name
        # by default just use package names
        # if self.contains_items is True, we
        # store a list of (package, action) items
        # Setting this does nothing now
        self.contains_items = False

    def parse_filterlist(self, confdir):
        filename = path(confdir) / self.name
        return self.parse_file(filename)

    def parse_file(self, filename):
        lines = path(filename).lines()
        return self.parse_lines(lines)
    
    def parse_contents(self, contents):
        lines = contents.split('\n')
        return self.parse_lines(lines)
    
    def parse_lines(self, lines):
        # strip newlines
        lines = [line.strip() for line in lines]
        # remove comments
        lines = [line for line in lines if not line.startswith('#')]
        # remove empty lines
        lines = [line for line in lines if line]
        # split the lines into [package, action] pairs
        items = [line.split() for line in lines]
        # fail if an item doesn't have two components
        for item in items:
            if len(item) != 2:
                raise RuntimeError , "The line containing %s wasn't parsed correctly" % item
        # If this class contains items, instead of just
        # package names, we return the items parsed
        if self.contains_items:
            return items
        # Otherwise, we return a list of pakages
        packages = []
        for package, action in items:
            # don't know what to do when action != install, so at least
            # inform us when it occurs
            if action != 'install':
                print "Action for package %s is %s" % (package, action)
            packages.append(package)
        packages.sort()
        return packages

    def merge_file(self, filename, empty_first=False):
        if empty_first:
            while len(self):
                self.pop()
        packages = self.parse_file(filename)
        for package in packages:
            if package not in self:
                self.append(package)
        self.sort()

    def _create_lines(self):
        if not self.contains_items:
            self.sort()
            lines = ['%s\tinstall' % p for p in self]
        else:
            data = dict(self)
            keys = data.keys()
            keys.sort()
            lines = ['%s\t%s' % (key, data[key]) for key in keys]
        return lines

    def _write_file(self, filename):
        filename = path(filename)
        lines = self._create_lines()
        filename.write_lines(lines)
        
    def write_file(self, confdir):
        filename = path(confdir) / self.name
        self._write_file(filename)
        
    def remove_package(self, package):
        if package in self:
            index = self.index(package)
            self.pop(index)
        


class FilterListManager(object):
    def __init__(self, config):
        self.config = config
        self.lists = dict()
        self.section = None
        
    def set_section(self, section):
        self.section = section
        self.lists  = dict()
        self.read_filterlists(section)
        
    def read_filterlists(self, section):
        names = self.config.get_filterlist_names(section)
        confdir = self.config.get_confdir(section)
        for name in names:
            filterlist = FilterList(name)
            filterlist.parse_file(confdir)
            self.lists[name] = filterlist

    def add_filterlist_to_section(self, section, filterlist):
        name = filterlist.name
        self.config.add_filterlist_to_section(name, section)
        confdir = self.config.get_confdir(section)
        filterlist.write_file(confdir)
        self.config.write_file()

    def remove_filterlist_from_section(self, name, section):
        self.config.remove_filterlist_from_section(name, section)
        self.config.write_file()
                
    def make_filterlist(self, name, packages=[], filename=None):
        flist = FilterList(name, packages)
        if filename is not None:
            packages = flist.parse_file(filename)
            while len(flist):
                flist.pop()
            flist += packages
        return flist
    
            
    

    
if __name__ == '__main__':
    filename = 'test~'
    fl = FilterList()
    fl.merge_file(filename)
    
