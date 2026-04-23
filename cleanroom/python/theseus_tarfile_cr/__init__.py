"""
theseus_tarfile_cr — Clean-room tar archive reader/writer (ustar format).
No import of the standard `tarfile` module.
"""

import io
import os
import struct
import time

_BLOCKSIZE = 512
_RECORDSIZE = 10 * _BLOCKSIZE
_GNU_MAGIC = b'ustar  \x00'
_POSIX_MAGIC = b'ustar\x0000'

REGTYPE = b'0'
DIRTYPE = b'5'


def _encode(s, length, encoding='utf-8'):
    """Encode string to bytes, null-padded to length."""
    b = s.encode(encoding)
    return b[:length].ljust(length, b'\x00')


def _checksum(buf):
    """Calculate tar header checksum."""
    s = 256  # 8 spaces for checksum field
    for i, b in enumerate(buf):
        if 148 <= i < 156:
            continue
        s += b
    return s


class TarInfo:
    """Information about a tar archive member."""

    def __init__(self, name=''):
        self.name = name
        self.mode = 0o644
        self.uid = 0
        self.gid = 0
        self.size = 0
        self.mtime = int(time.time())
        self.type = REGTYPE
        self.linkname = ''
        self.uname = ''
        self.gname = ''
        self._offset_data = 0

    def _build_header(self):
        """Build a 512-byte ustar header block."""
        buf = bytearray(512)

        def put(offset, length, value):
            if isinstance(value, str):
                value = value.encode('utf-8')
            value = value[:length].ljust(length, b'\x00')
            buf[offset:offset + length] = value

        def put_oct(offset, length, value):
            s = ('%0*o' % (length - 1, value)).encode() + b'\x00'
            buf[offset:offset + length] = s[:length]

        put(0, 100, self.name)
        put_oct(100, 8, self.mode)
        put_oct(108, 8, self.uid)
        put_oct(116, 8, self.gid)
        put_oct(124, 12, self.size)
        put_oct(136, 12, self.mtime)
        buf[156] = self.type[0] if isinstance(self.type, bytes) else ord(self.type)
        put(157, 100, self.linkname)
        put(257, 6, b'ustar')
        put(263, 2, b'00')
        put(265, 32, self.uname)
        put(297, 32, self.gname)

        chksum = _checksum(buf)
        put(148, 8, ('%06o\x00 ' % chksum).encode())
        return bytes(buf)

    @classmethod
    def _from_header(cls, buf):
        """Parse a 512-byte header block."""
        def get_str(offset, length):
            raw = buf[offset:offset + length]
            null = raw.find(b'\x00')
            if null >= 0:
                raw = raw[:null]
            return raw.decode('utf-8', errors='replace')

        def get_oct(offset, length):
            raw = buf[offset:offset + length].strip(b'\x00 ')
            if not raw:
                return 0
            try:
                return int(raw, 8)
            except ValueError:
                return 0

        info = cls()
        info.name = get_str(0, 100)
        info.mode = get_oct(100, 8)
        info.uid = get_oct(108, 8)
        info.gid = get_oct(116, 8)
        info.size = get_oct(124, 12)
        info.mtime = get_oct(136, 12)
        type_byte = buf[156:157]
        info.type = type_byte if type_byte else REGTYPE
        info.linkname = get_str(157, 100)
        info.uname = get_str(265, 32)
        info.gname = get_str(297, 32)
        return info


class TarFile:
    """TAR archive reader/writer."""

    def __init__(self, name=None, mode='r', fileobj=None):
        self._mode = mode
        self._members = []

        if fileobj is not None:
            self._fileobj = fileobj
            self._close_fileobj = False
        elif name is not None:
            if mode == 'r':
                self._fileobj = open(name, 'rb')
            else:
                self._fileobj = open(name, 'w+b')
            self._close_fileobj = True
        else:
            raise ValueError("Either name or fileobj must be given")

        if mode == 'r':
            self._read_members()

    def _read_members(self):
        f = self._fileobj
        f.seek(0)
        while True:
            header = f.read(_BLOCKSIZE)
            if len(header) < _BLOCKSIZE or header == b'\x00' * _BLOCKSIZE:
                break
            info = TarInfo._from_header(header)
            if not info.name:
                break
            info._offset_data = f.tell()
            self._members.append(info)
            # Skip data blocks
            blocks = (info.size + _BLOCKSIZE - 1) // _BLOCKSIZE
            f.seek(blocks * _BLOCKSIZE, 1)

    def getmembers(self):
        """Return list of TarInfo objects."""
        return list(self._members)

    def getnames(self):
        """Return list of member names."""
        return [m.name for m in self._members]

    def getmember(self, name):
        for m in self._members:
            if m.name == name:
                return m
        raise KeyError(f'{name!r} not found in archive')

    def extractfile(self, member):
        """Return a file-like object for reading member data."""
        if isinstance(member, str):
            member = self.getmember(member)
        self._fileobj.seek(member._offset_data)
        return io.BytesIO(self._fileobj.read(member.size))

    def addfile(self, tarinfo, fileobj=None):
        """Add tarinfo to archive, reading data from fileobj."""
        header = tarinfo._build_header()
        self._fileobj.write(header)
        if fileobj is not None:
            data = fileobj.read()
            self._fileobj.write(data)
            pad = (_BLOCKSIZE - len(data) % _BLOCKSIZE) % _BLOCKSIZE
            if pad:
                self._fileobj.write(b'\x00' * pad)
        tarinfo._offset_data = self._fileobj.tell() - (tarinfo.size + (_BLOCKSIZE - tarinfo.size % _BLOCKSIZE) % _BLOCKSIZE)
        self._members.append(tarinfo)

    def add(self, name, arcname=None):
        """Add a file to the archive."""
        if arcname is None:
            arcname = os.path.basename(name)
        stat_result = os.stat(name)
        info = TarInfo(arcname)
        info.size = stat_result.st_size
        info.mtime = int(stat_result.st_mtime)
        info.mode = stat_result.st_mode & 0o7777
        with open(name, 'rb') as f:
            self.addfile(info, f)

    def close(self):
        """Write end-of-archive and close."""
        if self._mode in ('w', 'x', 'a'):
            self._fileobj.write(b'\x00' * (_BLOCKSIZE * 2))
        if self._close_fileobj:
            self._fileobj.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def tarfile2_addfile_read():
    """Add bytes to tar, extractfile reads them back; returns 'hello tar'."""
    buf = io.BytesIO()
    with TarFile(fileobj=buf, mode='w') as tf:
        data = b'hello tar'
        info = TarInfo('test.txt')
        info.size = len(data)
        tf.addfile(info, io.BytesIO(data))
    buf.seek(0)
    with TarFile(fileobj=buf, mode='r') as tf:
        return tf.extractfile('test.txt').read().decode('utf-8')


def tarfile2_getmembers():
    """Add 2 files, getmembers() returns 2 entries; returns 2."""
    buf = io.BytesIO()
    with TarFile(fileobj=buf, mode='w') as tf:
        for name, content in [('a.txt', b'aaa'), ('b.txt', b'bbb')]:
            info = TarInfo(name)
            info.size = len(content)
            tf.addfile(info, io.BytesIO(content))
    buf.seek(0)
    with TarFile(fileobj=buf, mode='r') as tf:
        return len(tf.getmembers())


def tarfile2_tarinfo_name():
    """TarInfo constructed with name has correct .name attribute; returns 'test.txt'."""
    info = TarInfo('test.txt')
    return info.name


__all__ = [
    'TarFile', 'TarInfo', 'REGTYPE', 'DIRTYPE',
    'tarfile2_addfile_read', 'tarfile2_getmembers', 'tarfile2_tarinfo_name',
]
