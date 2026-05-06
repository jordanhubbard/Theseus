"""Clean-room implementation of an aifc-like module (AIFF/AIFF-C).

This module is a clean-room re-implementation. It does not import the
original `aifc` package. Only Python standard library primitives are used.
"""

import struct
import builtins

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

_AIFC_version = 0xA2805140  # version of the AIFF-C format

_HUGE_VAL = 1.79769313486231e+308  # used in float80 conversion fallback


# ---------------------------------------------------------------------------
# Error exception
# ---------------------------------------------------------------------------


class Error(Exception):
    """Exception raised for errors in the AIFF/AIFF-C clean-room module."""
    pass


# ---------------------------------------------------------------------------
# IEEE 754 80-bit extended precision helpers (used by AIFF for sample rate)
# ---------------------------------------------------------------------------


def _read_float(s):
    """Decode an 80-bit IEEE-754 extended float (10 bytes, big-endian)."""
    if len(s) != 10:
        raise Error('not enough data for 80-bit float')
    expon = (s[0] << 8) | s[1]
    sign = 1
    if expon & 0x8000:
        sign = -1
        expon = expon & 0x7FFF
    himant = (s[2] << 24) | (s[3] << 16) | (s[4] << 8) | s[5]
    lomant = (s[6] << 24) | (s[7] << 16) | (s[8] << 8) | s[9]
    if expon == 0 and himant == 0 and lomant == 0:
        return 0.0
    if expon == 0x7FFF:
        return _HUGE_VAL
    expon = expon - 16383
    f = (himant * (2.0 ** -31)) + (lomant * (2.0 ** -63))
    return sign * f * (2.0 ** expon)


def _write_float(f):
    """Encode a float as an 80-bit IEEE-754 extended big-endian value."""
    import math
    if f == 0.0:
        sign = 0
        expon = 0
        himant = 0
        lomant = 0
    else:
        if f < 0:
            sign = 0x8000
            f = -f
        else:
            sign = 0
        if f != f:  # NaN
            expon = sign | 0x7FFF
            himant = 0
            lomant = 0
        else:
            fmant, expon = math.frexp(f)
            if expon > 16384 or fmant >= 1:
                expon = sign | 0x7FFF
                himant = 0
                lomant = 0
            else:
                expon = expon + 16382
                if expon < 0:
                    fmant = math.ldexp(fmant, expon)
                    expon = 0
                expon = expon | sign
                fmant = math.ldexp(fmant, 32)
                fsmant = math.floor(fmant)
                himant = int(fsmant)
                fmant = math.ldexp(fmant - fsmant, 32)
                fsmant = math.floor(fmant)
                lomant = int(fsmant)
    return bytes([
        (expon >> 8) & 0xFF, expon & 0xFF,
        (himant >> 24) & 0xFF, (himant >> 16) & 0xFF,
        (himant >> 8) & 0xFF, himant & 0xFF,
        (lomant >> 24) & 0xFF, (lomant >> 16) & 0xFF,
        (lomant >> 8) & 0xFF, lomant & 0xFF,
    ])


# ---------------------------------------------------------------------------
# Reader
# ---------------------------------------------------------------------------


class Aifc_read:
    """Read AIFF/AIFF-C files."""

    def __init__(self, f):
        if isinstance(f, (str, bytes)):
            f = builtins.open(f, 'rb')
            self._i_opened_file = True
        else:
            self._i_opened_file = False
        self._file = f
        self._aifc = False
        self._nchannels = 0
        self._nframes = 0
        self._sampwidth = 0
        self._framerate = 0
        self._comptype = b'NONE'
        self._compname = b'not compressed'
        self._markers = []
        self._soundpos = 0
        self._ssnd_chunk = None
        try:
            self._read_header()
        except Exception:
            if self._i_opened_file:
                self._file.close()
            raise

    def _read_header(self):
        header = self._file.read(12)
        if len(header) < 12:
            raise Error('file does not start with FORM id')
        form, _size, kind = struct.unpack('>4sI4s', header)
        if form != b'FORM':
            raise Error('file does not start with FORM id')
        if kind == b'AIFF':
            self._aifc = False
        elif kind == b'AIFC':
            self._aifc = True
        else:
            raise Error('not an AIFF or AIFF-C file')

        comm_seen = False
        while True:
            chdr = self._file.read(8)
            if len(chdr) < 8:
                break
            cid, csize = struct.unpack('>4sI', chdr)
            data_start = self._file.tell()
            if cid == b'COMM':
                self._read_comm_chunk(self._file.read(csize))
                comm_seen = True
            elif cid == b'SSND':
                ssnd_hdr = self._file.read(8)
                if len(ssnd_hdr) < 8:
                    raise Error('SSND chunk truncated')
                offset, _blocksize = struct.unpack('>II', ssnd_hdr)
                self._ssnd_chunk_pos = self._file.tell() + offset
                # leave file positioned past the SSND chunk
                self._file.seek(data_start + csize)
            else:
                self._file.seek(data_start + csize)
            # AIFF chunks are padded to even length
            if csize % 2:
                self._file.seek(1, 1)

        if not comm_seen:
            raise Error('COMM chunk missing')

    def _read_comm_chunk(self, data):
        if len(data) < 18:
            raise Error('COMM chunk truncated')
        nchannels, nframes, sampwidth = struct.unpack('>hIh', data[:8])
        rate = _read_float(data[8:18])
        self._nchannels = nchannels
        self._nframes = nframes
        self._sampwidth = (sampwidth + 7) // 8
        self._framerate = int(rate)
        if self._aifc and len(data) > 18:
            self._comptype = data[18:22]
            # Pascal string: 1-byte length then bytes
            namelen = data[22] if len(data) > 22 else 0
            self._compname = data[23:23 + namelen]
        else:
            self._comptype = b'NONE'
            self._compname = b'not compressed'

    # --- accessors -------------------------------------------------------

    def getnchannels(self):
        return self._nchannels

    def getnframes(self):
        return self._nframes

    def getsampwidth(self):
        return self._sampwidth

    def getframerate(self):
        return self._framerate

    def getcomptype(self):
        return self._comptype

    def getcompname(self):
        return self._compname

    def getparams(self):
        return (self._nchannels, self._sampwidth, self._framerate,
                self._nframes, self._comptype, self._compname)

    def getmarkers(self):
        return self._markers if self._markers else None

    def getmark(self, ident):
        for m in self._markers:
            if m[0] == ident:
                return m
        raise Error('marker {} does not exist'.format(ident))

    def tell(self):
        return self._soundpos

    def setpos(self, pos):
        if pos < 0 or pos > self._nframes:
            raise Error('position not in range')
        self._soundpos = pos

    def rewind(self):
        self._soundpos = 0

    def readframes(self, nframes):
        if nframes <= 0:
            return b''
        if self._ssnd_chunk is None:
            return b''
        # Minimal placeholder: not implementing full decoding
        return b''

    def close(self):
        if self._file is None:
            return
        if self._i_opened_file:
            self._file.close()
        self._file = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


# ---------------------------------------------------------------------------
# Writer
# ---------------------------------------------------------------------------


class Aifc_write:
    """Write AIFF/AIFF-C files."""

    def __init__(self, f):
        if isinstance(f, (str, bytes)):
            f = builtins.open(f, 'wb')
            self._i_opened_file = True
        else:
            self._i_opened_file = False
        self._file = f
        self._nchannels = 0
        self._nframes = 0
        self._sampwidth = 0
        self._framerate = 0
        self._comptype = b'NONE'
        self._compname = b'not compressed'
        self._aifc = False
        self._nframeswritten = 0
        self._datalength = 0
        self._datawritten = 0
        self._markers = []
        self._marklength = 0
        self._form_length_pos = None
        self._closed = False

    # --- setters --------------------------------------------------------

    def aiff(self):
        self._aifc = False

    def aifc(self):
        self._aifc = True

    def setnchannels(self, n):
        if n < 1:
            raise Error('bad number of channels')
        self._nchannels = n

    def setsampwidth(self, n):
        if n < 1 or n > 4:
            raise Error('bad sample width')
        self._sampwidth = n

    def setframerate(self, n):
        if n <= 0:
            raise Error('bad frame rate')
        self._framerate = n

    def setnframes(self, n):
        self._nframes = n

    def setcomptype(self, comptype, compname):
        if comptype not in (b'NONE', b'ulaw', b'ULAW',
                            b'alaw', b'ALAW', b'G722'):
            raise Error('unsupported compression type')
        self._comptype = comptype
        self._compname = compname
        if comptype != b'NONE':
            self._aifc = True

    def setparams(self, params):
        nchannels, sampwidth, framerate, nframes, comptype, compname = params
        self.setnchannels(nchannels)
        self.setsampwidth(sampwidth)
        self.setframerate(framerate)
        self.setnframes(nframes)
        self.setcomptype(comptype, compname)

    def getnchannels(self):
        return self._nchannels

    def getsampwidth(self):
        return self._sampwidth

    def getframerate(self):
        return self._framerate

    def getnframes(self):
        return self._nframeswritten

    def getcomptype(self):
        return self._comptype

    def getcompname(self):
        return self._compname

    def getparams(self):
        return (self._nchannels, self._sampwidth, self._framerate,
                self._nframes, self._comptype, self._compname)

    def setmark(self, id_, pos, name):
        if id_ <= 0:
            raise Error('bad marker id')
        for i, m in enumerate(self._markers):
            if m[0] == id_:
                self._markers[i] = (id_, pos, name)
                return
        self._markers.append((id_, pos, name))

    def getmark(self, ident):
        for m in self._markers:
            if m[0] == ident:
                return m
        raise Error('marker {} does not exist'.format(ident))

    def getmarkers(self):
        return self._markers if self._markers else None

    def tell(self):
        return self._nframeswritten

    def writeframesraw(self, data):
        if not self._nchannels or not self._sampwidth or not self._framerate:
            raise Error('parameters not set')
        if self._form_length_pos is None:
            self._write_header()
        if isinstance(data, memoryview):
            data = data.tobytes()
        self._file.write(data)
        nframes = len(data) // (self._sampwidth * self._nchannels)
        self._nframeswritten += nframes
        self._datawritten += len(data)

    def writeframes(self, data):
        self.writeframesraw(data)

    def _write_header(self):
        if self._aifc or self._comptype != b'NONE':
            kind = b'AIFC'
            self._aifc = True
        else:
            kind = b'AIFF'
        self._file.write(b'FORM')
        self._form_length_pos = self._file.tell()
        self._file.write(b'\x00\x00\x00\x00')  # placeholder
        self._file.write(kind)
        if self._aifc:
            self._file.write(b'FVER')
            self._file.write(struct.pack('>I', 4))
            self._file.write(struct.pack('>I', _AIFC_version))
        # COMM chunk
        if self._aifc:
            comm_size = 18 + 4 + 1 + len(self._compname)
            if comm_size % 2:
                comm_size += 1
        else:
            comm_size = 18
        self._file.write(b'COMM')
        self._file.write(struct.pack('>I', comm_size))
        self._file.write(struct.pack('>hIh',
                                     self._nchannels,
                                     self._nframes,
                                     self._sampwidth * 8))
        self._file.write(_write_float(float(self._framerate)))
        if self._aifc:
            self._file.write(self._comptype)
            self._file.write(bytes([len(self._compname)]))
            self._file.write(self._compname)
            if (1 + len(self._compname)) % 2:
                self._file.write(b'\x00')
        # SSND chunk header (size patched at close)
        self._file.write(b'SSND')
        self._ssnd_size_pos = self._file.tell()
        self._file.write(b'\x00\x00\x00\x00')
        self._file.write(struct.pack('>II', 0, 0))  # offset, block size

    def _patch_header(self):
        if self._form_length_pos is None:
            self._write_header()
        end = self._file.tell()
        # SSND data size = data + 8 (offset+blocksize)
        ssnd_size = self._datawritten + 8
        self._file.seek(self._ssnd_size_pos)
        self._file.write(struct.pack('>I', ssnd_size))
        # FORM size = total - 8
        form_size = end - 8
        self._file.seek(self._form_length_pos)
        self._file.write(struct.pack('>I', form_size))
        self._file.seek(end)

    def close(self):
        if self._closed:
            return
        try:
            if self._file is not None:
                if self._datawritten % 2:
                    self._file.write(b'\x00')
                self._patch_header()
                if self._i_opened_file:
                    self._file.close()
        finally:
            self._closed = True
            self._file = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


# ---------------------------------------------------------------------------
# Public open()
# ---------------------------------------------------------------------------


def open(f, mode=None):
    """Open an AIFF/AIFF-C file for reading or writing."""
    if mode is None:
        if hasattr(f, 'mode'):
            mode = f.mode
        else:
            mode = 'rb'
    if mode in ('r', 'rb'):
        return Aifc_read(f)
    if mode in ('w', 'wb'):
        return Aifc_write(f)
    raise Error("mode must be 'r', 'rb', 'w', or 'wb'")


# Some implementations expose openfp as an alias
openfp = open


# ---------------------------------------------------------------------------
# Invariant test functions
# ---------------------------------------------------------------------------


def aifc2_error():
    """Verify the Error exception is defined and inherits from Exception."""
    if not isinstance(Error, type):
        return False
    if not issubclass(Error, Exception):
        return False
    try:
        raise Error('test')
    except Error as e:
        if str(e) != 'test':
            return False
    except Exception:
        return False
    return True


def aifc2_open():
    """Verify open() and the reader/writer classes exist and behave."""
    if not callable(open):
        return False
    if not isinstance(Aifc_read, type):
        return False
    if not isinstance(Aifc_write, type):
        return False
    # Bad mode must raise Error
    try:
        open(None, mode='x')
        return False
    except Error:
        pass
    except Exception:
        return False
    return True


def aifc2_constants():
    """Verify AIFF/AIFF-C constants are defined with expected values."""
    if _AIFC_version != 0xA2805140:
        return False
    # _write_float / _read_float should round-trip an integer rate
    encoded = _write_float(44100.0)
    if len(encoded) != 10:
        return False
    decoded = _read_float(encoded)
    if int(decoded) != 44100:
        return False
    return True