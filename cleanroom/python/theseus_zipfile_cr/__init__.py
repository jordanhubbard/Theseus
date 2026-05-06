"""Clean-room implementation of a minimal ZIP file reader/writer.

Implements the subset of ZIP format needed to satisfy the invariants:
  - Local file headers
  - Central directory headers
  - End-of-central-directory (EOCD) record
  - STORED and DEFLATED compression methods

Does NOT import the original `zipfile` module.
"""

import struct
import zlib
import io
import os


# Compression methods
ZIP_STORED = 0
ZIP_DEFLATED = 8

# Signatures
_LFH_SIG = 0x04034B50   # b'PK\x03\x04'
_CDH_SIG = 0x02014B50   # b'PK\x01\x02'
_EOCD_SIG = 0x06054B50  # b'PK\x05\x06'

_EOCD_MAX = 22 + 0xFFFF  # max possible EOCD position from EOF


class ZipInfo:
    """Description of a single archive member."""

    def __init__(self, filename='', date_time=(1980, 1, 1, 0, 0, 0)):
        self.filename = filename
        self.date_time = date_time
        self.compress_type = ZIP_STORED
        self.CRC = 0
        self.compress_size = 0
        self.file_size = 0
        self.header_offset = 0
        self.flag_bits = 0
        self.create_version = 20
        self.extract_version = 20
        self.external_attr = 0
        self.internal_attr = 0
        self.extra = b''
        self.comment = b''


def _dos_time(dt):
    """Convert a (year,month,day,hour,minute,second) tuple to DOS time/date."""
    year, month, day, hour, minute, second = dt
    if year < 1980:
        year = 1980
    dos_date = ((year - 1980) << 9) | (month << 5) | day
    dos_time = (hour << 11) | (minute << 5) | (second // 2)
    return dos_time & 0xFFFF, dos_date & 0xFFFF


class ZipFile:
    """A ZIP archive opened for reading, writing, or appending."""

    def __init__(self, file, mode='r'):
        if mode not in ('r', 'w', 'a'):
            raise ValueError("ZipFile requires mode 'r', 'w', or 'a'")
        self.mode = mode
        self.filename = None
        self._owns_fp = False
        self._closed = False

        if isinstance(file, (str, bytes)):
            self.filename = file
            if mode == 'r':
                self.fp = open(file, 'rb')
            elif mode == 'w':
                self.fp = open(file, 'w+b')
            else:  # 'a'
                if os.path.exists(file):
                    self.fp = open(file, 'r+b')
                else:
                    self.fp = open(file, 'w+b')
            self._owns_fp = True
        else:
            self.fp = file
            self._owns_fp = False

        self.infos = []
        self.NameToInfo = {}
        self._start_dir = 0  # where central directory should be written

        if mode == 'r':
            self._read_central_directory()
        elif mode == 'a':
            # Try to read existing central directory; if file is empty, start fresh
            try:
                self.fp.seek(0, 2)
                size = self.fp.tell()
            except Exception:
                size = 0
            if size > 0:
                try:
                    self._read_central_directory()
                    # Position to overwrite existing central directory
                    self.fp.seek(self._start_dir)
                except Exception:
                    self.fp.seek(0, 2)
                    self._start_dir = self.fp.tell()
            else:
                self._start_dir = 0
                self.fp.seek(0)
        else:  # 'w'
            try:
                self.fp.seek(0)
            except Exception:
                pass
            self._start_dir = 0

    # ------------------------------------------------------------------
    # Reading
    # ------------------------------------------------------------------

    def _read_central_directory(self):
        """Locate the EOCD, then walk the central directory."""
        self.fp.seek(0, 2)
        filesize = self.fp.tell()
        if filesize < 22:
            raise ValueError("File too small to be a ZIP archive")

        # Search the last 64KB+22 bytes for the EOCD signature
        max_back = min(_EOCD_MAX, filesize)
        self.fp.seek(filesize - max_back)
        tail = self.fp.read(max_back)
        idx = tail.rfind(b'PK\x05\x06')
        if idx < 0:
            raise ValueError("Not a valid ZIP file: EOCD not found")

        eocd = tail[idx:idx + 22]
        if len(eocd) < 22:
            raise ValueError("Truncated EOCD record")
        (sig, _disk, _cd_disk, _cd_num_disk, cd_total,
         cd_size, cd_offset, _comment_len) = struct.unpack('<IHHHHIIH', eocd)

        self._start_dir = cd_offset
        self.fp.seek(cd_offset)

        for _ in range(cd_total):
            sig_bytes = self.fp.read(4)
            if sig_bytes != b'PK\x01\x02':
                raise ValueError("Bad central directory header signature")
            cd_fixed = self.fp.read(42)
            if len(cd_fixed) < 42:
                raise ValueError("Truncated central directory header")
            (version_made, version_needed, flag_bits, compress_type,
             mod_time, mod_date, crc, compress_size, file_size,
             name_len, extra_len, comment_len, disk_start,
             internal_attr, external_attr,
             local_offset) = struct.unpack('<HHHHHHIIIHHHHHII', cd_fixed)

            name_bytes = self.fp.read(name_len)
            extra = self.fp.read(extra_len)
            comment = self.fp.read(comment_len)
            try:
                name = name_bytes.decode('utf-8')
            except UnicodeDecodeError:
                name = name_bytes.decode('latin-1')

            info = ZipInfo(name)
            info.create_version = version_made
            info.extract_version = version_needed
            info.flag_bits = flag_bits
            info.compress_type = compress_type
            info.CRC = crc
            info.compress_size = compress_size
            info.file_size = file_size
            info.header_offset = local_offset
            info.internal_attr = internal_attr
            info.external_attr = external_attr
            info.extra = extra
            info.comment = comment

            # Decode DOS time/date
            year = ((mod_date >> 9) & 0x7F) + 1980
            month = (mod_date >> 5) & 0x0F
            day = mod_date & 0x1F
            hour = (mod_time >> 11) & 0x1F
            minute = (mod_time >> 5) & 0x3F
            second = (mod_time & 0x1F) * 2
            info.date_time = (year, month, day, hour, minute, second)

            self.infos.append(info)
            self.NameToInfo[name] = info

    def namelist(self):
        return [info.filename for info in self.infos]

    def infolist(self):
        return list(self.infos)

    def getinfo(self, name):
        if name not in self.NameToInfo:
            raise KeyError("There is no item named %r in the archive" % (name,))
        return self.NameToInfo[name]

    def read(self, name):
        """Return the bytes content of `name` from the archive."""
        if isinstance(name, ZipInfo):
            info = name
        else:
            info = self.NameToInfo[name]

        self.fp.seek(info.header_offset)
        sig_bytes = self.fp.read(4)
        if sig_bytes != b'PK\x03\x04':
            raise ValueError("Bad local file header signature for %r" % info.filename)
        local_fixed = self.fp.read(26)
        if len(local_fixed) < 26:
            raise ValueError("Truncated local file header")
        (version, flag_bits, compress_type, mod_time, mod_date,
         crc, compress_size, file_size,
         name_len, extra_len) = struct.unpack('<HHHHHIIIHH', local_fixed)
        # Skip name and extra in local header — we already trust the central directory
        self.fp.read(name_len)
        self.fp.read(extra_len)

        # Use central-directory sizes (more authoritative)
        c_size = info.compress_size
        raw = self.fp.read(c_size)
        if len(raw) < c_size:
            raise ValueError("Truncated compressed data for %r" % info.filename)

        if info.compress_type == ZIP_STORED:
            data = raw
        elif info.compress_type == ZIP_DEFLATED:
            # raw deflate stream (no zlib header), so use wbits=-15
            data = zlib.decompress(raw, -15)
        else:
            raise ValueError("Unsupported compression method %d" % info.compress_type)

        # Verify CRC
        if (zlib.crc32(data) & 0xFFFFFFFF) != (info.CRC & 0xFFFFFFFF):
            raise ValueError("Bad CRC-32 for file %r" % info.filename)
        return data

    # ------------------------------------------------------------------
    # Writing
    # ------------------------------------------------------------------

    def writestr(self, zinfo_or_name, data):
        """Write a string/bytes payload as an archive member."""
        if self.mode not in ('w', 'a'):
            raise RuntimeError("write() requires mode 'w' or 'a'")

        if isinstance(zinfo_or_name, ZipInfo):
            info = zinfo_or_name
        else:
            info = ZipInfo(zinfo_or_name)
            info.compress_type = ZIP_DEFLATED

        if isinstance(data, str):
            data = data.encode('utf-8')
        elif not isinstance(data, (bytes, bytearray)):
            raise TypeError("data must be bytes, bytearray, or str")
        data = bytes(data)

        info.file_size = len(data)
        info.CRC = zlib.crc32(data) & 0xFFFFFFFF

        if info.compress_type == ZIP_DEFLATED:
            compressor = zlib.compressobj(zlib.Z_DEFAULT_COMPRESSION, zlib.DEFLATED, -15)
            compressed = compressor.compress(data) + compressor.flush()
        elif info.compress_type == ZIP_STORED:
            compressed = data
        else:
            raise ValueError("Unsupported compression method %d" % info.compress_type)

        info.compress_size = len(compressed)

        # Position pointer at insertion point: end of last record (or start_dir)
        self.fp.seek(self._start_dir)
        info.header_offset = self.fp.tell()

        name_bytes = info.filename.encode('utf-8')
        dos_time, dos_date = _dos_time(info.date_time)
        local_header = struct.pack(
            '<IHHHHHIIIHH',
            _LFH_SIG,
            info.extract_version,
            info.flag_bits,
            info.compress_type,
            dos_time, dos_date,
            info.CRC,
            info.compress_size,
            info.file_size,
            len(name_bytes),
            0,  # extra length
        )
        self.fp.write(local_header)
        self.fp.write(name_bytes)
        self.fp.write(compressed)

        self._start_dir = self.fp.tell()
        self.infos.append(info)
        self.NameToInfo[info.filename] = info

    def write(self, filename, arcname=None):
        """Add the file at `filename` to the archive under name `arcname`."""
        if self.mode not in ('w', 'a'):
            raise RuntimeError("write() requires mode 'w' or 'a'")
        if arcname is None:
            arcname = os.path.basename(filename)
        with open(filename, 'rb') as f:
            data = f.read()
        info = ZipInfo(arcname)
        info.compress_type = ZIP_DEFLATED
        self.writestr(info, data)

    def _write_central_directory(self):
        """Write central directory headers and the EOCD record."""
        self.fp.seek(self._start_dir)
        cd_offset = self.fp.tell()

        for info in self.infos:
            name_bytes = info.filename.encode('utf-8')
            dos_time, dos_date = _dos_time(info.date_time)
            cd_header = struct.pack(
                '<IHHHHHHIIIHHHHHII',
                _CDH_SIG,
                info.create_version,
                info.extract_version,
                info.flag_bits,
                info.compress_type,
                dos_time, dos_date,
                info.CRC,
                info.compress_size,
                info.file_size,
                len(name_bytes),
                0,    # extra len
                0,    # comment len
                0,    # disk number start
                info.internal_attr,
                info.external_attr,
                info.header_offset,
            )
            self.fp.write(cd_header)
            self.fp.write(name_bytes)

        cd_end = self.fp.tell()
        cd_size = cd_end - cd_offset

        eocd = struct.pack(
            '<IHHHHIIH',
            _EOCD_SIG,
            0, 0,
            len(self.infos),
            len(self.infos),
            cd_size,
            cd_offset,
            0,  # comment length
        )
        self.fp.write(eocd)

        # Truncate file in case we shortened an existing archive (mode 'a')
        try:
            self.fp.truncate()
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def close(self):
        if self._closed:
            return
        try:
            if self.mode in ('w', 'a'):
                self._write_central_directory()
        finally:
            self._closed = True
            if self._owns_fp:
                try:
                    self.fp.close()
                except Exception:
                    pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass


# ----------------------------------------------------------------------
# Module-level helpers
# ----------------------------------------------------------------------

def _check_eocd(fp):
    """Return True if `fp` (already open binary) appears to contain an EOCD."""
    try:
        fp.seek(0, 2)
        size = fp.tell()
        if size < 22:
            return False
        max_back = min(_EOCD_MAX, size)
        fp.seek(size - max_back)
        tail = fp.read(max_back)
        idx = tail.rfind(b'PK\x05\x06')
        if idx < 0:
            return False
        # Make sure remaining bytes can hold the fixed EOCD record
        if len(tail) - idx < 22:
            return False
        return True
    except Exception:
        return False


def is_zipfile(filename_or_file):
    """Return True if the argument names a file or is a file-like ZIP archive."""
    try:
        if isinstance(filename_or_file, (str, bytes)):
            try:
                with open(filename_or_file, 'rb') as f:
                    return _check_eocd(f)
            except OSError:
                return False
        else:
            fp = filename_or_file
            try:
                pos = fp.tell()
            except Exception:
                pos = None
            try:
                result = _check_eocd(fp)
            finally:
                if pos is not None:
                    try:
                        fp.seek(pos)
                    except Exception:
                        pass
            return result
    except Exception:
        return False


# ----------------------------------------------------------------------
# Invariant checks
# ----------------------------------------------------------------------

def zipfile2_write_read():
    """Round-trip a single member and return its decoded text."""
    buf = io.BytesIO()
    with ZipFile(buf, 'w') as zf:
        zf.writestr('greeting.txt', 'hello')
    buf.seek(0)
    with ZipFile(buf, 'r') as zf:
        return zf.read('greeting.txt').decode('utf-8')


def zipfile2_namelist():
    """Write two members and return the namelist length."""
    buf = io.BytesIO()
    with ZipFile(buf, 'w') as zf:
        zf.writestr('a.txt', b'alpha')
        zf.writestr('b.txt', b'beta')
    buf.seek(0)
    with ZipFile(buf, 'r') as zf:
        return len(zf.namelist())


def zipfile2_is_zipfile():
    """Verify that a freshly written archive is recognized as a ZIP."""
    buf = io.BytesIO()
    with ZipFile(buf, 'w') as zf:
        zf.writestr('x.txt', b'data')
    buf.seek(0)
    return is_zipfile(buf)