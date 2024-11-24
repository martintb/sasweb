from io import BytesIO
from urllib.request import urlopen

class CustomFileOpen:
    '''Custom context manager to fetch file contents depending on where the file is located.'''
    def __init__(self, filename, mode='rb'):
        self.filename = filename
        self.mode = mode
        self.fd = None

    def __enter__(self):
        """A context method that either fetches a file from a URL or opens a local file."""
        if hasattr(self.filename, 'read'):
            #already a file-like object
            self.fd = self.filename

        elif '://' in self.filename:
            # Use urllib.request package to access remote files
            with urlopen(self.filename) as req:
                content = req.read()
                self.fd = BytesIO(content)
                self.fd.name = self.filename
        else:
            # Use native open to access local files
            self.fd = open(self.filename, self.mode)
        # Return the instance to allow access to the filename, and any open file handles.
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Close all open file handles when exiting the context manager."""
        if self.fd is not None:
            self.fd.close()

# Monkey patch the CustomFileOpen class into the sasdata.data_util module
from sasdata.data_util import registry
registry.CustomFileOpen = CustomFileOpen
