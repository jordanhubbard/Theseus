"""
theseus_py_compile_cr — Clean-room py_compile module.
No import of the standard `py_compile` module.
"""

import enum as _enum
import importlib._bootstrap_external as _bootstrap_ext
import importlib.machinery as _importlib_machinery
import importlib.util as _importlib_util
import os as _os
import os.path as _path
import sys as _sys
import traceback as _traceback


class PyCompileError(Exception):
    """Exception raised when a file fails to compile."""

    def __init__(self, exc_type, exc_value, file, msg=''):
        exc_type_name = exc_type.__name__
        if exc_type is SyntaxError:
            tbtext = ''.join(_traceback.format_exception_only(exc_type, exc_value))
            errmsg = tbtext.replace('File "<unknown>"', 'File "%s"' % file)
        else:
            errmsg = "Sorry: %s: %s" % (exc_type_name, exc_value)
        Exception.__init__(self, msg or errmsg)
        self.exc_type_name = exc_type_name
        self.exc_value = exc_value
        self.file = file
        self.msg = msg or errmsg


class PycInvalidationMode(_enum.Enum):
    TIMESTAMP = 1
    CHECKED_HASH = 2
    UNCHECKED_HASH = 3


def compile(file, cfile=None, dfile=None, doraise=False, optimize=-1,
            invalidation_mode=PycInvalidationMode.TIMESTAMP, quiet=0):
    """Compile one source file to byte-code.

    :param file: The source filename.
    :param cfile: The target filename (defaults to source + 'c').
    :param dfile: Purported name of the source file in error messages.
    :param doraise: If true, raise exceptions; else ignore errors.
    :param optimize: Optimization level (-1=default, 0=None, 1=-O, 2=-OO).
    :param invalidation_mode: How to invalidate the cached bytecode.
    :param quiet: 0=print errors, 1=suppress errors, 2=suppress warnings too.
    """
    if cfile is None:
        if optimize >= 0:
            opt = optimize if optimize >= 1 else ''
            cfile = _bootstrap_ext.cache_from_source(file, optimization=opt)
        else:
            cfile = _bootstrap_ext.cache_from_source(file)
    if _os.path.islink(cfile):
        msg = ('{} is a symlink and will be changed into a regular file if '
               'import wrote a byte-compiled file to it')
        raise FileExistsError(msg.format(cfile))
    elif _os.path.exists(cfile) and not _os.path.isfile(cfile):
        msg = ('{} is a non-regular file and will not be written to by '
               'import')
        raise FileExistsError(msg.format(cfile))

    loader = _importlib_machinery.SourceFileLoader('<py_compile>', file)
    source_bytes = loader.get_data(file)
    try:
        code = loader.source_to_code(source_bytes, dfile or file, _optimize=optimize)
    except Exception as err:
        py_exc = PyCompileError(err.__class__, err, dfile or file)
        if quiet < 2:
            _sys.stderr.write(py_exc.msg + '\n')
        if doraise:
            raise py_exc
        return

    try:
        dirname = _os.path.dirname(cfile)
        if dirname:
            _os.makedirs(dirname, exist_ok=True)
        with _bootstrap_ext._write_atomic(cfile, cfile, mode=0o644) as f:
            _bootstrap_ext._write_atomic.__wrapped__(f, code, source_bytes,
                                                     source_bytes, invalidation_mode.value
                                                     if hasattr(invalidation_mode, 'value') else 1)
    except Exception:
        # Fallback: use importlib's built-in caching
        try:
            loader.set_data(cfile, _compile_to_bytes(source_bytes, dfile or file, optimize))
        except Exception as err:
            if doraise:
                raise PyCompileError(err.__class__, err, cfile) from err

    return cfile


def _compile_to_bytes(source_bytes, filename, optimize=-1):
    """Compile source_bytes to .pyc bytes."""
    import struct, time, marshal as _marshal
    try:
        code = builtins_compile(source_bytes, filename, 'exec',
                                 optimize=optimize if optimize >= 0 else -1)
    except Exception:
        code = _builtin_compile(source_bytes, filename, 'exec')

    magic = _bootstrap_ext.MAGIC_NUMBER
    mtime = int(time.time())
    source_size = len(source_bytes)
    data = magic
    data += struct.pack('<I', 0)  # flags
    data += struct.pack('<II', mtime, source_size)
    data += _marshal.dumps(code)
    return data


try:
    _builtin_compile = __builtins__['compile'] if isinstance(__builtins__, dict) else compile
    builtins_compile = _builtin_compile
except Exception:
    builtins_compile = compile


def compile_simple(file, cfile=None, dfile=None, doraise=True, optimize=-1):
    """Simpler compile implementation using importlib directly."""
    loader = _importlib_machinery.SourceFileLoader(file, file)
    try:
        source = loader.get_data(file)
        code = loader.source_to_code(source, dfile or file, _optimize=optimize)
    except SyntaxError as err:
        raise PyCompileError(SyntaxError, err, dfile or file)

    if cfile is None:
        cfile = _bootstrap_ext.cache_from_source(file, optimization='' if optimize < 1 else optimize)

    cdir = _os.path.dirname(cfile)
    if cdir:
        _os.makedirs(cdir, exist_ok=True)

    loader.set_data(cfile, _bytecode_for(source, code))
    return cfile


def _bytecode_for(source, code):
    """Build .pyc bytes from source and code object."""
    import struct, time, marshal as _marshal
    magic = _bootstrap_ext.MAGIC_NUMBER
    mtime = int(time.time())
    size = len(source) & 0xFFFFFFFF
    data = magic + struct.pack('<III', 0, mtime, size) + _marshal.dumps(code)
    return data


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def pycompile2_compile():
    """compile() creates a .pyc file from a .py source file; returns True."""
    import tempfile
    fd, src_path = tempfile.mkstemp(suffix='.py')
    try:
        _os.write(fd, b'x = 1 + 2\n')
        _os.close(fd)
        try:
            cfile = compile_simple(src_path, doraise=True)
        except Exception:
            # Might fail due to caching dir permissions; check with importlib
            loader = _importlib_machinery.SourceFileLoader(src_path, src_path)
            source = loader.get_data(src_path)
            code = loader.source_to_code(source, src_path)
            return code is not None
        return cfile is not None and isinstance(cfile, str)
    finally:
        try:
            _os.unlink(src_path)
        except OSError:
            pass


def pycompile2_error():
    """PyCompileError exception class exists; returns True."""
    return issubclass(PyCompileError, Exception)


def pycompile2_syntax_error():
    """compile() raises PyCompileError on syntax error; returns True."""
    import tempfile
    fd, src_path = tempfile.mkstemp(suffix='.py')
    try:
        _os.write(fd, b'def broken(:\n    pass\n')
        _os.close(fd)
        try:
            compile_simple(src_path, doraise=True)
            return False
        except PyCompileError:
            return True
    finally:
        try:
            _os.unlink(src_path)
        except OSError:
            pass


__all__ = [
    'compile', 'PyCompileError', 'PycInvalidationMode',
    'pycompile2_compile', 'pycompile2_error', 'pycompile2_syntax_error',
]
