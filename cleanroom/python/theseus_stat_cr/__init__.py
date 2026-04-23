"""
theseus_stat_cr — Clean-room stat module constants and helpers.
No import of the standard `stat` module.
"""

import os

# File type bits
S_IFMT  = 0o170000
S_IFSOCK = 0o140000
S_IFLNK = 0o120000
S_IFREG = 0o100000
S_IFBLK = 0o060000
S_IFDIR = 0o040000
S_IFCHR = 0o020000
S_IFIFO = 0o010000

# Permission bits
S_ISUID = 0o4000
S_ISGID = 0o2000
S_ISVTX = 0o1000

S_IRWXU = 0o700
S_IRUSR = 0o400
S_IWUSR = 0o200
S_IXUSR = 0o100

S_IRWXG = 0o070
S_IRGRP = 0o040
S_IWGRP = 0o020
S_IXGRP = 0o010

S_IRWXO = 0o007
S_IROTH = 0o004
S_IWOTH = 0o002
S_IXOTH = 0o001


def S_IFMT_(mode):
    return mode & S_IFMT


def S_ISREG(mode):
    return S_IFMT_(mode) == S_IFREG


def S_ISDIR(mode):
    return S_IFMT_(mode) == S_IFDIR


def S_ISLNK(mode):
    return S_IFMT_(mode) == S_IFLNK


def S_ISBLK(mode):
    return S_IFMT_(mode) == S_IFBLK


def S_ISCHR(mode):
    return S_IFMT_(mode) == S_IFCHR


def S_ISFIFO(mode):
    return S_IFMT_(mode) == S_IFIFO


def S_ISSOCK(mode):
    return S_IFMT_(mode) == S_IFSOCK


def filemode(mode):
    """Return a string like '-rwxr-xr-x' from a numeric mode."""
    _type_chars = {
        S_IFREG: '-',
        S_IFDIR: 'd',
        S_IFLNK: 'l',
        S_IFBLK: 'b',
        S_IFCHR: 'c',
        S_IFIFO: 'p',
        S_IFSOCK: 's',
    }
    ftype = _type_chars.get(S_IFMT_(mode), '?')

    def rwx(bits, r, w, x, sticky=False, setid=False):
        chars = [
            'r' if bits & r else '-',
            'w' if bits & w else '-',
        ]
        if sticky:
            chars.append('t' if bits & x else 'T')
        elif setid:
            chars.append('s' if bits & x else 'S')
        else:
            chars.append('x' if bits & x else '-')
        return ''.join(chars)

    umode = rwx(mode, S_IRUSR, S_IWUSR, S_IXUSR, setid=bool(mode & S_ISUID))
    gmode = rwx(mode, S_IRGRP, S_IWGRP, S_IXGRP, setid=bool(mode & S_ISGID))
    omode = rwx(mode, S_IROTH, S_IWOTH, S_IXOTH, sticky=bool(mode & S_ISVTX))

    return ftype + umode + gmode + omode


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def stat2_isreg():
    """S_ISREG(os.stat(__file__).st_mode) is True for a regular file; returns True."""
    import os as _os
    mode = _os.stat(__file__).st_mode
    return S_ISREG(mode)


def stat2_filemode():
    """filemode(0o100644) == '-rw-r--r--'; returns '-rw-r--r--'."""
    return filemode(0o100644)


def stat2_constants():
    """S_IRUSR | S_IWUSR | S_IRGRP | S_IROTH == 0o644; returns True."""
    return (S_IRUSR | S_IWUSR | S_IRGRP | S_IROTH) == 0o644


__all__ = [
    'S_IFMT', 'S_IFSOCK', 'S_IFLNK', 'S_IFREG', 'S_IFBLK',
    'S_IFDIR', 'S_IFCHR', 'S_IFIFO',
    'S_ISUID', 'S_ISGID', 'S_ISVTX',
    'S_IRUSR', 'S_IWUSR', 'S_IXUSR',
    'S_IRGRP', 'S_IWGRP', 'S_IXGRP',
    'S_IROTH', 'S_IWOTH', 'S_IXOTH',
    'S_ISREG', 'S_ISDIR', 'S_ISLNK', 'S_ISBLK', 'S_ISCHR', 'S_ISFIFO', 'S_ISSOCK',
    'filemode',
    'stat2_isreg', 'stat2_filemode', 'stat2_constants',
]
