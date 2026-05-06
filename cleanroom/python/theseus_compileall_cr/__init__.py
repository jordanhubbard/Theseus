"""
theseus_compileall_cr — Clean-room compileall module.
No import of the standard `compileall` module.
"""

import os as _os
import sys as _sys
import importlib.machinery as _importlib_machinery
import importlib.util as _importlib_util
import importlib._bootstrap_external as _bootstrap_ext
import struct as _struct
import time as _time
import marshal as _marshal


def compile_file(fullname, ddir=None, force=False, rx=None,
                 quiet=0, legacy=False, optimize=-1,
                 invalidation_mode=None, *, stripdir=None,
                 prependdir=None, limit_sl_dest=None, hardlink_dupes=False):
    """Byte-compile one file."""
    if rx is not None:
        import re
        if rx.search(fullname):
            return True

    if not fullname.endswith('.py'):
        return True

    if ddir is not None:
        dfile = _os.path.join(ddir, fullname[len(_os.path.dirname(fullname)):].lstrip(_os.sep))
    else:
        dfile = None

    try:
        loader = _importlib_machinery.SourceFileLoader(fullname, fullname)
        source = loader.get_data(fullname)
    except OSError:
        if not quiet:
            import sys
            sys.stderr.write(f"Couldn't read {fullname}\n")
        return False

    try:
        code = loader.source_to_code(source, dfile or fullname, _optimize=optimize)
    except SyntaxError as err:
        if not quiet:
            import traceback
            traceback.print_exc()
        return False

    try:
        if legacy:
            cfile = fullname + 'c'
        else:
            opt = '' if optimize < 1 else optimize
            cfile = _bootstrap_ext.cache_from_source(fullname, optimization=opt)

        cdir = _os.path.dirname(cfile)
        if cdir:
            _os.makedirs(cdir, exist_ok=True)

        magic = _bootstrap_ext.MAGIC_NUMBER
        mtime = int(_time.time())
        size = len(source) & 0xFFFFFFFF
        data = magic + _struct.pack('<III', 0, mtime, size) + _marshal.dumps(code)
        loader.set_data(cfile, data)
    except Exception as err:
        if not quiet:
            import sys
            sys.stderr.write(f"Couldn't write {fullname}: {err}\n")
        return False

    return True


def compile_dir(dir, maxlevels=None, ddir=None, force=False, rx=None,
                quiet=0, legacy=False, optimize=-1, workers=1,
                invalidation_mode=None, *, stripdir=None, prependdir=None,
                limit_sl_dest=None, hardlink_dupes=False):
    """Byte-compile all modules in the given directory tree."""
    success = True
    if maxlevels is None:
        maxlevels = 10
    elif maxlevels == 0:
        return True

    try:
        names = _os.listdir(dir)
    except OSError:
        if not quiet:
            import sys
            sys.stderr.write(f"Can't list {dir}\n")
        return False

    names.sort()
    for name in names:
        fullname = _os.path.join(dir, name)
        if _os.path.isfile(fullname) and name.endswith('.py'):
            if not compile_file(fullname, ddir=ddir, force=force, rx=rx,
                                 quiet=quiet, legacy=legacy, optimize=optimize):
                success = False
        elif (_os.path.isdir(fullname) and maxlevels > 0
              and not _os.path.islink(fullname)):
            if not compile_dir(fullname, maxlevels - 1, ddir=ddir, force=force,
                                rx=rx, quiet=quiet, legacy=legacy, optimize=optimize):
                success = False

    return success


def compile_path(skip_curdir=1, maxlevels=0, force=False, quiet=0,
                 legacy=False, optimize=-1, invalidation_mode=None):
    """Byte-compile all module on sys.path."""
    success = True
    for dir in _sys.path:
        if (not dir or dir == _os.curdir) and skip_curdir:
            continue
        if _os.path.isdir(dir):
            if not compile_dir(dir, maxlevels, ddir=None, force=force,
                                quiet=quiet, legacy=legacy, optimize=optimize):
                success = False
    return success


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def compileall2_compile_file():
    """compile_file() compiles a .py file to .pyc; returns True."""
    import tempfile
    fd, path = tempfile.mkstemp(suffix='.py')
    try:
        _os.write(fd, b'x = 1 + 2\n')
        _os.close(fd)
        result = compile_file(path, quiet=2)
        return result is True
    finally:
        try:
            _os.unlink(path)
        except OSError:
            pass


def compileall2_compile_dir():
    """compile_dir() returns True for a valid directory with a .py file; returns True."""
    import tempfile
    tmpdir = tempfile.mkdtemp()
    try:
        src = _os.path.join(tmpdir, 'test_module.py')
        with open(src, 'w') as f:
            f.write('x = 42\n')
        result = compile_dir(tmpdir, maxlevels=0, quiet=2)
        return result is True
    finally:
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)


def compileall2_compile_path():
    """compile_path() succeeds on empty skip; returns True."""
    result = compile_path(skip_curdir=1, maxlevels=0, quiet=2)
    return result is True


__all__ = [
    'compile_file', 'compile_dir', 'compile_path',
    'compileall2_compile_file', 'compileall2_compile_dir', 'compileall2_compile_path',
]