"""
theseus_tempfile_cr — Clean-room tempfile module.
No import of the standard `tempfile` module.
"""

import os as _os
import sys as _sys
import io as _io
import stat as _stat
import random as _random
import string as _string
import time as _time
import weakref as _weakref
import threading as _threading
import errno as _errno


_allocate_lock = _threading.Lock
_text_openflags = _os.O_RDWR | _os.O_CREAT | _os.O_EXCL
if hasattr(_os, 'O_NOFOLLOW'):
    _text_openflags |= _os.O_NOFOLLOW
_bin_openflags = _text_openflags | getattr(_os, 'O_BINARY', 0)

_once_lock = _threading.Lock()

try:
    _O_TMPFILE = _os.O_TMPFILE
except AttributeError:
    _O_TMPFILE = None

try:
    _os.stat('/tmp')
    _default_dir = '/tmp'
except OSError:
    _default_dir = _os.curdir


_name_sequence = None


class _RandomNameSequence:
    characters = 'abcdefghijklmnopqrstuvwxyz0123456789_'

    @property
    def rng(self):
        cur_pid = _os.getpid()
        if cur_pid != getattr(self, '_rng_pid', None):
            self._rng = _random.Random()
            self._rng_pid = cur_pid
        return self._rng

    def __iter__(self):
        return self

    def __next__(self):
        c = self.characters
        choose = self.rng.choice
        letters = [choose(c) for _ in range(8)]
        return ''.join(letters)


def _get_candidate_names():
    global _name_sequence
    if _name_sequence is None:
        with _once_lock:
            if _name_sequence is None:
                _name_sequence = _RandomNameSequence()
    return _name_sequence


def _get_default_tempdir():
    for d in [_os.environ.get('TMPDIR', ''), _os.environ.get('TEMP', ''),
              _os.environ.get('TMP', ''), '/tmp', '/var/tmp', '/usr/tmp', _os.curdir]:
        if d:
            try:
                fd, name = _os.open(d, _bin_openflags, 0o600), None
                try:
                    _os.close(fd)
                    _os.unlink(name) if name else None
                except:
                    pass
                return d
            except (OSError, AttributeError):
                pass
    raise FileNotFoundError("No usable temporary directory found")


def gettempdir():
    """Return the default temporary directory."""
    return _os.environ.get('TMPDIR', _os.environ.get('TEMP', _os.environ.get('TMP', '/tmp')))


def gettempdirb():
    """Return the default temporary directory as bytes."""
    return gettempdir().encode()


def gettempprefix():
    return 'tmp'


def gettempprefixb():
    return b'tmp'


def _sanitize_params(prefix, suffix, dir):
    if prefix is None:
        prefix = gettempprefix()
    if suffix is None:
        suffix = ''
    if dir is None:
        dir = gettempdir()
    return prefix, suffix, dir


def mkstemp(suffix=None, prefix=None, dir=None, text=False):
    """Create and return a unique temporary file."""
    prefix, suffix, dir = _sanitize_params(prefix, suffix, dir)
    if text:
        flags = _text_openflags
    else:
        flags = _bin_openflags
    for seq in _get_candidate_names():
        name = _os.path.join(dir, prefix + seq + suffix)
        try:
            fd = _os.open(name, flags, 0o600)
            return fd, _os.path.abspath(name)
        except FileExistsError:
            continue
        except PermissionError:
            if _os.path.isdir(dir) and _os.access(dir, _os.W_OK):
                continue
            raise
    raise FileExistsError("No usable temporary filename found")


def mkdtemp(suffix=None, prefix=None, dir=None):
    """Create and return a unique temporary directory."""
    prefix, suffix, dir = _sanitize_params(prefix, suffix, dir)
    for seq in _get_candidate_names():
        name = _os.path.join(dir, prefix + seq + suffix)
        try:
            _os.mkdir(name, 0o700)
            return _os.path.abspath(name)
        except FileExistsError:
            continue
        except PermissionError:
            if _os.path.isdir(dir) and _os.access(dir, _os.W_OK):
                continue
            raise
    raise FileExistsError("No usable temporary directory name found")


def mktemp(suffix='', prefix='tmp', dir=None):
    """Return an absolute pathname of a file that did not exist at call time."""
    if dir is None:
        dir = gettempdir()
    for seq in _get_candidate_names():
        name = _os.path.join(dir, prefix + seq + suffix)
        if not _os.path.exists(name):
            return name
    raise FileExistsError("No usable temporary filename found")


class _TemporaryFileCloser:
    file = None
    close_called = False
    cleanup_called = False

    def __init__(self, file, name, delete=True, delete_on_close=True):
        self.file = file
        self.name = name
        self.delete = delete
        self.delete_on_close = delete_on_close

    def cleanup(self, windows=False):
        if not self.cleanup_called:
            self.cleanup_called = True
            try:
                self.file.close()
            finally:
                if self.delete:
                    self.unlink(self.name)

    def unlink(self, name):
        try:
            _os.unlink(name)
        except OSError:
            pass

    def close(self):
        if not self.close_called and self.file is not None:
            self.close_called = True
            try:
                self.file.close()
            finally:
                if self.delete and self.delete_on_close:
                    self.unlink(self.name)

    def __del__(self):
        self.cleanup()


class _TemporaryFileWrapper:
    """Wrapper around temporary file for auto-deletion."""

    def __init__(self, file, name, delete=True, delete_on_close=True):
        self.file = file
        self.name = name
        self.delete = delete
        self._closer = _TemporaryFileCloser(file, name, delete, delete_on_close)

    def __getattr__(self, name):
        a = self.__dict__.get('file')
        if a is None:
            raise AttributeError(name)
        return getattr(a, name)

    def __enter__(self):
        self.file.__enter__()
        return self

    def __exit__(self, exc, value, tb):
        result = self.file.__exit__(exc, value, tb)
        if self.delete:
            self._closer.cleanup()
        return result

    def close(self):
        self._closer.close()

    def __iter__(self):
        for line in self.file:
            yield line


def NamedTemporaryFile(mode='w+b', buffering=-1, encoding=None, newline=None,
                       suffix=None, prefix=None, dir=None, delete=True,
                       *, errors=None, delete_on_close=True):
    """Create and return a temporary file."""
    prefix, suffix, dir = _sanitize_params(prefix, suffix, dir)

    flags = _bin_openflags
    file = None
    fd, name = mkstemp(suffix=suffix, prefix=prefix, dir=dir)
    try:
        file = open(fd, mode, buffering=buffering, encoding=encoding, newline=newline, errors=errors)
        return _TemporaryFileWrapper(file, name, delete, delete_on_close)
    except:
        try:
            _os.close(fd)
        except:
            pass
        try:
            _os.unlink(name)
        except:
            pass
        raise


TemporaryFile = NamedTemporaryFile


class TemporaryDirectory:
    """A context manager that creates a temporary directory."""

    def __init__(self, suffix=None, prefix=None, dir=None,
                 ignore_cleanup_errors=False, *, delete=True):
        self.name = mkdtemp(suffix, prefix, dir)
        self._ignore_cleanup_errors = ignore_cleanup_errors
        self._delete = delete
        self._finalizer = _weakref.finalize(
            self, self._cleanup, self.name,
            warn_message="Implicitly cleaning up {!r}".format(self))

    @classmethod
    def _rmtree(cls, name, ignore_errors=False):
        import shutil
        shutil.rmtree(name, ignore_errors=ignore_errors)

    @classmethod
    def _cleanup(cls, name, warn_message=None):
        try:
            cls._rmtree(name)
        except Exception:
            pass

    def __repr__(self):
        return '<{} {!r}>'.format(self.__class__.__name__, self.name)

    def __enter__(self):
        return self.name

    def __exit__(self, exc, value, tb):
        self.cleanup()

    def cleanup(self):
        if self._finalizer.detach() or _os.path.exists(self.name):
            self._rmtree(self.name, ignore_errors=self._ignore_cleanup_errors)

    def __del__(self):
        self.cleanup()


class SpooledTemporaryFile:
    """A file-like object that starts in memory and spills to disk."""

    _rolled = False

    def __init__(self, max_size=0, mode='w+b', buffering=-1,
                 encoding=None, newline=None, suffix=None, prefix=None,
                 dir=None, *, errors=None):
        if 'b' in mode:
            self._file = _io.BytesIO()
        else:
            self._file = _io.StringIO()
        self._max_size = max_size
        self._rolled = False
        self._TemporaryFileArgs = {
            'mode': mode, 'buffering': buffering, 'suffix': suffix,
            'prefix': prefix, 'dir': dir, 'encoding': encoding,
            'newline': newline,
        }

    def _check(self, file):
        if self._rolled:
            return
        max_size = self._max_size
        if max_size and file.tell() > max_size:
            self.rollover()

    def rollover(self):
        if self._rolled:
            return
        file = self._file
        newfile = self._file = NamedTemporaryFile(**self._TemporaryFileArgs)
        newfile.write(file.getvalue())
        newfile.seek(file.tell())
        self._rolled = True

    def write(self, s):
        self._file.write(s)
        self._check(self._file)

    def read(self, *args):
        return self._file.read(*args)

    def seek(self, *args):
        return self._file.seek(*args)

    def tell(self):
        return self._file.tell()

    def getvalue(self):
        return self._file.getvalue()

    def close(self):
        self._file.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self._file.__exit__(*args)

    def __iter__(self):
        return self._file.__iter__()


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def tempfile2_mkstemp():
    """mkstemp creates a temporary file; returns True."""
    fd, path = mkstemp()
    try:
        _os.close(fd)
        return _os.path.exists(path)
    finally:
        try:
            _os.unlink(path)
        except OSError:
            pass


def tempfile2_mkdtemp():
    """mkdtemp creates a temporary directory; returns True."""
    d = mkdtemp()
    try:
        return _os.path.isdir(d)
    finally:
        try:
            _os.rmdir(d)
        except OSError:
            pass


def tempfile2_named():
    """NamedTemporaryFile creates and auto-deletes a temp file; returns True."""
    with NamedTemporaryFile() as f:
        name = f.name
        f.write(b'test')
        exists_during = _os.path.exists(name)
    return exists_during


__all__ = [
    'NamedTemporaryFile', 'TemporaryFile', 'SpooledTemporaryFile',
    'TemporaryDirectory', 'mkstemp', 'mkdtemp', 'mktemp',
    'gettempdir', 'gettempdirb', 'gettempprefix', 'gettempprefixb',
    'tempfile2_mkstemp', 'tempfile2_mkdtemp', 'tempfile2_named',
]
