"""
theseus_fileinput_cr — Clean-room fileinput module.
No import of the standard `fileinput` module.
"""

import os as _os
import sys as _sys

_state = None

DEFAULT_BUFSIZE = 8*1024


class FileInput:
    """Class that emulates fileinput.input() as an iterator."""

    def __init__(self, files=None, inplace=False, backup='', mode='r',
                 openhook=None, encoding=None, errors=None):
        if isinstance(files, str):
            files = (files,)
        elif isinstance(files, _os.PathLike):
            files = (files,)
        elif files is None:
            files = _sys.argv[1:] or ('-',)
        else:
            files = tuple(files)

        self._files = files
        self._inplace = inplace
        self._backup = backup
        self._mode = mode
        self._openhook = openhook
        self._encoding = encoding
        self._errors = errors

        self._file = None
        self._filename = None
        self._fileno = -1
        self._filelineno = 0
        self._lineno = 0
        self._isfirstline = True
        self._isstdin = False
        self._backupfilename = None
        self._stdout = None
        self._output = None
        self._fileindex = 0
        self._savestdout = None

    def __del__(self):
        self.close()

    def close(self):
        if self._file:
            try:
                self._file.close()
            except Exception:
                pass
            self._file = None
        if self._savestdout:
            _sys.stdout = self._savestdout
            self._savestdout = None
        if self._output:
            try:
                self._output.close()
            except Exception:
                pass
            self._output = None

    def __enter__(self):
        return self

    def __exit__(self, type, value, tb):
        self.close()

    def __iter__(self):
        return self

    def __next__(self):
        while True:
            line = self._readline()
            if line:
                self._lineno += 1
                self._filelineno += 1
                self._isfirstline = (self._filelineno == 1)
                return line
            if not self._nextfile():
                raise StopIteration

    def _readline(self):
        if self._file is None:
            if not self._nextfile():
                return None
        line = self._file.readline()
        return line if line else None

    def _nextfile(self):
        if self._file is not None:
            if self._inplace and self._savestdout:
                _sys.stdout = self._savestdout
                self._savestdout = None
            if self._output is not None:
                self._output.close()
                self._output = None
                if self._backup:
                    _os.rename(self._filename, self._backupfilename)
                else:
                    try:
                        _os.unlink(self._backupfilename)
                    except OSError:
                        pass
            if self._isstdin:
                pass
            else:
                self._file.close()
            self._file = None

        if self._fileindex >= len(self._files):
            return False

        self._filename = self._files[self._fileindex]
        self._fileindex += 1
        self._filelineno = 0
        self._isfirstline = True

        if self._filename == '-':
            self._isstdin = True
            self._file = _sys.stdin
            self._fileno = _sys.stdin.fileno() if hasattr(_sys.stdin, 'fileno') else -1
        else:
            self._isstdin = False
            if self._inplace:
                self._backupfilename = self._filename + (self._backup or '.bak')
                _os.rename(self._filename, self._backupfilename)
                if self._openhook:
                    self._file = self._openhook(self._backupfilename, self._mode)
                else:
                    self._file = open(self._backupfilename, self._mode,
                                      encoding=self._encoding, errors=self._errors)
                self._output = open(self._filename, 'w',
                                    encoding=self._encoding, errors=self._errors)
                self._savestdout = _sys.stdout
                _sys.stdout = self._output
            else:
                if self._openhook:
                    self._file = self._openhook(self._filename, self._mode)
                else:
                    if self._mode in ('r', 'rb'):
                        self._file = open(self._filename, self._mode,
                                          encoding=self._encoding, errors=self._errors)
                    else:
                        self._file = open(self._filename, self._mode,
                                          encoding=self._encoding, errors=self._errors)
            self._fileno = self._file.fileno()
        return True

    def readline(self):
        try:
            line = next(self)
        except StopIteration:
            return ''
        return line

    def filename(self):
        return self._filename

    def fileno(self):
        if self._file:
            try:
                return self._file.fileno()
            except Exception:
                return -1
        return -1

    def lineno(self):
        return self._lineno

    def filelineno(self):
        return self._filelineno

    def isfirstline(self):
        return self._isfirstline

    def isstdin(self):
        return self._isstdin

    def nextfile(self):
        self._fileindex = self._fileindex  # advance on next read
        if self._file and not self._isstdin:
            self._file.close()
            self._file = None

    def __getitem__(self, i):
        if i != self._lineno:
            raise RuntimeError("accessing lines out of order")
        try:
            return next(self)
        except StopIteration:
            raise IndexError("end of input reached")


def input(files=None, inplace=False, backup='', mode='r',
          openhook=None, encoding=None, errors=None):
    """Return a FileInput object as a context manager."""
    global _state
    if _state and _state._file:
        raise RuntimeError("input() already active")
    _state = FileInput(files=files, inplace=inplace, backup=backup,
                       mode=mode, openhook=openhook, encoding=encoding, errors=errors)
    return _state


def filename():
    return _state.filename() if _state else None


def fileno():
    return _state.fileno() if _state else -1


def lineno():
    return _state.lineno() if _state else 0


def filelineno():
    return _state.filelineno() if _state else 0


def isfirstline():
    return _state.isfirstline() if _state else True


def isstdin():
    return _state.isstdin() if _state else False


def nextfile():
    if _state:
        _state.nextfile()


def close():
    global _state
    if _state:
        _state.close()
        _state = None


def hook_compressed(filename, mode):
    """Open compressed files transparently."""
    ext = _os.path.splitext(filename)[1]
    if ext == '.gz':
        import gzip
        return gzip.open(filename, mode)
    elif ext == '.bz2':
        import bz2
        return bz2.open(filename, mode)
    else:
        return open(filename, mode)


def hook_encoded(encoding, errors=None):
    """Return a hook that opens files with the given encoding."""
    def openhook(filename, mode):
        return open(filename, mode, encoding=encoding, errors=errors)
    return openhook


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def fileinput2_lines():
    """FileInput iterates lines from a temp file; returns True."""
    import tempfile
    fd, path = tempfile.mkstemp()
    try:
        _os.write(fd, b'line1\nline2\n')
        _os.close(fd)
        with FileInput([path]) as fi:
            lines = list(fi)
        return len(lines) == 2
    finally:
        try:
            _os.unlink(path)
        except OSError:
            pass


def fileinput2_lineno():
    """lineno() returns the cumulative line number; returns True."""
    import tempfile
    fd, path = tempfile.mkstemp()
    try:
        _os.write(fd, b'a\nb\nc\n')
        _os.close(fd)
        fi = FileInput([path])
        lines = list(fi)
        result = fi.lineno()
        fi.close()
        return result == 3
    finally:
        try:
            _os.unlink(path)
        except OSError:
            pass


def fileinput2_filename():
    """filename() returns the current file name; returns True."""
    import tempfile
    fd, path = tempfile.mkstemp()
    try:
        _os.write(fd, b'hello\n')
        _os.close(fd)
        fi = FileInput([path])
        next(fi)
        fname = fi.filename()
        fi.close()
        return fname == path
    finally:
        try:
            _os.unlink(path)
        except OSError:
            pass


__all__ = [
    'input', 'filename', 'fileno', 'lineno', 'filelineno',
    'isfirstline', 'isstdin', 'nextfile', 'close',
    'FileInput', 'hook_compressed', 'hook_encoded',
    'fileinput2_lines', 'fileinput2_lineno', 'fileinput2_filename',
]
