"""
theseus_zipfile_cr — Clean-room ZIP file reader/writer.
No import of the standard `zipfile` module.
"""

import io
import os
import struct
import zlib
import time


# ZIP format constants
_LOCAL_FILE_HEADER_SIG = b'PK\x03\x04'
_CENTRAL_DIR_SIG = b'PK\x01\x02'
_END_OF_CENTRAL_DIR_SIG = b'PK\x05\x06'

ZIP_STORED = 0
ZIP_DEFLATED = 8


def _dos_time(t=None):
    """Return (date, time) as DOS-format integers."""
    if t is None:
        t = time.localtime()
    dosdate = (t[0] - 1980) << 9 | t[1] << 5 | t[2]
    dostime = t[3] << 11 | t[4] << 5 | (t[5] // 2)
    return dosdate, dostime


class ZipInfo:
    """Information about a member of a ZIP archive."""

    def __init__(self, filename, date_time=None):
        self.filename = filename
        if date_time is None:
            date_time = time.localtime()[:6]
        self.date_time = date_time
        self.compress_type = ZIP_STORED
        self.compress_size = 0
        self.file_size = 0
        self.CRC = 0
        self.header_offset = 0
        self.external_attr = 0
        self.internal_attr = 0
        self.extra = b''
        self.comment = b''
        self.flag_bits = 0

    def _raw_time(self):
        dosdate, dostime = _dos_time(self.date_time)
        return dosdate, dostime


class ZipFile:
    """ZIP archive reader/writer."""

    def __init__(self, file, mode='r', compression=ZIP_STORED):
        self._mode = mode
        self._compression = compression
        self._filelist = []
        self._NameToInfo = {}

        if isinstance(file, (str, bytes, os.PathLike)):
            if mode == 'r':
                self._fileobj = open(file, 'rb')
            elif mode in ('w', 'x'):
                self._fileobj = open(file, 'w+b')
            elif mode == 'a':
                self._fileobj = open(file, 'r+b')
            else:
                raise ValueError(f"ZipFile requires mode 'r', 'w', 'x', or 'a'")
            self._close_fileobj = True
        elif hasattr(file, 'read') or hasattr(file, 'write'):
            self._fileobj = file
            self._close_fileobj = False
        else:
            raise TypeError("file must be a path or file-like object")

        if mode == 'r':
            self._read_central_directory()
        elif mode in ('w', 'x'):
            self._fileobj.seek(0)

    def _read_central_directory(self):
        """Parse ZIP central directory."""
        f = self._fileobj
        f.seek(0, 2)
        filesize = f.tell()

        # Find end-of-central-directory record
        # It starts with PK\x05\x06 and is at least 22 bytes
        eocd_offset = -1
        for search_size in range(22, min(66000, filesize + 1)):
            f.seek(filesize - search_size)
            data = f.read(search_size)
            idx = data.rfind(_END_OF_CENTRAL_DIR_SIG)
            if idx != -1:
                eocd_offset = filesize - search_size + idx
                break

        if eocd_offset == -1:
            return  # empty or invalid

        f.seek(eocd_offset)
        eocd = f.read(22)
        if len(eocd) < 22:
            return
        (sig, disk_num, start_disk, num_entries_this, num_entries,
         cd_size, cd_offset, comment_len) = struct.unpack('<4sHHHHIIH', eocd)

        f.seek(cd_offset)
        for _ in range(num_entries):
            sig = f.read(4)
            if sig != _CENTRAL_DIR_SIG:
                break
            data = f.read(42)
            (version_made, version_needed, flag_bits, compress_type,
             mod_time, mod_date, crc32, compress_size, file_size,
             fname_len, extra_len, comment_len2, disk_start,
             internal_attr, external_attr, local_offset) = struct.unpack('<HHHHHIIIHHHHHHII', data)
            fname = f.read(fname_len).decode('utf-8', errors='replace')
            f.read(extra_len)
            f.read(comment_len2)

            info = ZipInfo(fname)
            info.compress_type = compress_type
            info.compress_size = compress_size
            info.file_size = file_size
            info.CRC = crc32
            info.header_offset = local_offset
            info.flag_bits = flag_bits
            self._filelist.append(info)
            self._NameToInfo[fname] = info

    def namelist(self):
        """Return list of archive member names."""
        return [info.filename for info in self._filelist]

    def infolist(self):
        """Return list of ZipInfo instances."""
        return list(self._filelist)

    def getinfo(self, name):
        """Return ZipInfo for the named member."""
        try:
            return self._NameToInfo[name]
        except KeyError:
            raise KeyError(f"There is no item named {name!r} in the archive")

    def read(self, name):
        """Return bytes of the named archive member."""
        info = self.getinfo(name) if isinstance(name, str) else name
        f = self._fileobj
        f.seek(info.header_offset)
        sig = f.read(4)
        if sig != _LOCAL_FILE_HEADER_SIG:
            raise BadZipFile("Bad magic number for file header")
        header = f.read(26)
        (version, flag_bits, compress_type, mod_time, mod_date,
         crc32, compress_size, file_size, fname_len, extra_len) = struct.unpack('<HHHHHIIIHH', header[:26])
        f.read(fname_len)
        f.read(extra_len)
        raw = f.read(compress_size)
        if compress_type == ZIP_DEFLATED:
            return zlib.decompress(raw, -15)
        return raw

    def writestr(self, zinfo_or_arcname, data):
        """Write bytes data into the archive."""
        if isinstance(data, str):
            data = data.encode('utf-8')
        if isinstance(zinfo_or_arcname, str):
            zinfo = ZipInfo(zinfo_or_arcname)
            zinfo.compress_type = self._compression
        else:
            zinfo = zinfo_or_arcname

        zinfo.file_size = len(data)
        zinfo.CRC = zlib.crc32(data) & 0xFFFFFFFF

        if zinfo.compress_type == ZIP_DEFLATED:
            compressed = zlib.compress(data, 6)[2:-4]
        else:
            compressed = data
        zinfo.compress_size = len(compressed)

        zinfo.header_offset = self._fileobj.seek(0, 1)
        fname_bytes = zinfo.filename.encode('utf-8')
        dosdate, dostime = zinfo._raw_time()
        local_header = struct.pack(
            '<4sHHHHHIIIHH',
            _LOCAL_FILE_HEADER_SIG,
            20,              # version needed
            0,               # flag bits
            zinfo.compress_type,
            dostime,
            dosdate,
            zinfo.CRC,
            zinfo.compress_size,
            zinfo.file_size,
            len(fname_bytes),
            0,               # extra field length
        )
        self._fileobj.write(local_header)
        self._fileobj.write(fname_bytes)
        self._fileobj.write(compressed)

        self._filelist.append(zinfo)
        self._NameToInfo[zinfo.filename] = zinfo

    def write(self, filename, arcname=None):
        """Write a file into the archive."""
        if arcname is None:
            arcname = os.path.basename(filename)
        with open(filename, 'rb') as f:
            data = f.read()
        self.writestr(arcname, data)

    def close(self):
        """Write central directory and close."""
        if self._mode in ('w', 'x', 'a'):
            cd_offset = self._fileobj.seek(0, 1)
            for info in self._filelist:
                fname_bytes = info.filename.encode('utf-8')
                dosdate, dostime = info._raw_time()
                cd_entry = struct.pack(
                    '<4sHHHHHHIIIHHHHHII',
                    _CENTRAL_DIR_SIG,
                    20,                   # version made by
                    20,                   # version needed
                    info.flag_bits,
                    info.compress_type,
                    dostime,
                    dosdate,
                    info.CRC,
                    info.compress_size,
                    info.file_size,
                    len(fname_bytes),
                    0,                    # extra len
                    0,                    # comment len
                    0,                    # disk start
                    info.internal_attr,
                    info.external_attr,
                    info.header_offset,
                )
                self._fileobj.write(cd_entry)
                self._fileobj.write(fname_bytes)

            cd_end = self._fileobj.seek(0, 1)
            cd_size = cd_end - cd_offset
            eocd = struct.pack(
                '<4sHHHHIIH',
                _END_OF_CENTRAL_DIR_SIG,
                0,                    # disk number
                0,                    # disk with cd
                len(self._filelist),
                len(self._filelist),
                cd_size,
                cd_offset,
                0,                    # comment len
            )
            self._fileobj.write(eocd)

        if self._close_fileobj:
            self._fileobj.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False


class BadZipFile(Exception):
    pass


def is_zipfile(filename):
    """Return True if filename (path or file-like) is a valid ZIP file."""
    try:
        if isinstance(filename, (str, bytes, os.PathLike)):
            with open(filename, 'rb') as f:
                sig = f.read(4)
        else:
            pos = filename.tell()
            sig = filename.read(4)
            filename.seek(pos)
        return sig == _LOCAL_FILE_HEADER_SIG
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def zipfile2_write_read():
    """Write bytes to in-memory zip, read back; returns the decoded string."""
    buf = io.BytesIO()
    with ZipFile(buf, 'w') as zf:
        zf.writestr('test.txt', b'hello')
    buf.seek(0)
    with ZipFile(buf, 'r') as zf:
        return zf.read('test.txt').decode('utf-8')


def zipfile2_namelist():
    """Write 2 entries; namelist() has length 2; returns 2."""
    buf = io.BytesIO()
    with ZipFile(buf, 'w') as zf:
        zf.writestr('a.txt', b'aaa')
        zf.writestr('b.txt', b'bbb')
    buf.seek(0)
    with ZipFile(buf, 'r') as zf:
        return len(zf.namelist())


def zipfile2_is_zipfile():
    """is_zipfile on in-memory zip returns True."""
    buf = io.BytesIO()
    with ZipFile(buf, 'w') as zf:
        zf.writestr('x.txt', b'x')
    buf.seek(0)
    return is_zipfile(buf)


__all__ = [
    'ZipFile', 'ZipInfo', 'BadZipFile', 'is_zipfile',
    'ZIP_STORED', 'ZIP_DEFLATED',
    'zipfile2_write_read', 'zipfile2_namelist', 'zipfile2_is_zipfile',
]
