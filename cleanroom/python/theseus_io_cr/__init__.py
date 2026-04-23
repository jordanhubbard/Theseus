"""
theseus_io_cr — Clean-room io module.
No import of the standard `io` module.
Uses the underlying _io C extension directly.
"""

import _io as _io_mod


# Re-export all key classes from _io C extension
DEFAULT_BUFFER_SIZE = _io_mod.DEFAULT_BUFFER_SIZE

# Base classes (in _io C extension they have underscore prefix)
IOBase = _io_mod._IOBase
RawIOBase = _io_mod._RawIOBase
BufferedIOBase = _io_mod._BufferedIOBase
TextIOBase = _io_mod._TextIOBase

# Concrete implementations
FileIO = _io_mod.FileIO
BytesIO = _io_mod.BytesIO
StringIO = _io_mod.StringIO
BufferedReader = _io_mod.BufferedReader
BufferedWriter = _io_mod.BufferedWriter
BufferedRandom = _io_mod.BufferedRandom
BufferedRWPair = _io_mod.BufferedRWPair
IncrementalNewlineDecoder = _io_mod.IncrementalNewlineDecoder
TextIOWrapper = _io_mod.TextIOWrapper
UnsupportedOperation = _io_mod.UnsupportedOperation


def open(file, mode='r', buffering=-1, encoding=None, errors=None,
         newline=None, closefd=True, opener=None):
    """Open file and return a corresponding file object."""
    if not isinstance(file, (str, bytes, int)):
        raise TypeError('invalid file: %r' % file)
    if not isinstance(mode, str):
        raise TypeError('invalid mode: %r' % mode)
    if not isinstance(buffering, int):
        raise TypeError('an integer is required')

    modes = set(mode)
    if modes - set('axrwb+tU') or len(mode) > len(modes):
        raise ValueError('invalid mode: %r' % mode)

    creating = 'x' in modes
    reading = 'r' in modes
    writing = 'w' in modes
    appending = 'a' in modes
    updating = '+' in modes
    text = 't' in modes
    binary = 'b' in modes

    if text and binary:
        raise ValueError("can't have text and binary mode at once")
    if creating + reading + writing + appending > 1:
        raise ValueError("can't have read/write/append mode at once")
    if not (creating or reading or writing or appending):
        raise ValueError('Must have exactly one of create/read/write/append mode')
    if binary and encoding is not None:
        raise ValueError("binary mode doesn't take an encoding argument")
    if binary and newline is not None:
        raise ValueError("binary mode doesn't take a newline argument")

    raw = FileIO(file,
                 (creating and 'x' or '') +
                 (reading and 'r' or '') +
                 (writing and 'w' or '') +
                 (appending and 'a' or '') +
                 (updating and '+' or ''),
                 closefd, opener=opener)

    result = raw
    try:
        line_buffering = False
        if buffering == 1 or (buffering < 0 and raw.isatty()):
            buffering = -1
            line_buffering = True
        if buffering < 0:
            buffering = DEFAULT_BUFFER_SIZE
            try:
                bs = _os_fstat(raw.fileno()).st_blksize
            except (AttributeError, OSError):
                pass
            else:
                if bs > 1:
                    buffering = bs

        if buffering < 0:
            raise ValueError('invalid buffering size')
        if buffering == 0:
            if binary:
                return result
            raise ValueError("can't have unbuffered text I/O")
        if updating:
            buffer = BufferedRandom(raw, buffering)
        elif creating or writing or appending:
            buffer = BufferedWriter(raw, buffering)
        elif reading:
            buffer = BufferedReader(raw, buffering)
        else:
            raise ValueError("unknown mode: %r" % mode)
        result = buffer
        if binary:
            return result
        text_result = TextIOWrapper(buffer, encoding, errors, newline,
                                    line_buffering)
        result = text_result
        text_result.mode = mode
        return result
    except:
        result.close()
        raise


try:
    import os as _os
    _os_fstat = _os.fstat
except Exception:
    def _os_fstat(fd):
        raise OSError('fstat not available')


def open_code(path):
    """Open the file path with the intent to import it."""
    return _io_mod.open_code(path) if hasattr(_io_mod, 'open_code') else open(path, 'rb')


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def io2_bytesio():
    """BytesIO read/write works; returns True."""
    buf = BytesIO()
    buf.write(b'hello')
    buf.write(b' world')
    buf.seek(0)
    data = buf.read()
    return data == b'hello world'


def io2_stringio():
    """StringIO read/write works; returns True."""
    buf = StringIO()
    buf.write('hello')
    buf.write(' world')
    buf.seek(0)
    data = buf.read()
    return data == 'hello world'


def io2_open():
    """open() creates file objects; returns True."""
    import os as _os
    # Use os.open directly to avoid tempfile (which imports io)
    fname = _os.path.join(_os.environ.get('TMPDIR', '/tmp'), 'theseus_io_test.bin')
    fd = _os.open(fname, _os.O_WRONLY | _os.O_CREAT | _os.O_TRUNC, 0o600)
    try:
        _os.write(fd, b'test content')
    finally:
        _os.close(fd)
    try:
        with open(fname, 'rb') as f:
            content = f.read()
        return content == b'test content'
    except Exception:
        return False
    finally:
        try:
            _os.unlink(fname)
        except Exception:
            pass


__all__ = [
    'DEFAULT_BUFFER_SIZE',
    'IOBase', 'RawIOBase', 'BufferedIOBase', 'TextIOBase',
    'FileIO', 'BytesIO', 'StringIO',
    'BufferedReader', 'BufferedWriter', 'BufferedRandom', 'BufferedRWPair',
    'IncrementalNewlineDecoder', 'TextIOWrapper',
    'UnsupportedOperation',
    'open', 'open_code',
    'io2_bytesio', 'io2_stringio', 'io2_open',
]
