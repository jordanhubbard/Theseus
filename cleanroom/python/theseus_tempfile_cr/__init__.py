"""Clean-room reimplementation of a tempfile-style module.

Implements mkstemp, mkdtemp, and a NamedTemporaryFile-like context manager
without importing the standard ``tempfile`` package.
"""

import os
import sys
import errno


_RANDOM_CHARS = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_"
_NAME_LENGTH = 8
_MAX_ATTEMPTS = 10000
_DEFAULT_PREFIX = "tmp"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _candidate_tempdirs():
    """Yield candidate temporary directories in priority order."""
    for var in ("TMPDIR", "TEMP", "TMP"):
        v = os.environ.get(var)
        if v:
            yield v
    if sys.platform == "win32":
        yield os.path.join(os.environ.get("SystemRoot", "C:\\Windows"), "Temp")
        yield "C:\\Temp"
        yield "C:\\TMP"
        yield "\\TEMP"
        yield "\\TMP"
    else:
        yield "/tmp"
        yield "/var/tmp"
        yield "/usr/tmp"
    yield os.getcwd()


def _gettempdir():
    """Return a usable directory for temporary files."""
    for d in _candidate_tempdirs():
        if not d:
            continue
        try:
            if os.path.isdir(d) and os.access(d, os.R_OK | os.W_OK | os.X_OK):
                return d
        except OSError:
            continue
    # Last-ditch fallback.
    return os.getcwd()


def _random_name(length=_NAME_LENGTH):
    """Generate a random alphanumeric suffix using os.urandom."""
    raw = os.urandom(length)
    n = len(_RANDOM_CHARS)
    return "".join(_RANDOM_CHARS[b % n] for b in raw)


def _sanitize_template_part(value, default=""):
    if value is None:
        return default
    if isinstance(value, bytes):
        try:
            value = value.decode(sys.getfilesystemencoding() or "utf-8")
        except Exception:
            value = value.decode("latin-1", errors="replace")
    if not isinstance(value, str):
        raise TypeError("template parts must be str, bytes, or None")
    return value


# ---------------------------------------------------------------------------
# Core primitives
# ---------------------------------------------------------------------------

def mkstemp(suffix=None, prefix=None, dir=None, text=False):
    """Create a temporary file securely; return (fd, absolute_path).

    The file is created with O_EXCL and mode 0600. The caller is responsible
    for closing the file descriptor and deleting the file.
    """
    suffix = _sanitize_template_part(suffix, "")
    prefix = _sanitize_template_part(prefix, _DEFAULT_PREFIX)
    if dir is None:
        dir = _gettempdir()
    elif isinstance(dir, bytes):
        dir = dir.decode(sys.getfilesystemencoding() or "utf-8")

    flags = os.O_RDWR | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    if not text and hasattr(os, "O_BINARY"):
        flags |= os.O_BINARY
    if text and hasattr(os, "O_TEXT"):
        flags |= os.O_TEXT

    last_err = None
    for _ in range(_MAX_ATTEMPTS):
        name = prefix + _random_name() + suffix
        path = os.path.join(dir, name)
        try:
            fd = os.open(path, flags, 0o600)
        except FileExistsError:
            continue
        except OSError as e:
            if e.errno == errno.EEXIST:
                continue
            last_err = e
            raise
        return fd, os.path.abspath(path)

    if last_err is not None:
        raise last_err
    raise FileExistsError(errno.EEXIST,
                          "No usable temporary file name found")


def mkdtemp(suffix=None, prefix=None, dir=None):
    """Create a temporary directory securely; return its absolute path."""
    suffix = _sanitize_template_part(suffix, "")
    prefix = _sanitize_template_part(prefix, _DEFAULT_PREFIX)
    if dir is None:
        dir = _gettempdir()
    elif isinstance(dir, bytes):
        dir = dir.decode(sys.getfilesystemencoding() or "utf-8")

    last_err = None
    for _ in range(_MAX_ATTEMPTS):
        name = prefix + _random_name() + suffix
        path = os.path.join(dir, name)
        try:
            os.mkdir(path, 0o700)
        except FileExistsError:
            continue
        except OSError as e:
            if e.errno == errno.EEXIST:
                continue
            last_err = e
            raise
        return os.path.abspath(path)

    if last_err is not None:
        raise last_err
    raise FileExistsError(errno.EEXIST,
                          "No usable temporary directory name found")


def gettempdir():
    """Public accessor for the chosen temporary directory."""
    return _gettempdir()


def gettempprefix():
    return _DEFAULT_PREFIX


# ---------------------------------------------------------------------------
# NamedTemporaryFile-like wrapper
# ---------------------------------------------------------------------------

class _NamedTemporaryFile:
    """A named temporary file that is automatically deleted on close.

    Behaves like a context manager and proxies file operations to the
    underlying file object opened from the descriptor returned by mkstemp.
    """

    def __init__(self, mode="w+b", buffering=-1, encoding=None, newline=None,
                 suffix=None, prefix=None, dir=None, delete=True):
        binary = "b" in mode
        fd, name = mkstemp(suffix=suffix, prefix=prefix, dir=dir, text=not binary)
        try:
            if binary:
                self._file = os.fdopen(fd, mode, buffering)
            else:
                self._file = os.fdopen(fd, mode, buffering,
                                       encoding=encoding, newline=newline)
        except Exception:
            try:
                os.close(fd)
            except OSError:
                pass
            try:
                os.unlink(name)
            except OSError:
                pass
            raise
        self.name = name
        self.delete = bool(delete)
        self.mode = mode
        self._closed = False

    # Context-manager protocol -----------------------------------------
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    # Iterator protocol ------------------------------------------------
    def __iter__(self):
        return iter(self._file)

    def __next__(self):
        return next(self._file)

    # Lifecycle --------------------------------------------------------
    def close(self):
        if self._closed:
            return
        self._closed = True
        try:
            self._file.close()
        finally:
            if self.delete:
                try:
                    os.unlink(self.name)
                except OSError:
                    pass

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass

    # Common file API passthroughs (explicit for clarity) -------------
    def write(self, data):
        return self._file.write(data)

    def read(self, *args, **kwargs):
        return self._file.read(*args, **kwargs)

    def readline(self, *args, **kwargs):
        return self._file.readline(*args, **kwargs)

    def readlines(self, *args, **kwargs):
        return self._file.readlines(*args, **kwargs)

    def seek(self, *args, **kwargs):
        return self._file.seek(*args, **kwargs)

    def tell(self):
        return self._file.tell()

    def flush(self):
        return self._file.flush()

    def fileno(self):
        return self._file.fileno()

    def truncate(self, *args, **kwargs):
        return self._file.truncate(*args, **kwargs)

    def writable(self):
        return self._file.writable()

    def readable(self):
        return self._file.readable()

    def seekable(self):
        return self._file.seekable()

    @property
    def closed(self):
        return self._closed or self._file.closed

    # Catch-all for anything else
    def __getattr__(self, item):
        # __getattr__ only fires for missing attributes.
        return getattr(self._file, item)


def NamedTemporaryFile(mode="w+b", buffering=-1, encoding=None, newline=None,
                       suffix=None, prefix=None, dir=None, delete=True):
    return _NamedTemporaryFile(mode=mode, buffering=buffering,
                               encoding=encoding, newline=newline,
                               suffix=suffix, prefix=prefix, dir=dir,
                               delete=delete)


# ---------------------------------------------------------------------------
# Required invariant entry points
# ---------------------------------------------------------------------------

def tempfile2_mkstemp():
    """Verify mkstemp creates a unique, writable temp file and clean up."""
    fd, path = mkstemp(prefix="t2_")
    try:
        if not isinstance(fd, int) or fd < 0:
            return False
        if not os.path.exists(path):
            return False
        payload = b"theseus-tempfile-cr"
        written = os.write(fd, payload)
        if written != len(payload):
            return False
        os.lseek(fd, 0, 0)
        # Read back via a fresh descriptor to confirm content landed on disk.
        with open(path, "rb") as fh:
            data = fh.read()
        if data != payload:
            return False
        return True
    finally:
        try:
            os.close(fd)
        except OSError:
            pass
        try:
            os.unlink(path)
        except OSError:
            pass


def tempfile2_mkdtemp():
    """Verify mkdtemp creates a usable, isolated temp directory."""
    path = mkdtemp(prefix="t2d_")
    try:
        if not os.path.isdir(path):
            return False
        # Confirm we can put a file inside the directory.
        inner = os.path.join(path, "probe.txt")
        with open(inner, "wb") as fh:
            fh.write(b"ok")
        if not os.path.isfile(inner):
            return False
        os.unlink(inner)
        return True
    finally:
        try:
            # Best-effort recursive cleanup of any stragglers.
            for entry in os.listdir(path):
                full = os.path.join(path, entry)
                try:
                    if os.path.isdir(full) and not os.path.islink(full):
                        os.rmdir(full)
                    else:
                        os.unlink(full)
                except OSError:
                    pass
            os.rmdir(path)
        except OSError:
            pass


def tempfile2_named():
    """Verify NamedTemporaryFile round-trips content and auto-deletes."""
    with NamedTemporaryFile(prefix="t2n_", delete=True) as fh:
        name = fh.name
        if not os.path.exists(name):
            return False
        fh.write(b"named-temp-data")
        fh.flush()
        fh.seek(0)
        if fh.read() != b"named-temp-data":
            return False
    # After the context exits the file should be gone.
    if os.path.exists(name):
        try:
            os.unlink(name)
        except OSError:
            pass
        return False
    return True


__all__ = [
    "mkstemp",
    "mkdtemp",
    "NamedTemporaryFile",
    "gettempdir",
    "gettempprefix",
    "tempfile2_mkstemp",
    "tempfile2_mkdtemp",
    "tempfile2_named",
]