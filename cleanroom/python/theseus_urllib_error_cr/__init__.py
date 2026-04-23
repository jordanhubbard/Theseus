"""
theseus_urllib_error_cr — Clean-room urllib.error module.
No import of urllib.error.
"""


class URLError(OSError):
    def __init__(self, reason, filename=None):
        self.reason = reason
        super().__init__(reason)
        if filename is not None:
            self.filename = filename

    def __str__(self):
        return f'<urlopen error {self.reason}>'


class HTTPError(URLError):
    def __init__(self, url, code, msg, hdrs, fp):
        self.url = url
        self.code = code
        self.msg = msg
        self.headers = hdrs
        self.hdrs = hdrs
        self.fp = fp
        super().__init__(msg)

    def __str__(self):
        return f'HTTP Error {self.code}: {self.msg}'

    def read(self):
        return self.fp.read() if self.fp else b''

    def close(self):
        if self.fp:
            self.fp.close()

    def info(self):
        return self.headers

    def geturl(self):
        return self.url

    def getcode(self):
        return self.code


class ContentTooShortError(URLError):
    def __init__(self, message, content):
        super().__init__(message)
        self.content = content


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def urlerror2_class():
    """URLError is an OSError subclass; returns True."""
    err = URLError('test reason')
    return isinstance(err, OSError) and err.reason == 'test reason'


def urlerror2_httperror():
    """HTTPError has code, msg, headers attributes; returns True."""
    import io as _io
    err = HTTPError('http://example.com', 404, 'Not Found', {}, _io.BytesIO(b''))
    return err.code == 404 and err.msg == 'Not Found' and isinstance(err, URLError)


def urlerror2_contenttoo():
    """ContentTooShortError exists as IOError subclass; returns True."""
    err = ContentTooShortError('too short', b'data')
    return isinstance(err, URLError) and err.content == b'data'


__all__ = [
    'URLError', 'HTTPError', 'ContentTooShortError',
    'urlerror2_class', 'urlerror2_httperror', 'urlerror2_contenttoo',
]
