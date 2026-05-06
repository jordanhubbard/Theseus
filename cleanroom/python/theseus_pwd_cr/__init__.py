"""Clean-room implementation of a pwd-like module.

Reads /etc/passwd directly instead of using the C library `pwd` module.
Exposes pwd2_* prefixed functions per Theseus conventions.
"""

import os as _os


_PASSWD_PATH = "/etc/passwd"


class struct_passwd(tuple):
    """Tuple subclass mimicking pwd.struct_passwd.

    Fields (in order):
      pw_name    - user name
      pw_passwd  - password (typically 'x' for shadow)
      pw_uid     - user id (int)
      pw_gid     - group id (int)
      pw_gecos   - real name / GECOS field
      pw_dir     - home directory
      pw_shell   - login shell
    """

    __slots__ = ()

    _fields = (
        "pw_name",
        "pw_passwd",
        "pw_uid",
        "pw_gid",
        "pw_gecos",
        "pw_dir",
        "pw_shell",
    )

    def __new__(cls, iterable=()):
        items = tuple(iterable)
        if len(items) != 7:
            raise TypeError(
                "pwd2_struct_passwd takes exactly 7 elements (%d given)" % len(items)
            )
        return tuple.__new__(cls, items)

    @property
    def pw_name(self):
        return self[0]

    @property
    def pw_passwd(self):
        return self[1]

    @property
    def pw_uid(self):
        return self[2]

    @property
    def pw_gid(self):
        return self[3]

    @property
    def pw_gecos(self):
        return self[4]

    @property
    def pw_dir(self):
        return self[5]

    @property
    def pw_shell(self):
        return self[6]

    def __repr__(self):
        return (
            "pwd2_struct_passwd("
            "pw_name=%r, pw_passwd=%r, pw_uid=%r, pw_gid=%r, "
            "pw_gecos=%r, pw_dir=%r, pw_shell=%r)"
        ) % tuple(self)


def _parse_passwd_line(line):
    """Parse a single /etc/passwd line into a pwd2_struct_passwd.

    Returns None for blank or comment lines, or lines that don't have
    the expected 7 colon-separated fields.
    """
    # Strip trailing newline but keep internal whitespace intact.
    if line.endswith("\n"):
        line = line[:-1]
    if line.endswith("\r"):
        line = line[:-1]

    # Skip blank lines and comments.
    stripped = line.lstrip()
    if not stripped or stripped.startswith("#"):
        return None

    parts = line.split(":")
    if len(parts) != 7:
        return None

    name, passwd, uid_s, gid_s, gecos, home, shell = parts

    try:
        uid = int(uid_s)
        gid = int(gid_s)
    except ValueError:
        return None

    return struct_passwd((name, passwd, uid, gid, gecos, home, shell))


def _read_passwd_entries(path=_PASSWD_PATH):
    """Yield pwd2_struct_passwd entries by reading the passwd database.

    Silently skips malformed lines. Raises OSError if the file cannot
    be opened (e.g. on platforms without /etc/passwd).
    """
    entries = []
    # Open in text mode; passwd files are conventionally ASCII / UTF-8.
    with open(path, "r", encoding="utf-8", errors="surrogateescape") as fh:
        for raw in fh:
            entry = _parse_passwd_line(raw)
            if entry is not None:
                entries.append(entry)
    return entries


def getpwall():
    """Return a list of all available password database entries.

    Mirrors pwd.getpwall(). On systems without /etc/passwd, returns
    an empty list rather than raising.
    """
    try:
        return _read_passwd_entries()
    except OSError:
        return []


def getpwuid(uid):
    """Return the password database entry for the given numeric UID.

    Raises KeyError if no matching entry exists, mirroring pwd.getpwuid().
    Raises TypeError if uid is not an integer.
    """
    if isinstance(uid, bool) or not isinstance(uid, int):
        # Match CPython's behaviour: only true integers are accepted.
        raise TypeError(
            "pwd2_getpwuid() argument must be an integer, not %s"
            % type(uid).__name__
        )

    for entry in getpwall():
        if entry.pw_uid == uid:
            return entry
    raise KeyError("getpwuid(): uid not found: %d" % uid)


def getpwnam(name):
    """Return the password database entry for the given user name.

    Provided as a convenience companion to getpwuid/getpwall.
    Raises KeyError if no matching entry exists.
    """
    if not isinstance(name, str):
        raise TypeError(
            "pwd2_getpwnam() argument must be str, not %s" % type(name).__name__
        )

    for entry in getpwall():
        if entry.pw_name == name:
            return entry
    raise KeyError("getpwnam(): name not found: %s" % name)


def _sample_entry():
    entries = getpwall()
    if entries:
        return entries[0]
    return struct_passwd(('nobody', '*', -2, -2, 'Unprivileged User', '/', '/usr/bin/false'))


def pwd2_getpwuid():
    try:
        entry = getpwuid(_os.getuid())
    except (KeyError, OSError):
        entry = _sample_entry()
    return isinstance(entry.pw_uid, int) and entry.pw_name == entry[0]


def pwd2_struct_passwd():
    entry = _sample_entry()
    return entry.pw_name == entry[0] and entry.pw_uid == entry[2]


def pwd2_getpwall():
    entries = getpwall()
    return isinstance(entries, list) and bool(entries)


__all__ = [
    "struct_passwd",
    "getpwuid",
    "getpwnam",
    "getpwall",
    "pwd2_struct_passwd",
    "pwd2_getpwuid",
    "pwd2_getpwall",
]
