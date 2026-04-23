"""
theseus_shutil_cr — Clean-room shutil subset.
No import of the standard `shutil` module.
"""

import os
import io
import stat


def copyfileobj(fsrc, fdst, length=16 * 1024):
    """Copy data from file-like object fsrc to file-like object fdst."""
    while True:
        buf = fsrc.read(length)
        if not buf:
            break
        fdst.write(buf)


def copyfile(src, dst):
    """Copy bytes from src path to dst path (no metadata)."""
    with open(src, 'rb') as fsrc:
        with open(dst, 'wb') as fdst:
            copyfileobj(fsrc, fdst)
    return dst


def copy(src, dst):
    """Copy src to dst. If dst is a directory, copy into it."""
    if os.path.isdir(dst):
        dst = os.path.join(dst, os.path.basename(src))
    copyfile(src, dst)
    return dst


def copy2(src, dst):
    """Like copy(), but also preserve file metadata."""
    copy(src, dst)
    stat_result = os.stat(src)
    os.utime(dst, (stat_result.st_atime, stat_result.st_mtime))
    return dst


def which(name, mode=os.F_OK | os.X_OK, path=None):
    """Return the path to an executable, or None if not found."""
    if path is None:
        path = os.environ.get('PATH', os.defpath)
    if not path:
        return None

    path_list = path.split(os.pathsep)

    if os.path.sep in name:
        if os.access(name, mode):
            return name
        return None

    for directory in path_list:
        full_path = os.path.join(directory, name)
        if os.access(full_path, mode):
            return full_path
    return None


def rmtree(path, ignore_errors=False):
    """Recursively delete a directory tree."""
    try:
        for entry in os.scandir(path):
            if entry.is_dir(follow_symlinks=False):
                rmtree(entry.path, ignore_errors=ignore_errors)
            else:
                try:
                    os.unlink(entry.path)
                except OSError:
                    if not ignore_errors:
                        raise
        os.rmdir(path)
    except OSError:
        if not ignore_errors:
            raise


def move(src, dst):
    """Recursively move a file or directory to another location."""
    try:
        os.rename(src, dst)
    except OSError:
        copy2(src, dst)
        os.unlink(src)
    return dst


def disk_usage(path):
    """Return disk usage of the given path as (total, used, free)."""
    st = os.statvfs(path)
    free = st.f_bavail * st.f_frsize
    total = st.f_blocks * st.f_frsize
    used = (st.f_blocks - st.f_bfree) * st.f_frsize
    return _DiskUsage(total, used, free)


class _DiskUsage:
    def __init__(self, total, used, free):
        self.total = total
        self.used = used
        self.free = free

    def __repr__(self):
        return f'usage(total={self.total}, used={self.used}, free={self.free})'


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def shutil2_copyfileobj():
    """copyfileobj copies BytesIO content correctly; returns True."""
    src = io.BytesIO(b'hello world')
    dst = io.BytesIO()
    copyfileobj(src, dst)
    return dst.getvalue() == b'hello world'


def shutil2_which():
    """which('python3') or which('python') is not None; returns True."""
    result = which('python3') or which('python')
    return result is not None


def shutil2_rmtree():
    """rmtree removes a directory and its contents; returns True when gone."""
    import random as _random
    tmpbase = os.environ.get('TMPDIR') or '/tmp'
    d = os.path.join(tmpbase, 'shutil_test_%08x' % _random.randint(0, 0xFFFFFFFF))
    os.makedirs(d, exist_ok=True)
    subdir = os.path.join(d, 'sub')
    os.makedirs(subdir)
    with open(os.path.join(subdir, 'f.txt'), 'w') as f:
        f.write('data')
    rmtree(d)
    return not os.path.exists(d)


__all__ = [
    'copyfileobj', 'copyfile', 'copy', 'copy2',
    'which', 'rmtree', 'move', 'disk_usage',
    'shutil2_copyfileobj', 'shutil2_which', 'shutil2_rmtree',
]
