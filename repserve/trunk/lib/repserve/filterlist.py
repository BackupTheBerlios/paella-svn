from repserve.path import path

class FilterList(list):
    def __init__(self, iterable=[]):
        list.__init__(self, iterable)
        # by default just use package names
        # if self.contains_items is True, we
        # store a list of (package, action) items
        # Setting this does nothing now
        self.contains_items = False

    def parse_file(self, filename):
        lines = path(filename).lines()
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
        self.sort()
        lines = ['%s\tinstall' % p for p in self]
        return lines
    
    def write_file(self, filename):
        lines = self._create_lines()
        path(filename).write_lines(lines)


    def remove_package(self, package):
        if package in self:
            index = self.index(package)
            self.pop(index)
        
    
if __name__ == '__main__':
    filename = 'test~'
    fl = FilterList()
    fl.merge_file(filename)
    
