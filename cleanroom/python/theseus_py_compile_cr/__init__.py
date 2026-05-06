"""
theseus_py_compile_cr — Clean-room py_compile module.

This module provides a function to byte-compile Python source files
to .pyc files. Implemented from scratch without importing or wrapping
the standard library's py_compile module.
"""

import enum as _enum
import errno as _errno
import importlib.machinery as _importlib_machinery
import importlib.util as _importlib_util
import marshal as _marshal
import os as _os
import struct as _struct
import sys as _sys
import tempfile as _tempfile
import traceback as _traceback


# Capture the builtin compile() before this module's `compile` shadows it.
import builtins as _builtins
_builtin_compile = _builtins.compile


__all__ = [
    'compile',
    'main',
    'PyCompileError',
    'PycInvalidationMode',
    'MAGIC_NUMBER',
    'pycompile2_compile',
    'pycompile2_error',
    'pycompile2_syntax_error',
]


MAGIC_NUMBER = _importlib_util.MAGIC_NUMBER


class PycInvalidationMode(_enum.Enum):
    """Invalidation modes for .pyc files."""
    TIMESTAMP = 1
    CHECKED_HASH = 2
    UNCHECKED_HASH = 3


def _get_default_invalidation_mode():
    """Return the default invalidation mode for the current environment."""
    if _os.environ.get('SOURCE_DATE_EPOCH'):
        return PycInvalidationMode.CHECKED_HASH
    return PycInvalidationMode.TIMESTAMP


class PyCompileError(Exception):
    """Exception raised when an error occurs while attempting to
    compile the file.
    """

    def __init__(self, exc_type, exc_value, file, msg=''):
        exc_type_name = exc_type.__name__
        if exc_type is SyntaxError:
            tbtext = ''.join(
                _traceback.format_exception_only(exc_type, exc_value)
            )
            errmsg = tbtext.replace('File "<string>"', 'File "%s"' % file)
        else:
            errmsg = "Sorry: %s: %s" % (exc_type_name, exc_value)

        Exception.__init__(self, msg or errmsg, exc_type_name, exc_value, file)

        self.exc_type_name = exc_type_name
        self.exc_value = exc_value
        self.file = file
        self.msg = msg or errmsg

    def __str__(self):
        return self.msg


def _pack_uint32(value):
    """Pack a 32-bit unsigned integer in little-endian order."""
    return _struct.pack('<I', value & 0xFFFFFFFF)


def _code_to_timestamp_pyc(code, mtime=0, source_size=0):
    """Produce the data for a timestamp-based pyc file."""
    data = bytearray(MAGIC_NUMBER)
    data.extend(_pack_uint32(0))  # flags = 0 for timestamp-based
    data.extend(_pack_uint32(int(mtime)))
    data.extend(_pack_uint32(source_size))
    data.extend(_marshal.dumps(code))
    return data


def _code_to_hash_pyc(code, source_hash, checked=True):
    """Produce the data for a hash-based pyc file."""
    data = bytearray(MAGIC_NUMBER)
    flags = 0b1 | (0b10 if checked else 0)
    data.extend(_pack_uint32(flags))
    if len(source_hash) != 8:
        raise ValueError("source_hash must be 8 bytes long")
    data.extend(source_hash)
    data.extend(_marshal.dumps(code))
    return data


def _read_source_bytes(path):
    """Read the source file as raw bytes."""
    with open(path, 'rb') as fh:
        return fh.read()


def _atomic_write(path, data, mode=0o666):
    """Write data atomically to path."""
    tmp_path = "{}.{}".format(path, _os.getpid())
    try:
        fd = _os.open(tmp_path, _os.O_EXCL | _os.O_CREAT | _os.O_WRONLY, mode)
    except OSError:
        with open(path, 'wb') as f:
            f.write(data)
        try:
            _os.chmod(path, mode)
        except OSError:
            pass
        return

    try:
        try:
            with _os.fdopen(fd, 'wb') as f:
                f.write(data)
        except BaseException:
            try:
                _os.unlink(tmp_path)
            except OSError:
                pass
            raise
        _os.replace(tmp_path, path)
    except OSError:
        try:
            _os.unlink(tmp_path)
        except OSError:
            pass
        with open(path, 'wb') as f:
            f.write(data)


def _calc_pyc_mode(source_path):
    """Determine the file mode for a .pyc based on the source file mode."""
    try:
        st = _os.stat(source_path)
        return st.st_mode | 0o200
    except OSError:
        return 0o666


def compile(file, cfile=None, dfile=None, doraise=False, optimize=-1,
            invalidation_mode=None, quiet=0):
    """Byte-compile one Python source file to Python bytecode."""
    if invalidation_mode is None:
        invalidation_mode = _get_default_invalidation_mode()

    if cfile is None:
        if optimize >= 0:
            optimization = optimize if optimize >= 1 else ''
            cfile = _importlib_util.cache_from_source(
                file, optimization=optimization
            )
        else:
            cfile = _importlib_util.cache_from_source(file)

    if _os.path.islink(cfile):
        msg = ('{} is a symlink and will be changed into a regular file if '
               'import writes a byte-compiled file to it')
        raise FileExistsError(msg.format(cfile))
    elif _os.path.exists(cfile) and not _os.path.isfile(cfile):
        msg = ('{} is a non-regular file and will be changed into a regular '
               'one if import writes a byte-compiled file to it')
        raise FileExistsError(msg.format(cfile))

    source_bytes = _read_source_bytes(file)
    display_name = dfile if dfile is not None else file

    try:
        if optimize < 0:
            code = _builtin_compile(
                source_bytes, display_name, 'exec', dont_inherit=True,
            )
        else:
            code = _builtin_compile(
                source_bytes, display_name, 'exec',
                dont_inherit=True, optimize=optimize,
            )
    except Exception as err:
        py_exc = PyCompileError(err.__class__, err, display_name)
        if quiet < 2:
            if doraise:
                raise py_exc
            else:
                _sys.stderr.write(py_exc.msg + '\n')
        return

    try:
        dirname = _os.path.dirname(cfile)
        if dirname:
            _os.makedirs(dirname)
    except FileExistsError:
        pass
    except OSError as e:
        if e.errno != _errno.EEXIST:
            raise

    if invalidation_mode == PycInvalidationMode.TIMESTAMP:
        try:
            st = _os.stat(file)
            mtime = int(st.st_mtime)
            source_size = st.st_size & 0xFFFFFFFF
        except OSError:
            mtime = 0
            source_size = 0
        bytecode = _code_to_timestamp_pyc(code, mtime, source_size)
    else:
        source_hash = _importlib_util.source_hash(source_bytes)
        bytecode = _code_to_hash_pyc(
            code,
            source_hash,
            checked=(invalidation_mode == PycInvalidationMode.CHECKED_HASH),
        )

    mode = _calc_pyc_mode(file)
    _atomic_write(cfile, bytes(bytecode), mode)

    return cfile


def main(args=None):
    """Compile several source files."""
    if args is None:
        args = _sys.argv[1:]
    if args == ['-']:
        while True:
            line = _sys.stdin.readline()
            if not line:
                break
            filename = line.rstrip('\n')
            try:
                compile(filename, doraise=True)
            except PyCompileError as error:
                _sys.stderr.write("%s\n" % error.msg)
                return 1
            except OSError as error:
                _sys.stderr.write("%s\n" % error)
                return 1
    else:
        for filename in args:
            try:
                compile(filename, doraise=True)
            except PyCompileError as error:
                _sys.stderr.write("%s\n" % error.msg)
                return 1
    return 0


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def pycompile2_compile():
    """compile() creates a .pyc file from a .py source file; returns True."""
    src_dir = _tempfile.mkdtemp(prefix='theseus_pycompile_')
    src_path = _os.path.join(src_dir, 'sample.py')
    cfile_path = _os.path.join(src_dir, 'sample.pyc')
    try:
        with open(src_path, 'wb') as fh:
            fh.write(b'x = 1 + 2\nprint(x)\n')
        result = compile(src_path, cfile=cfile_path, doraise=True)
        if result != cfile_path:
            return False
        if not _os.path.isfile(cfile_path):
            return False
        with open(cfile_path, 'rb') as fh:
            data = fh.read()
        if not data.startswith(MAGIC_NUMBER):
            return False
        code_obj = _marshal.loads(data[16:])
        if not hasattr(code_obj, 'co_code'):
            return False
        return True
    finally:
        for path in (src_path, cfile_path):
            try:
                _os.unlink(path)
            except OSError:
                pass
        try:
            _os.rmdir(src_dir)
        except OSError:
            pass


def pycompile2_error():
    """PyCompileError exception class exists and is an Exception subclass."""
    if not isinstance(PyCompileError, type):
        return False
    if not issubclass(PyCompileError, Exception):
        return False
    err = PyCompileError(ValueError, ValueError('boom'), 'somefile.py')
    if err.file != 'somefile.py':
        return False
    if err.exc_type_name != 'ValueError':
        return False
    if not str(err):
        return False
    return True


def pycompile2_syntax_error():
    """compile() raises PyCompileError on a syntax error when doraise=True."""
    src_dir = _tempfile.mkdtemp(prefix='theseus_pycompile_syn_')
    src_path = _os.path.join(src_dir, 'broken.py')
    cfile_path = _os.path.join(src_dir, 'broken.pyc')
    saved_stderr = _sys.stderr
    try:
        with open(src_path, 'wb') as fh:
            fh.write(b'def broken(:\n    pass\n')
        try:
            import io as _io
            _sys.stderr = _io.StringIO()
        except Exception:
            pass
        try:
            compile(src_path, cfile=cfile_path, doraise=True)
        except PyCompileError as exc:
            if exc.exc_type_name != 'SyntaxError':
                return False
            if exc.file != src_path:
                return False
            return True
        except SyntaxError:
            return False
        return False
    finally:
        _sys.stderr = saved_stderr
        for path in (src_path, cfile_path):
            try:
                _os.unlink(path)
            except OSError:
                pass
        try:
            _os.rmdir(src_dir)
        except OSError:
            pass


if __name__ == '__main__':
    _sys.exit(main())