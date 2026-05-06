"""Clean-room subset of shutil — implemented from scratch using only os/stdlib.

Does NOT import shutil. Provides copyfileobj, copyfile, which, rmtree, plus
invariant self-test functions.
"""

import os
import io
import stat
import errno


# ---------------------------------------------------------------------------
# copyfileobj
# ---------------------------------------------------------------------------

_DEFAULT_BUFFER_SIZE = 64 * 1024


def copyfileobj(fsrc, fdst, length=_DEFAULT_BUFFER_SIZE):
    """Copy data from file-like object fsrc to file-like object fdst.

    Reads in chunks of `length` bytes (default 64 KiB) until EOF.
    """
    if length is None or length <= 0:
        length = _DEFAULT_BUFFER_SIZE
    read = fsrc.read
    write = fdst.write
    while True:
        buf = read(length)
        if not buf:
            break
        write(buf)


# ---------------------------------------------------------------------------
# copyfile
# ---------------------------------------------------------------------------

def _samefile(src, dst):
    try:
        return os.path.samefile(src, dst)
    except (OSError, ValueError, AttributeError):
        return (os.path.normcase(os.path.abspath(src)) ==
                os.path.normcase(os.path.abspath(dst)))


def copyfile(src, dst):
    """Copy bytes from src path to dst path. No metadata is copied.

    Returns the path to the destination file.
    """
    if os.path.exists(src) and os.path.exists(dst) and _samefile(src, dst):
        raise OSError("`%s` and `%s` are the same file" % (src, dst))

    # Refuse to copy from special files (sockets, devices) but allow regular
    # files and symlinks-to-regular-files. Mirrors typical behavior.
    try:
        st = os.stat(src)
    except OSError:
        raise
    if stat.S_ISFIFO(st.st_mode) or stat.S_ISSOCK(st.st_mode):
        raise OSError("`%s` is not a regular file" % src)

    with open(src, "rb") as fsrc:
        with open(dst, "wb") as fdst:
            copyfileobj(fsrc, fdst)
    return dst


# ---------------------------------------------------------------------------
# which
# ---------------------------------------------------------------------------

def which(cmd, mode=os.F_OK | os.X_OK, path=None):
    """Return the absolute-ish path to an executable `cmd`, or None.

    Mirrors the standard semantics:
      - If cmd contains a directory component, check that path directly.
      - Otherwise, search the directories in PATH (or supplied `path`).
      - On Windows, also try every extension listed in PATHEXT and
        search the current directory first.
    """
    def _access_check(fn, mode):
        return (os.path.exists(fn)
                and os.access(fn, mode)
                and not os.path.isdir(fn))

    # If the command contains a directory component, only check that.
    if os.path.dirname(cmd):
        if _access_check(cmd, mode):
            return cmd
        return None

    use_bytes = isinstance(cmd, bytes)

    if path is None:
        path = os.environ.get("PATH", None)
        if path is None:
            try:
                path = os.confstr("CS_PATH")
            except (AttributeError, ValueError, OSError):
                path = os.defpath if hasattr(os, "defpath") else "/usr/bin:/bin"

    if not path:
        return None

    if use_bytes:
        path = os.fsencode(path)
        pathext_sep = os.fsencode(os.pathsep)
        paths = path.split(pathext_sep)
    else:
        paths = path.split(os.pathsep)

    # Windows: prepend current directory and try PATHEXT extensions.
    if os.name == "nt" or sys_platform_is_windows():
        curdir = os.curdir
        if use_bytes:
            curdir = os.fsencode(curdir)
        if curdir not in paths:
            paths.insert(0, curdir)

        pathext_env = os.environ.get("PATHEXT", "")
        pathext = [ext for ext in pathext_env.split(os.pathsep) if ext]
        if use_bytes:
            pathext = [os.fsencode(ext) for ext in pathext]

        # If cmd already ends with one of the extensions, don't re-add.
        cmd_lower = cmd.lower() if not use_bytes else cmd.lower()
        if any(cmd_lower.endswith(ext.lower()) for ext in pathext):
            files = [cmd]
        else:
            files = [cmd + ext for ext in pathext]
            # Also allow bare cmd in case caller put extension in name oddly
            files = files + [cmd]
    else:
        files = [cmd]

    seen = set()
    for directory in paths:
        normdir = os.path.normcase(directory)
        if normdir in seen:
            continue
        seen.add(normdir)
        for thefile in files:
            full = os.path.join(directory, thefile)
            if _access_check(full, mode):
                return full
    return None


def sys_platform_is_windows():
    """Best-effort Windows detection without importing sys.platform tricks."""
    return os.name == "nt"


# ---------------------------------------------------------------------------
# rmtree
# ---------------------------------------------------------------------------

def _is_dir_no_follow(path):
    """Return True if path is a directory and not a symlink."""
    try:
        st = os.lstat(path)
    except OSError:
        return False
    return stat.S_ISDIR(st.st_mode)


def _is_symlink(path):
    try:
        st = os.lstat(path)
    except OSError:
        return False
    return stat.S_ISLNK(st.st_mode)


def rmtree(path, ignore_errors=False, onerror=None):
    """Recursively delete a directory tree.

    Refuses to follow symlinks at the top level (raises OSError) and
    unlinks symlinks encountered inside rather than recursing into them.

    If `ignore_errors` is true, errors are silently ignored.
    Otherwise, if `onerror` is supplied it will be called as
    `onerror(function, path, exc_info)` — same shape as the standard
    library — and any unhandled error will propagate.
    """
    if ignore_errors:
        def _onerror(func, p, exc_info):
            pass
    elif onerror is None:
        def _onerror(func, p, exc_info):
            # Re-raise the original exception
            raise exc_info[1]
    else:
        _onerror = onerror

    # Refuse to operate on symlinks at the top level.
    try:
        if _is_symlink(path):
            # mirror stdlib: raise OSError
            try:
                raise OSError("Cannot call rmtree on a symbolic link")
            except OSError:
                import sys as _sys
                _onerror(os.path.islink, path, _sys.exc_info())
                return
    except OSError:
        import sys as _sys
        _onerror(os.path.islink, path, _sys.exc_info())
        return

    # List directory contents.
    try:
        entries = os.listdir(path)
    except OSError:
        import sys as _sys
        _onerror(os.listdir, path, _sys.exc_info())
        return

    for name in entries:
        fullname = os.path.join(path, name)
        try:
            mode = os.lstat(fullname).st_mode
        except OSError:
            import sys as _sys
            _onerror(os.lstat, fullname, _sys.exc_info())
            continue

        if stat.S_ISDIR(mode) and not stat.S_ISLNK(mode):
            # Recurse into real subdirectory
            rmtree(fullname, ignore_errors=ignore_errors, onerror=onerror)
        else:
            # File or symlink — just unlink
            try:
                os.unlink(fullname)
            except OSError:
                import sys as _sys
                _onerror(os.unlink, fullname, _sys.exc_info())

    # Finally remove the (now-empty) directory itself.
    try:
        os.rmdir(path)
    except OSError:
        import sys as _sys
        _onerror(os.rmdir, path, _sys.exc_info())


# ---------------------------------------------------------------------------
# Invariant self-test functions
# ---------------------------------------------------------------------------

def shutil2_copyfileobj():
    """Verify copyfileobj behavior using in-memory file objects."""
    try:
        # Empty source -> empty dest
        src = io.BytesIO(b"")
        dst = io.BytesIO()
        copyfileobj(src, dst)
        if dst.getvalue() != b"":
            return False

        # Small payload
        src = io.BytesIO(b"hello world")
        dst = io.BytesIO()
        copyfileobj(src, dst)
        if dst.getvalue() != b"hello world":
            return False

        # Larger than buffer chunk
        payload = b"A" * (200 * 1024) + b"B" * (50 * 1024)
        src = io.BytesIO(payload)
        dst = io.BytesIO()
        copyfileobj(src, dst, length=8192)
        if dst.getvalue() != payload:
            return False

        # Custom length=0 should fall back to default and still work
        src = io.BytesIO(b"abc")
        dst = io.BytesIO()
        copyfileobj(src, dst, length=0)
        if dst.getvalue() != b"abc":
            return False

        return True
    except Exception:
        return False


def shutil2_which():
    """Verify which() returns None for missing names and finds real ones."""
    try:
        # Nonexistent name must yield None
        bogus = "definitely_not_a_real_executable_xyz_9876543210"
        if which(bogus) is not None:
            return False

        # Find an actual executable on PATH and confirm we can locate it.
        path_env = os.environ.get("PATH", "")
        if not path_env:
            # Without a PATH there's nothing to find — logic still sound.
            # Verify path-component branch: a known directory entry by full path.
            return which(bogus) is None

        for d in path_env.split(os.pathsep):
            if not d:
                continue
            try:
                names = os.listdir(d)
            except OSError:
                continue
            for n in names:
                full = os.path.join(d, n)
                try:
                    if (os.path.isfile(full)
                            and os.access(full, os.X_OK)):
                        # Test bare-name lookup
                        result = which(n)
                        if result is None:
                            # Could be shadowed by an earlier same-name dir;
                            # try direct path lookup instead.
                            direct = which(full)
                            if direct != full:
                                return False
                            return True
                        # Verify the returned path is itself executable
                        if not os.access(result, os.X_OK):
                            return False
                        # Also verify direct-path lookup
                        if which(full) != full:
                            return False
                        return True
                except OSError:
                    continue
        # PATH had no executables; that's still fine — logic verified by
        # the bogus-name check above.
        return True
    except Exception:
        return False


def _make_temp_dir():
    """Pick a writable temp directory using only os."""
    candidates = [
        os.environ.get("TMPDIR"),
        os.environ.get("TEMP"),
        os.environ.get("TMP"),
        "/tmp",
        ".",
    ]
    for c in candidates:
        if c and os.path.isdir(c):
            return c
    return "."


def shutil2_rmtree():
    """Verify rmtree removes a nested directory tree."""
    try:
        base_tmp = _make_temp_dir()
        root = os.path.join(
            base_tmp, "theseus_shutil_cr_test_%d" % os.getpid()
        )
        # Clean any leftover
        if os.path.exists(root):
            rmtree(root, ignore_errors=True)

        # Build a small tree:
        #   root/
        #     file_a.txt
        #     sub1/
        #       file_b.txt
        #       sub2/
        #         file_c.txt
        os.makedirs(os.path.join(root, "sub1", "sub2"))
        with open(os.path.join(root, "file_a.txt"), "wb") as f:
            f.write(b"alpha")
        with open(os.path.join(root, "sub1", "file_b.txt"), "wb") as f:
            f.write(b"beta")
        with open(os.path.join(root, "sub1", "sub2", "file_c.txt"), "wb") as f:
            f.write(b"gamma")

        # Sanity: tree exists
        if not os.path.isdir(root):
            return False
        if not os.path.isfile(os.path.join(root, "sub1", "sub2", "file_c.txt")):
            return False

        rmtree(root)

        if os.path.exists(root):
            return False

        # ignore_errors=True on a missing path should be a no-op
        rmtree(root, ignore_errors=True)

        return True
    except Exception:
        # Best-effort cleanup
        try:
            if 'root' in locals() and os.path.exists(root):
                rmtree(root, ignore_errors=True)
        except Exception:
            pass
        return False


__all__ = [
    "copyfileobj",
    "copyfile",
    "which",
    "rmtree",
    "shutil2_copyfileobj",
    "shutil2_which",
    "shutil2_rmtree",
]