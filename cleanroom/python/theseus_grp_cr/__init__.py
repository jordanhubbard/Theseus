"""
Clean-room reimplementation of the standard library ``grp`` module.

This module reads ``/etc/group`` directly to provide group-database
lookups without importing the original ``grp`` module.

Public API mirrors the standard library:
    - struct_group   : sequence-like type holding a single group entry
    - getgrall()     : return a list of all group entries
    - getgrgid(gid)  : look up a group entry by numeric GID
    - getgrnam(name) : look up a group entry by name

Invariant wrappers exposed for the Theseus verification harness:
    - grp2_struct_group()  : True if struct_group has the expected fields
    - grp2_getgrall()      : True if getgrall() returns a non-empty list
    - grp2_getgrgid()      : True if getgrgid(int) round-trips a real entry
    - grp2_getgrnam()      : True if getgrnam(str) round-trips a real entry

The invariant wrappers are nullary (take no arguments) and return ``True``
when the underlying behavior matches the documented contract.  This is the
shape the Theseus ``python_call_eq`` harness expects.
"""

import os as _os

__all__ = [
    "struct_group",
    "getgrall",
    "getgrgid",
    "getgrnam",
    "grp2_struct_group",
    "grp2_getgrall",
    "grp2_getgrgid",
    "grp2_getgrnam",
]

_GROUP_FILE = "/etc/group"


# ---------------------------------------------------------------------------
# struct_group
# ---------------------------------------------------------------------------
class struct_group(tuple):
    """Results from getgr*() routines.

    Behaves like a 4-tuple ``(gr_name, gr_passwd, gr_gid, gr_mem)`` and
    exposes the same fields as named attributes, matching the interface
    of the C-implemented ``grp.struct_group`` type.
    """

    __slots__ = ()

    n_fields = 4
    n_sequence_fields = 4
    n_unnamed_fields = 0

    _fields = ("gr_name", "gr_passwd", "gr_gid", "gr_mem")

    def __new__(cls, *args, **kwargs):
        # Accept either:
        #   struct_group((name, passwd, gid, mem))   - one iterable
        #   struct_group(name, passwd, gid, mem)      - four positionals
        #   struct_group(gr_name=..., gr_passwd=..., gr_gid=..., gr_mem=...)
        if kwargs and not args:
            try:
                seq = (
                    kwargs["gr_name"],
                    kwargs["gr_passwd"],
                    kwargs["gr_gid"],
                    kwargs["gr_mem"],
                )
            except KeyError as exc:
                raise TypeError(
                    "struct_group() missing required keyword argument: %s" % exc
                )
        elif len(args) == 1 and not kwargs:
            seq = tuple(args[0])
        elif len(args) == 4 and not kwargs:
            seq = args
        else:
            raise TypeError(
                "struct_group() takes a 4-sequence "
                "(or 4 positional / 4 keyword arguments)"
            )

        if len(seq) != 4:
            raise TypeError(
                "grp.struct_group() takes a 4-sequence (%d-sequence given)"
                % len(seq)
            )
        name, passwd, gid, mem = seq
        if not isinstance(mem, list):
            mem = list(mem) if mem is not None else []
        return tuple.__new__(cls, (name, passwd, gid, mem))

    @property
    def gr_name(self):
        """Group name."""
        return self[0]

    @property
    def gr_passwd(self):
        """Group password (often a placeholder such as ``*`` or ``x``)."""
        return self[1]

    @property
    def gr_gid(self):
        """Numeric group ID."""
        return self[2]

    @property
    def gr_mem(self):
        """List of group member usernames."""
        return self[3]

    def __repr__(self):
        return (
            "grp.struct_group(gr_name=%r, gr_passwd=%r, "
            "gr_gid=%r, gr_mem=%r)"
            % (self[0], self[1], self[2], self[3])
        )


# ---------------------------------------------------------------------------
# /etc/group parser
# ---------------------------------------------------------------------------
def _coerce_gid(gid):
    """Convert ``gid`` to a Python int, mirroring ``grp.getgrgid``."""
    if isinstance(gid, bool):
        return int(gid)
    if isinstance(gid, int):
        return gid
    if hasattr(gid, "__index__"):
        try:
            return gid.__index__()
        except Exception:
            pass
    raise TypeError(
        "getgrgid() argument must be int, not %s" % type(gid).__name__
    )


def _parse_group_line(line):
    """Parse one ``/etc/group`` line into a ``struct_group``.

    Returns ``None`` for blank lines, comments, or malformed entries.
    """
    if line.endswith("\n"):
        line = line[:-1]
    if line.endswith("\r"):
        line = line[:-1]

    if not line:
        return None
    stripped = line.lstrip()
    if stripped.startswith("#"):
        return None

    parts = line.split(":")
    if len(parts) < 4:
        return None

    name = parts[0]
    passwd = parts[1]
    gid_str = parts[2]
    members_field = ":".join(parts[3:])

    try:
        gid = int(gid_str)
    except ValueError:
        return None

    if members_field == "":
        members = []
    else:
        members = [m for m in members_field.split(",") if m]

    return struct_group((name, passwd, gid, members))


def _read_group_file():
    """Yield every ``struct_group`` parsed from ``/etc/group``."""
    try:
        fd = _os.open(_GROUP_FILE, _os.O_RDONLY)
    except OSError:
        return

    try:
        chunks = []
        while True:
            chunk = _os.read(fd, 65536)
            if not chunk:
                break
            chunks.append(chunk)
    finally:
        try:
            _os.close(fd)
        except OSError:
            pass

    data = b"".join(chunks)
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        text = data.decode("utf-8", errors="replace")

    for raw_line in text.split("\n"):
        entry = _parse_group_line(raw_line)
        if entry is not None:
            yield entry


# ---------------------------------------------------------------------------
# Public stdlib-compatible API
# ---------------------------------------------------------------------------
def getgrall():
    """Return a list of all available group entries, in file order."""
    return list(_read_group_file())


def getgrgid(gid):
    """Return the group entry whose numeric GID matches ``gid``.

    Raises ``KeyError`` if no such entry exists.
    """
    target = _coerce_gid(gid)
    for entry in _read_group_file():
        if entry.gr_gid == target:
            return entry
    raise KeyError("getgrgid(): gid not found: %d" % target)


def getgrnam(name):
    """Return the group entry whose name matches ``name``.

    Raises ``KeyError`` if no such entry exists.
    """
    if not isinstance(name, str):
        raise TypeError(
            "getgrnam() argument must be str, not %s" % type(name).__name__
        )
    for entry in _read_group_file():
        if entry.gr_name == name:
            return entry
    raise KeyError("getgrnam(): name not found: %s" % name)


# ---------------------------------------------------------------------------
# Theseus invariant wrappers.
#
# The Theseus ``python_call_eq`` harness invokes each ``grp2_*`` symbol with
# no arguments and asserts the return value equals ``True``.  Each wrapper
# therefore exercises the underlying contract and returns a boolean.
# ---------------------------------------------------------------------------
def grp2_struct_group():
    """True if ``struct_group`` exposes the documented gr_name / gr_gid fields.

    Constructs a synthetic 4-tuple, verifies field accessors, indexing, and
    sequence semantics all behave per the stdlib contract.
    """
    sample = struct_group(("theseus_test", "*", 4242, ["alice", "bob"]))

    # Named attribute access.
    if sample.gr_name != "theseus_test":
        return False
    if sample.gr_passwd != "*":
        return False
    if sample.gr_gid != 4242:
        return False
    if sample.gr_mem != ["alice", "bob"]:
        return False

    # Sequence access (it inherits from tuple).
    if sample[0] != "theseus_test":
        return False
    if sample[2] != 4242:
        return False
    if len(sample) != 4:
        return False

    # Field-name introspection mirrors CPython's structseq.
    if "gr_name" not in struct_group._fields:
        return False
    if "gr_gid" not in struct_group._fields:
        return False

    return True


def grp2_getgrall():
    """True if ``getgrall()`` returns a non-empty list of struct_group entries."""
    entries = getgrall()
    if not isinstance(entries, list):
        return False
    if len(entries) == 0:
        return False
    for entry in entries:
        if not isinstance(entry, struct_group):
            return False
        if not isinstance(entry.gr_name, str):
            return False
        if not isinstance(entry.gr_gid, int):
            return False
        if not isinstance(entry.gr_mem, list):
            return False
    return True


def grp2_getgrgid():
    """True if ``getgrgid(int)`` returns the matching entry from ``getgrall()``.

    Picks the first available group, looks it up by numeric GID, and confirms
    the lookup yields the same name and gid.  Also confirms ``KeyError`` is
    raised for a deliberately missing GID.
    """
    entries = getgrall()
    if not entries:
        return False

    # Lookups should resolve every entry returned by getgrall().
    for expected in entries:
        try:
            found = getgrgid(expected.gr_gid)
        except KeyError:
            return False
        if found.gr_gid != expected.gr_gid:
            return False
        if found.gr_name != expected.gr_name:
            return False
        # Once we have proof for one entry we can stop — every group file is
        # consistent with itself, and walking thousands of groups would be
        # wasteful.
        break

    # A GID we are confident does not exist must raise KeyError.
    used_gids = {e.gr_gid for e in entries}
    bogus = 1
    while bogus in used_gids:
        bogus += 1
    # Use a clearly-out-of-range value to minimize collision risk.
    bogus = max(used_gids) + 9_999_999 if used_gids else 9_999_999
    try:
        getgrgid(bogus)
    except KeyError:
        pass
    else:
        return False

    return True


def grp2_getgrnam():
    """True if ``getgrnam(str)`` round-trips entries returned by getgrall()."""
    entries = getgrall()
    if not entries:
        return False
    sample = entries[0]
    try:
        found = getgrnam(sample.gr_name)
    except KeyError:
        return False
    if found.gr_name != sample.gr_name:
        return False
    if found.gr_gid != sample.gr_gid:
        return False
    return True