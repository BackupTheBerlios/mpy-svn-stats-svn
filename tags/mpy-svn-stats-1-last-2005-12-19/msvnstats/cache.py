
import shelve

"""Cache information about revisions.
Uses anydbm.

Features:

 - never expires automatically
 - no external requirements - uses anydbm/shelve
 - multiple repositories can be stored

"""


class Cache(object):
    """Cache object.
    Encapsulates whole cache database associated with one file.
    All operations are done via this object.

    Cache object is used mainly to store diffs now.

    It might be used to store blames in future.

    """

    class Modification(object):
        """Internal cache's reprezentation of information
        about file (path) modification.

        Attributes:
          
          - path
          - type - modification type (string):
           
            - A for adding
            - M for modyfing existing file

          - diff - diff to previous version of the same file/path (if available)
        
        """

        def __init__(self, path=None):
            self.path = path 
            self.type = None
            self.diff = None


    class Revision(object):
        """Internal cache's revision object kept in shelve.
        Attributes:
        
         - revision_number
         - modified_paths - dictionary of modified paths, values are Modification objects.
         - log_message
         - author

        """

        def __init__(self, repository_url=None, revision_number=None):
            self.repository_url = repository_url
            self.revision_number = revision_number
            self.modified_paths = {}
            self.log_message = None
            self.author = None

        def get_modification(self, path):
            if path in self.modified_paths:
                return self.modified_paths[path]
            else:
                return Modification(path)

        def set_modification(self, path, mod):
            self.modified_paths[path] = mod

        def set_diff(self, path, diff):
            mod = self.get_modification(path)
            mod.diff = diff
            self.set_modification(path, mod)
    
    def __init__(self, filename='msvnstats.db'):
        """Create cache object."""
        self.filename = filename
        self.db = anydbm.open(self.filename, 'c')

    def revision_key(repository_url, revision_number):
        key = '%s-%d' % (repository_url, revision_number)

    def get_revision(self, repository_url, revision_number):
        key = self.revision_key(repository_url, revision_number)
        if key in self.db:
            rev = self.db[key]
        else:
            rev = self.Revision(repository_url, revision_number)
        return rev

    def set_revision(self, repository_url, revision_number, rev):
        self.db[self.revision_key(repository_url, revision_number] = rev
    
    def set_diff(self, repository_url, revision_number, path, diff):
        rev = self.get_revision(repository_url, revision_number)
        rev.set_diff(path, diff)
        self.set_revision(repository_url, revision_number, rev)

