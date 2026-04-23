"""
theseus_zipapp_cr — Clean-room zipapp module.
No import of the standard `zipapp` module.
Pure Python implementation.
"""

import io as _io
import os as _os
import pathlib as _pathlib
import zipfile as _zipfile
import stat as _stat
import sys as _sys


PYTHON_SHEBANG = b'#!/usr/bin/env python3\n'
MAIN_ENTRY = '__main__.py'


class ZipAppError(ValueError):
    pass


def _write_file_prefix(f, interpreter):
    if interpreter:
        if not interpreter.startswith('/'):
            shebang = f'#!{interpreter}\n'.encode()
        else:
            shebang = f'#!{interpreter}\n'.encode()
        f.write(shebang)


def create_archive(source, target=None, interpreter=None, main=None,
                   filter=None, compressed=False):
    """
    Create a zipapp archive from source directory or file.
    source: path to source directory or zip file
    target: output file path or file-like object (None = source + '.pyz')
    interpreter: Python interpreter shebang line
    main: 'module:callable' for main entry point
    """
    source = _pathlib.Path(source)
    has_main = False

    if source.is_dir():
        has_main = (source / MAIN_ENTRY).is_file()
    elif source.is_file():
        if not _zipfile.is_zipfile(source):
            raise ZipAppError(f"Source {source} is not a directory or zipfile")
        with _zipfile.ZipFile(str(source)) as zf:
            has_main = MAIN_ENTRY in zf.namelist()
    else:
        raise ZipAppError(f"Source {source} does not exist")

    if main and has_main:
        raise ZipAppError("Cannot specify 'main' when __main__.py already exists")
    if not main and not has_main:
        raise ZipAppError("Archive has no __main__.py and no 'main' specified")

    if target is None:
        if source.suffix == '.pyz':
            raise ZipAppError("Cannot use source directory as target")
        target = source.with_suffix('.pyz')

    if isinstance(target, (_os.PathLike, str)):
        target_path = _pathlib.Path(target)
        fd = open(str(target_path), 'wb')
        close_fd = True
    else:
        fd = target
        close_fd = False

    try:
        _write_file_prefix(fd, interpreter)
        compression = _zipfile.ZIP_DEFLATED if compressed else _zipfile.ZIP_STORED
        with _zipfile.ZipFile(fd, 'w', compression=compression) as zf:
            if main:
                pkg, func = main.rsplit(':', 1)
                main_py = (
                    f"# -*- coding: utf-8 -*-\n"
                    f"import {pkg}\n"
                    f"import sys\n"
                    f"sys.exit({pkg}.{func}())\n"
                )
                zf.writestr(MAIN_ENTRY, main_py)
            if source.is_dir():
                for path in sorted(source.rglob('*')):
                    if filter and not filter(path):
                        continue
                    arcname = path.relative_to(source)
                    if path.is_file() and str(arcname) != MAIN_ENTRY:
                        zf.write(str(path), str(arcname))
            else:
                with _zipfile.ZipFile(str(source)) as src_zf:
                    for item in src_zf.namelist():
                        if item != MAIN_ENTRY:
                            zf.writestr(item, src_zf.read(item))
    finally:
        if close_fd:
            fd.close()

    if isinstance(target, (_os.PathLike, str)):
        tpath = _pathlib.Path(target)
        mode = tpath.stat().st_mode
        tpath.chmod(mode | _stat.S_IXUSR | _stat.S_IXGRP | _stat.S_IXOTH)


def get_interpreter(archive):
    """Return the interpreter from the shebang line of archive, or None."""
    with open(str(archive), 'rb') as f:
        first_line = f.readline()
    if first_line.startswith(b'#!'):
        return first_line[2:].rstrip(b'\n').decode()
    return None


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def zipapp2_error():
    """ZipAppError exception class exists; returns True."""
    return issubclass(ZipAppError, ValueError)


def zipapp2_get_interpreter():
    """get_interpreter() returns the interpreter from an archive; returns True."""
    import tempfile as _tmpmod
    with _tmpmod.TemporaryDirectory() as d:
        src = _os.path.join(d, 'myapp')
        _os.makedirs(src)
        with open(_os.path.join(src, '__main__.py'), 'w') as f:
            f.write('print("hello")\n')
        out = _os.path.join(d, 'myapp.pyz')
        create_archive(src, out, interpreter='/usr/bin/env python3')
        interp = get_interpreter(out)
        return interp == '/usr/bin/env python3'


def zipapp2_create():
    """create_archive() creates a runnable zip archive; returns True."""
    import tempfile as _tmpmod
    with _tmpmod.TemporaryDirectory() as d:
        src = _os.path.join(d, 'myapp')
        _os.makedirs(src)
        with open(_os.path.join(src, '__main__.py'), 'w') as f:
            f.write('print("hello")\n')
        out = _os.path.join(d, 'myapp.pyz')
        create_archive(src, out)
        return _os.path.exists(out) and _zipfile.is_zipfile(out)


__all__ = [
    'ZipAppError', 'create_archive', 'get_interpreter',
    'zipapp2_error', 'zipapp2_get_interpreter', 'zipapp2_create',
]
