"""
theseus_fileinput_cr — Clean-room reimplementation of the standard
``fileinput`` module.

Implements iteration over lines from one or more files (or stdin) with
state tracking for the current filename, cumulative line number, and
per-file line number. No import of the original ``fileinput`` module.
"""

import os as _os
import sys as _sys


# ---------------------------------------------------------------------------
# FileInput class
# ---------------------------------------------------------------------------

class FileInput:
    """Iterator over lines from multiple input streams."""

    def __init__(self, files=None, inplace=False, backup='', mode='r',
                 openhook=None, encoding=None, errors=None):
        # Normalise the ``files`` argument.
        if isinstance(files, str):
            files = (files,)
        elif isinstance(files, _os.PathLike):
            files = (_os.fspath(files),)
        elif files is None:
            files = tuple(_sys.argv[1:]) or ('-',)
        else:
            files = tuple(files)

        if mode not in ('r', 'rU', 'U', 'rb'):
            raise ValueError("FileInput opening mode must be one of "
                             "'r', 'rU', 'U' and 'rb'")

        if inplace and openhook:
            raise ValueError("FileInput cannot use an opening hook in "
                             "inplace mode")

        if openhook is not None and not callable(openhook):
            raise ValueError("FileInput openhook must be callable")

        self._files = files
        self._inplace = inplace
        self._backup = backup
        self._mode = mode
        self._openhook = openhook
        self._encoding = encoding
        self._errors = errors

        self._file = None
        self._filename = None
        self._lineno = 0
        self._filelineno = 0
        self._isfirstline = False
        self._isstdin = False
        self._backupfilename = None
        self._output = None
        self._savestdout = None
        self._fileindex = 0
        self._startedline = False

    # ----- context manager / iterator protocol ----------------------------

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
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
            # Current file exhausted; advance to the next one.
            if not self._advance():
                raise StopIteration

    def __getitem__(self, i):
        # Legacy indexing: only forward sequential access is supported.
        if i != self._lineno:
            raise RuntimeError("accessing lines out of order")
        try:
            return self.__next__()
        except StopIteration:
            raise IndexError("end of input reached")

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass

    # ----- public state accessors -----------------------------------------

    def filename(self):
        return self._filename

    def lineno(self):
        return self._lineno

    def filelineno(self):
        return self._filelineno

    def fileno(self):
        if self._file is not None:
            try:
                return self._file.fileno()
            except Exception:
                return -1
        return -1

    def isfirstline(self):
        return self._isfirstline

    def isstdin(self):
        return self._isstdin

    def readline(self):
        try:
            return self.__next__()
        except StopIteration:
            return ''

    def nextfile(self):
        """Close the current file early so the next iteration moves on."""
        savedfile = self._file
        self._file = None
        try:
            if savedfile is not None and not self._isstdin:
                savedfile.close()
        except Exception:
            pass
        self._closeoutput()

    def close(self):
        try:
            self.nextfile()
        finally:
            self._files = ()

    # ----- internal helpers -----------------------------------------------

    def _readline(self):
        if self._file is None:
            return None
        return self._file.readline() or None

    def _closeoutput(self):
        if self._output is not None:
            try:
                self._output.close()
            except Exception:
                pass
            self._output = None
            if self._savestdout is not None:
                _sys.stdout = self._savestdout
                self._savestdout = None
            if self._backupfilename is not None and not self._backup:
                try:
                    _os.unlink(self._backupfilename)
                except OSError:
                    pass
            self._backupfilename = None

    def _advance(self):
        # Tear down the file we just finished with.
        if self._file is not None:
            if not self._isstdin:
                try:
                    self._file.close()
                except Exception:
                    pass
            self._file = None
        self._closeoutput()

        if self._fileindex >= len(self._files):
            self._filename = None
            self._isstdin = False
            return False

        self._filename = self._files[self._fileindex]
        self._fileindex += 1
        self._filelineno = 0
        self._isfirstline = False

        if self._filename == '-':
            self._isstdin = True
            self._file = (_sys.stdin.buffer
                          if 'b' in self._mode and hasattr(_sys.stdin, 'buffer')
                          else _sys.stdin)
            return True

        self._isstdin = False

        if self._inplace:
            backupext = self._backup or '.bak'
            self._backupfilename = self._filename + backupext
            try:
                _os.unlink(self._backupfilename)
            except OSError:
                pass
            _os.rename(self._filename, self._backupfilename)
            self._file = self._open(self._backupfilename)
            try:
                perm = _os.fstat(self._file.fileno()).st_mode
            except OSError:
                self._output = open(self._filename, 'w',
                                    encoding=self._encoding,
                                    errors=self._errors)
            else:
                fd = _os.open(self._filename,
                              _os.O_CREAT | _os.O_WRONLY | _os.O_TRUNC,
                              perm)
                self._output = _os.fdopen(fd, 'w',
                                          encoding=self._encoding,
                                          errors=self._errors)
            self._savestdout = _sys.stdout
            _sys.stdout = self._output
        else:
            self._file = self._open(self._filename)
        return True

    def _open(self, path):
        if self._openhook is not None:
            return self._openhook(path, self._mode)
        if 'b' in self._mode:
            return open(path, self._mode)
        return open(path, self._mode,
                    encoding=self._encoding, errors=self._errors)


# ---------------------------------------------------------------------------
# Module-level state and convenience functions
# ---------------------------------------------------------------------------

_state = None


def input(files=None, inplace=False, backup='', mode='r',
          openhook=None, encoding=None, errors=None):
    """Return a shared :class:`FileInput` iterator for the given files."""
    global _state
    if _state is not None and _state._file is not None:
        raise RuntimeError("input() already active")
    _state = FileInput(files=files, inplace=inplace, backup=backup,
                       mode=mode, openhook=openhook,
                       encoding=encoding, errors=errors)
    return _state


def close():
    global _state
    state = _state
    _state = None
    if state is not None:
        state.close()


def nextfile():
    if _state is None:
        raise RuntimeError("no active input()")
    _state.nextfile()


def filename():
    if _state is None:
        raise RuntimeError("no active input()")
    return _state.filename()


def lineno():
    if _state is None:
        raise RuntimeError("no active input()")
    return _state.lineno()


def filelineno():
    if _state is None:
        raise RuntimeError("no active input()")
    return _state.filelineno()


def fileno():
    if _state is None:
        raise RuntimeError("no active input()")
    return _state.fileno()


def isfirstline():
    if _state is None:
        raise RuntimeError("no active input()")
    return _state.isfirstline()


def isstdin():
    if _state is None:
        raise RuntimeError("no active input()")
    return _state.isstdin()


# ---------------------------------------------------------------------------
# Open-hook helpers
# ---------------------------------------------------------------------------

def hook_compressed(filename, mode, *, encoding=None, errors=None):
    ext = _os.path.splitext(filename)[1]
    if ext == '.gz':
        import gzip
        return gzip.open(filename, mode, encoding=encoding, errors=errors)
    if ext == '.bz2':
        import bz2
        return bz2.open(filename, mode, encoding=encoding, errors=errors)
    return open(filename, mode, encoding=encoding, errors=errors)


def hook_encoded(encoding, errors=None):
    def openhook(path, mode):
        return open(path, mode, encoding=encoding, errors=errors)
    return openhook


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def _write_temp(data):
    """Create a temporary file containing ``data`` and return its path."""
    import tempfile
    fd, path = tempfile.mkstemp(prefix='theseus_fileinput_cr_')
    try:
        if isinstance(data, str):
            data = data.encode('utf-8')
        _os.write(fd, data)
    finally:
        _os.close(fd)
    return path


def fileinput2_lines():
    """A :class:`FileInput` iterator yields every line from its files."""
    path1 = _write_temp('one\ntwo\n')
    path2 = _write_temp('three\nfour\nfive\n')
    try:
        with FileInput([path1, path2]) as fi:
            collected = list(fi)
    finally:
        for p in (path1, path2):
            try:
                _os.unlink(p)
            except OSError:
                pass
    expected = ['one\n', 'two\n', 'three\n', 'four\n', 'five\n']
    return collected == expected


def fileinput2_lineno():
    """``lineno()`` reflects cumulative position across all input files."""
    path1 = _write_temp('a\nb\n')
    path2 = _write_temp('c\nd\ne\n')
    try:
        fi = FileInput([path1, path2])
        try:
            seen = []
            for _line in fi:
                seen.append(fi.lineno())
            final = fi.lineno()
        finally:
            fi.close()
    finally:
        for p in (path1, path2):
            try:
                _os.unlink(p)
            except OSError:
                pass
    return seen == [1, 2, 3, 4, 5] and final == 5


def fileinput2_filename():
    """``filename()`` tracks which input file is currently being read."""
    path1 = _write_temp('alpha\nbeta\n')
    path2 = _write_temp('gamma\n')
    try:
        fi = FileInput([path1, path2])
        try:
            first_line = next(fi)
            name_during_first = fi.filename()
            # Consume the rest of the first file.
            next(fi)
            # Now move into the second file.
            second_first = next(fi)
            name_during_second = fi.filename()
        finally:
            fi.close()
    finally:
        for p in (path1, path2):
            try:
                _os.unlink(p)
            except OSError:
                pass
    return (first_line == 'alpha\n'
            and name_during_first == path1
            and second_first == 'gamma\n'
            and name_during_second == path2)


__all__ = [
    'FileInput',
    'input',
    'close',
    'nextfile',
    'filename',
    'lineno',
    'filelineno',
    'fileno',
    'isfirstline',
    'isstdin',
    'hook_compressed',
    'hook_encoded',
    'fileinput2_lines',
    'fileinput2_lineno',
    'fileinput2_filename',
]