"""
theseus_shelve_cr — Clean-room shelve module.
No import of the standard `shelve` module.
"""

import dbm as _dbm
import _pickle as _pickle_mod
import io as _io


def _dumps(obj):
    buf = _io.BytesIO()
    _pickle_mod.Pickler(buf).dump(obj)
    return buf.getvalue()


def _loads(data):
    return _pickle_mod.Unpickler(_io.BytesIO(data)).load()


class Shelf(dict):
    """Persistent dict-like object backed by a dbm database."""

    def __init__(self, dict, flag='c', writeback=False):
        self.dict = dict
        self.writeback = writeback
        self.cache = {}

    def keys(self):
        return [k.decode() if isinstance(k, bytes) else k for k in self.dict.keys()]

    def __len__(self):
        return len(self.dict)

    def __contains__(self, key):
        return key.encode() in self.dict or key in self.dict

    def get(self, key, default=None):
        if key in self:
            return self[key]
        return default

    def __getitem__(self, key):
        if self.writeback and key in self.cache:
            return self.cache[key]
        try:
            value = _loads(self.dict[key.encode()])
        except KeyError:
            value = _loads(self.dict[key])
        if self.writeback:
            self.cache[key] = value
        return value

    def __setitem__(self, key, value):
        if self.writeback:
            self.cache[key] = value
        self.dict[key.encode()] = _dumps(value)

    def __delitem__(self, key):
        if self.writeback:
            self.cache.pop(key, None)
        try:
            del self.dict[key.encode()]
        except KeyError:
            del self.dict[key]

    def __iter__(self):
        for k in self.dict.keys():
            yield k.decode() if isinstance(k, bytes) else k

    def items(self):
        for k in self:
            yield k, self[k]

    def values(self):
        for k in self:
            yield self[k]

    def close(self):
        try:
            self.dict.close()
        except AttributeError:
            pass

    def sync(self):
        if self.writeback and self.cache:
            self.writeback = False
            for key, entry in self.cache.items():
                self[key] = entry
            self.writeback = True
            self.cache = {}
        try:
            self.dict.sync()
        except AttributeError:
            pass

    def __enter__(self):
        return self

    def __exit__(self, typ, val, tb):
        self.close()
        return False

    def __repr__(self):
        return f'<{type(self).__name__} object at {id(self):#x}>'


class DbfilenameShelf(Shelf):
    """Shelf implementation using a file-backed dbm database."""

    def __init__(self, filename, flag='c', protocol=None, writeback=False):
        self._protocol = protocol
        Shelf.__init__(self, _dbm.open(filename, flag), writeback=writeback)


def open(filename, flag='c', protocol=None, writeback=False):
    """Open a persistent dictionary for reading and writing."""
    return DbfilenameShelf(filename, flag, protocol, writeback)


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def shelve2_open_close():
    """open/set/get/close works correctly; returns True."""
    import os, tempfile
    fd, tmpfile = tempfile.mkstemp()
    os.close(fd)
    os.unlink(tmpfile)
    try:
        s = open(tmpfile, flag='n')
        s['key'] = 'value'
        val = s['key']
        s.close()
        return val == 'value'
    except Exception:
        return False
    finally:
        for ext in ['', '.db', '.dir', '.bak', '.dat']:
            try:
                os.unlink(tmpfile + ext)
            except FileNotFoundError:
                pass


def shelve2_keys():
    """keys() returns stored keys; returns True."""
    import os, tempfile
    fd, tmpfile = tempfile.mkstemp()
    os.close(fd)
    os.unlink(tmpfile)
    try:
        s = open(tmpfile, flag='n')
        s['a'] = 1
        s['b'] = 2
        keys = s.keys()
        s.close()
        return 'a' in keys and 'b' in keys
    except Exception:
        return False
    finally:
        for ext in ['', '.db', '.dir', '.bak', '.dat']:
            try:
                os.unlink(tmpfile + ext)
            except FileNotFoundError:
                pass


def shelve2_context_manager():
    """shelf works as context manager; returns True."""
    import os, tempfile
    fd, tmpfile = tempfile.mkstemp()
    os.close(fd)
    os.unlink(tmpfile)
    try:
        with open(tmpfile, flag='n') as s:
            s['x'] = [1, 2, 3]
        with open(tmpfile) as s:
            return s['x'] == [1, 2, 3]
    except Exception:
        return False
    finally:
        for ext in ['', '.db', '.dir', '.bak', '.dat']:
            try:
                os.unlink(tmpfile + ext)
            except FileNotFoundError:
                pass


__all__ = [
    'Shelf', 'DbfilenameShelf', 'open',
    'shelve2_open_close', 'shelve2_keys', 'shelve2_context_manager',
]
