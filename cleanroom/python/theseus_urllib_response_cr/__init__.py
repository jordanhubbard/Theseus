"""
theseus_urllib_response_cr — Clean-room urllib.response module.
No import of the standard `urllib.response` module.
"""

import io as _io


class addbase:
    """Base class for addinfo and addinfourl."""

    def __init__(self, fp):
        self.fp = fp

    def read(self, n=-1):
        return self.fp.read(n)

    def readline(self, n=-1):
        return self.fp.readline(n)

    def readlines(self, hint=-1):
        return self.fp.readlines(hint)

    def __iter__(self):
        return iter(self.fp)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def __repr__(self):
        return '<%s at %r whose fp = %r>' % (self.__class__.__name__,
                                              id(self), self.fp)

    def close(self):
        self.read = None
        self.readline = None
        self.readlines = None
        self.__iter__ = None
        if hasattr(self.fp, 'close'):
            self.fp.close()
        self.fp = None

    @property
    def closed(self):
        return self.fp is None

    def info(self):
        return self.headers

    def geturl(self):
        return self.url


class addinfo(addbase):
    """class to add an info() method to an open file."""

    def __init__(self, fp, headers):
        super().__init__(fp)
        self.headers = headers

    def info(self):
        return self.headers


class addinfourl(addbase):
    """class to add info() and geturl() methods to an open file."""

    def __init__(self, fp, headers, url, code=None):
        super().__init__(fp)
        self.headers = headers
        self.url = url
        self.code = code
        self.status = code

    def info(self):
        return self.headers

    def geturl(self):
        return self.url

    def getcode(self):
        return self.code

    @property
    def msg(self):
        return ''


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def urlresponse2_addinfo():
    """addinfo() wrapper class exists; returns True."""
    fp = _io.BytesIO(b'hello')
    obj = addinfo(fp, {'content-type': 'text/plain'})
    return isinstance(obj, addinfo) and obj.info() == {'content-type': 'text/plain'}


def urlresponse2_addinfourl():
    """addinfourl class exists with url/headers/code attrs; returns True."""
    fp = _io.BytesIO(b'data')
    obj = addinfourl(fp, {}, 'http://example.com', 200)
    return (isinstance(obj, addinfourl) and
            obj.url == 'http://example.com' and
            obj.code == 200)


def urlresponse2_methods():
    """addinfourl has read/info/geturl methods; returns True."""
    fp = _io.BytesIO(b'test data')
    obj = addinfourl(fp, {'x-test': '1'}, 'http://test.com', 200)
    return (callable(obj.read) and
            callable(obj.info) and
            callable(obj.geturl) and
            obj.read() == b'test data' and
            obj.geturl() == 'http://test.com')


__all__ = [
    'addbase', 'addinfo', 'addinfourl',
    'urlresponse2_addinfo', 'urlresponse2_addinfourl', 'urlresponse2_methods',
]