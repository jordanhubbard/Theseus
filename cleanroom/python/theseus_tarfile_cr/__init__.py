"""Clean-room tar archive reader/writer (ustar / POSIX.1-1988).

Implements a minimal subset of the tar archive format from scratch,
without importing the standard library `tarfile` module.
"""

import io
import os

BLOCK_SIZE = 512

# Type flags
REGTYPE = b"0"
AREGTYPE = b"\x00"
DIRTYPE = b"5"


class TarError(Exception):
    pass


class TarInfo:
    """Represents one entry (header record) in a tar archive."""

    def __init__(self, name=""):
        self.name = name
        self.size = 0
        self.mode = 0o644
        self.mtime = 0
        self.uid = 0
        self.gid = 0
        self.uname = ""
        self.gname = ""
        self.typeflag = REGTYPE
        self.linkname = ""
        self._data = b""

    def _encode_header(self):
        """Encode this TarInfo into a 512-byte ustar header block."""
        name_bytes = self.name.encode("utf-8", errors="replace")
        prefix_bytes = b""
        if len(name_bytes) > 100:
            # Try to split into prefix + name on a "/" boundary.
            split = name_bytes.rfind(b"/", 0, 156)
            if split != -1 and len(name_bytes[split + 1:]) <= 100:
                prefix_bytes = name_bytes[:split]
                name_bytes = name_bytes[split + 1:]
            else:
                name_bytes = name_bytes[:100]

        def octal_field(value, width):
            # width includes the trailing NUL byte expected by ustar.
            s = ("%0*o" % (width - 1, value)).encode("ascii")
            return s + b"\x00"

        name_field = name_bytes.ljust(100, b"\x00")[:100]
        mode_field = octal_field(self.mode & 0o7777, 8)
        uid_field = octal_field(self.uid & 0o7777777, 8)
        gid_field = octal_field(self.gid & 0o7777777, 8)
        size_field = octal_field(self.size, 12)
        mtime_field = octal_field(self.mtime, 12)
        chksum_placeholder = b" " * 8

        tf = self.typeflag
        if isinstance(tf, str):
            tf = tf.encode("ascii")
        if not tf:
            tf = REGTYPE
        typeflag_field = tf[:1]

        linkname_field = self.linkname.encode("utf-8", errors="replace")[:100].ljust(100, b"\x00")
        magic_field = b"ustar\x00"
        version_field = b"00"
        uname_field = self.uname.encode("utf-8", errors="replace")[:32].ljust(32, b"\x00")
        gname_field = self.gname.encode("utf-8", errors="replace")[:32].ljust(32, b"\x00")
        devmajor_field = b"\x00" * 8
        devminor_field = b"\x00" * 8
        prefix_field = prefix_bytes.ljust(155, b"\x00")[:155]
        padding = b"\x00" * 12

        header = (
            name_field
            + mode_field
            + uid_field
            + gid_field
            + size_field
            + mtime_field
            + chksum_placeholder
            + typeflag_field
            + linkname_field
            + magic_field
            + version_field
            + uname_field
            + gname_field
            + devmajor_field
            + devminor_field
            + prefix_field
            + padding
        )

        if len(header) != BLOCK_SIZE:
            raise TarError("internal header sizing error: %d" % len(header))

        # Compute checksum: unsigned sum of all header bytes,
        # treating the chksum field as 8 spaces.
        chksum = sum(header)
        chksum_bytes = ("%06o" % chksum).encode("ascii") + b"\x00 "
        header = header[:148] + chksum_bytes + header[156:]
        return header


def _parse_octal(field):
    s = field.rstrip(b"\x00 ").lstrip(b" ")
    if not s:
        return 0
    try:
        return int(s, 8)
    except ValueError:
        return 0


def _parse_header(buf):
    """Parse a 512-byte header block into a TarInfo, or None if it is empty."""
    if len(buf) < BLOCK_SIZE:
        return None
    if buf == b"\x00" * BLOCK_SIZE:
        return None

    info = TarInfo()
    name = buf[0:100].rstrip(b"\x00").decode("utf-8", errors="replace")
    prefix = buf[345:500].rstrip(b"\x00").decode("utf-8", errors="replace")
    if prefix:
        info.name = prefix + "/" + name
    else:
        info.name = name

    info.mode = _parse_octal(buf[100:108])
    info.uid = _parse_octal(buf[108:116])
    info.gid = _parse_octal(buf[116:124])
    info.size = _parse_octal(buf[124:136])
    info.mtime = _parse_octal(buf[136:148])

    tf = buf[156:157]
    info.typeflag = tf if tf and tf != b"\x00" else REGTYPE

    info.linkname = buf[157:257].rstrip(b"\x00").decode("utf-8", errors="replace")
    info.uname = buf[265:297].rstrip(b"\x00").decode("utf-8", errors="replace")
    info.gname = buf[297:329].rstrip(b"\x00").decode("utf-8", errors="replace")
    return info


class TarFile:
    """Read or create a tar archive in ustar format."""

    def __init__(self, name=None, mode="r", fileobj=None):
        self.name = name
        self.mode = mode
        self.members = []
        self._buffer = bytearray()
        self._fileobj = fileobj
        self._closed = False

        if mode.startswith("r"):
            self._read_all()
        elif mode.startswith("w") or mode.startswith("a"):
            # writable; data accumulates in self._buffer until close()
            pass
        else:
            raise TarError("unsupported mode: %r" % mode)

    # --- Reading --------------------------------------------------------

    def _read_all(self):
        if self._fileobj is not None:
            data = self._fileobj.read()
        elif self.name is not None:
            with open(self.name, "rb") as f:
                data = f.read()
        else:
            data = b""

        offset = 0
        n = len(data)
        while offset + BLOCK_SIZE <= n:
            header = data[offset:offset + BLOCK_SIZE]
            if header == b"\x00" * BLOCK_SIZE:
                break
            info = _parse_header(header)
            if info is None:
                break
            offset += BLOCK_SIZE
            payload = data[offset:offset + info.size]
            info._data = bytes(payload)
            blocks = (info.size + BLOCK_SIZE - 1) // BLOCK_SIZE
            offset += blocks * BLOCK_SIZE
            self.members.append(info)

    # --- Writing --------------------------------------------------------

    def _write_member(self, info, payload):
        info.size = len(payload)
        info._data = bytes(payload)
        header = info._encode_header()
        self._buffer.extend(header)
        self._buffer.extend(payload)
        pad = (-len(payload)) % BLOCK_SIZE
        if pad:
            self._buffer.extend(b"\x00" * pad)

    def add(self, name, arcname=None):
        """Add a file from the local filesystem to the archive."""
        if arcname is None:
            arcname = name
        info = TarInfo(arcname)
        try:
            st = os.stat(name)
            info.mode = st.st_mode & 0o7777
            info.mtime = int(st.st_mtime)
            info.uid = getattr(st, "st_uid", 0) or 0
            info.gid = getattr(st, "st_gid", 0) or 0
        except OSError:
            pass
        with open(name, "rb") as f:
            payload = f.read()
        self.members.append(info)
        self._write_member(info, payload)

    def addfile(self, tarinfo, fileobj=None):
        """Add a TarInfo (with optional fileobj for the data) to the archive."""
        if fileobj is not None:
            payload = fileobj.read()
        else:
            payload = getattr(tarinfo, "_data", b"") or b""
        self.members.append(tarinfo)
        self._write_member(tarinfo, payload)

    # --- Member access --------------------------------------------------

    def getmembers(self):
        return list(self.members)

    def getnames(self):
        return [m.name for m in self.members]

    def getmember(self, name):
        for m in self.members:
            if m.name == name:
                return m
        raise KeyError("filename %r not found" % name)

    def extractfile(self, member):
        if isinstance(member, str):
            member = self.getmember(member)
        if member is None:
            return None
        return io.BytesIO(member._data)

    # --- Lifecycle ------------------------------------------------------

    def close(self):
        if self._closed:
            return
        self._closed = True
        if self.mode.startswith("w") or self.mode.startswith("a"):
            # Two trailing zero blocks signal end-of-archive.
            self._buffer.extend(b"\x00" * (BLOCK_SIZE * 2))
            data = bytes(self._buffer)
            if self._fileobj is not None:
                self._fileobj.write(data)
            elif self.name is not None:
                with open(self.name, "wb") as f:
                    f.write(data)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False


# Convenience constructor mirroring tarfile.open's most basic shape.
def open(name=None, mode="r", fileobj=None):  # noqa: A001 - mirrors tarfile API name
    return TarFile(name=name, mode=mode, fileobj=fileobj)


# ---------------------------------------------------------------------------
# Invariant test functions
# ---------------------------------------------------------------------------

def tarfile2_addfile_read():
    """Add a TarInfo with payload "hello tar" then read it back."""
    buf = io.BytesIO()
    tf = TarFile(fileobj=buf, mode="w")
    info = TarInfo("test.txt")
    data = b"hello tar"
    info.size = len(data)
    tf.addfile(info, io.BytesIO(data))
    tf.close()

    buf.seek(0)
    tf2 = TarFile(fileobj=buf, mode="r")
    members = tf2.getmembers()
    fobj = tf2.extractfile(members[0])
    return fobj.read().decode("utf-8")


def tarfile2_getmembers():
    """Return the number of members in a two-entry archive."""
    buf = io.BytesIO()
    tf = TarFile(fileobj=buf, mode="w")

    info1 = TarInfo("a.txt")
    data1 = b"alpha"
    info1.size = len(data1)
    tf.addfile(info1, io.BytesIO(data1))

    info2 = TarInfo("b.txt")
    data2 = b"beta"
    info2.size = len(data2)
    tf.addfile(info2, io.BytesIO(data2))

    tf.close()

    buf.seek(0)
    tf2 = TarFile(fileobj=buf, mode="r")
    return len(tf2.getmembers())


def tarfile2_tarinfo_name():
    """Create a TarInfo and return its name."""
    info = TarInfo("test.txt")
    return info.name