"""
theseus_aifc_cr — Clean-room aifc module.
No import of the standard `aifc` module.
"""

import struct as _struct
import io as _io
import builtins as _builtins

# AIFF/AIFF-C compression type constants
NONE = b'NONE'
ULAW = b'ulaw'
ALAW = b'alaw'
G722 = b'G722'

# IFF chunk IDs
_AIFC_data = b'AIFC'
_AIFF_data = b'AIFF'
_FORM = b'FORM'
_COMM = b'COMM'
_SSND = b'SSND'
_MARK = b'MARK'
_INST = b'INST'
_MIDI = b'MIDI'
_AESD = b'AESD'
_APPL = b'APPL'
_NAME = b'NAME'
_AUTH = b'AUTH'
_COPY = b'(c) '
_ANNO = b'ANNO'
_COMT = b'COMT'
_FVER = b'FVER'


class Error(Exception):
    pass


def _read_float(f):
    """Read an 80-bit IEEE 754 extended float."""
    expon_hi, expon_lo, himant, lomant = _struct.unpack('>HHIi', f.read(10))
    sign = 1
    if expon_hi & 0x8000:
        sign = -1
        expon_hi &= 0x7FFF
    exp = expon_hi - 16383 - 63
    mantissa = (himant << 32) | (lomant & 0xffffffff)
    import math as _math
    if exp > 0:
        f_val = mantissa * (2 ** exp)
    elif exp < 0:
        f_val = mantissa / (2 ** (-exp))
    else:
        f_val = float(mantissa)
    return sign * f_val


def _write_float(f, x):
    """Write an 80-bit IEEE 754 extended float."""
    import math as _math
    if x < 0:
        sign = 0x8000
        x = -x
    else:
        sign = 0
    if x == 0:
        expon = 0
        himant = 0
        lomant = 0
    else:
        fmant, expon = _math.frexp(x)
        if expon > 16384 or fmant >= 1:
            expon = sign | 0x7FFF
            himant = 0
            lomant = 0
        else:
            expon += 16382
            fmant = _math.ldexp(fmant, 32)
            fsmant = int(fmant)
            himant = fsmant
            fmant = _math.ldexp(fmant - fsmant, 32)
            lomant = int(fmant)
    f.write(_struct.pack('>HHIi', sign | expon, 0, himant, lomant))


class Aifc_read:
    def __init__(self, f):
        if isinstance(f, (str, bytes)):
            f = _builtins.open(f, 'rb')
            self._opened = True
        else:
            self._opened = False
        self._file = f
        self._convert = None
        self._aifc = 0
        self._init_params()

    def _init_params(self):
        chunk = self._file.read(12)
        if len(chunk) < 12:
            raise Error('not an AIFF file')
        form, size, aiff = _struct.unpack('>4sI4s', chunk)
        if form != _FORM:
            raise Error('not an AIFF file')
        if aiff == _AIFC_data:
            self._aifc = 1
        elif aiff == _AIFF_data:
            self._aifc = 0
        else:
            raise Error('not an AIFF or AIFF-C file')

        self._nchannels = 0
        self._nframes = 0
        self._sampwidth = 0
        self._framerate = 0
        self._comptype = NONE
        self._compname = b'not compressed'

        # Read chunks
        while True:
            data = self._file.read(8)
            if len(data) < 8:
                break
            cid, csize = _struct.unpack('>4sI', data)
            if cid == _COMM:
                self._read_comm(csize)
            elif cid == _SSND:
                offset, blocksize = _struct.unpack('>II', self._file.read(8))
                self._ssnd_pos = self._file.tell()
                self._ssnd_seek_needed = False
                self._file.seek(csize - 8, 1)
            else:
                self._file.seek(csize, 1)
                if csize % 2:
                    self._file.read(1)

    def _read_comm(self, length):
        data = self._file.read(length)
        self._nchannels = _struct.unpack('>h', data[0:2])[0]
        self._nframes = _struct.unpack('>I', data[2:6])[0]
        self._sampwidth = (_struct.unpack('>h', data[6:8])[0] + 7) // 8
        fp = _io.BytesIO(data[8:18])
        self._framerate = int(_read_float(fp))
        if self._aifc:
            self._comptype = data[18:22]
        else:
            self._comptype = NONE

    def close(self):
        if self._opened:
            self._file.close()
        self._file = None

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
        return (self.getnchannels(), self.getsampwidth(), self.getframerate(),
                self.getnframes(), self.getcomptype(), self.getcompname())

    def readframes(self, nframes):
        if not hasattr(self, '_ssnd_pos'):
            return b''
        return self._file.read(nframes * self._sampwidth * self._nchannels)

    def rewind(self):
        if hasattr(self, '_ssnd_pos'):
            self._file.seek(self._ssnd_pos)

    def tell(self):
        return 0

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class Aifc_write:
    def __init__(self, f):
        if isinstance(f, (str, bytes)):
            f = _builtins.open(f, 'wb')
            self._opened = True
        else:
            self._opened = False
        self._file = f
        self._aifc = 0
        self._nchannels = 0
        self._sampwidth = 0
        self._framerate = 0
        self._nframes = 0
        self._nframeswritten = 0
        self._comptype = NONE
        self._compname = b'not compressed'
        self._header_written = False

    def setnchannels(self, nchannels):
        self._nchannels = nchannels

    def setsampwidth(self, sampwidth):
        self._sampwidth = sampwidth

    def setframerate(self, framerate):
        self._framerate = framerate

    def setnframes(self, nframes):
        self._nframes = nframes

    def setcomptype(self, comptype, compname):
        self._comptype = comptype
        self._compname = compname
        if comptype != NONE:
            self._aifc = 1

    def setparams(self, params):
        nchannels, sampwidth, framerate, nframes, comptype, compname = params
        self.setnchannels(nchannels)
        self.setsampwidth(sampwidth)
        self.setframerate(framerate)
        self.setnframes(nframes)
        self.setcomptype(comptype, compname)

    def _write_header(self):
        if self._header_written:
            return
        self._header_written = True
        if self._aifc:
            aiff_type = _AIFC_data
        else:
            aiff_type = _AIFF_data

        comm_size = 26 if self._aifc else 18

        # Write FORM chunk (size will be updated later)
        self._form_length_pos = 4
        self._file.write(_FORM)
        self._file.write(_struct.pack('>I', 0))
        self._file.write(aiff_type)

        # Write COMM chunk
        self._file.write(_COMM)
        self._file.write(_struct.pack('>I', comm_size))
        self._file.write(_struct.pack('>h', self._nchannels))
        self._file.write(_struct.pack('>I', self._nframes))
        self._file.write(_struct.pack('>h', self._sampwidth * 8))
        _write_float(self._file, self._framerate)
        if self._aifc:
            self._file.write(self._comptype)
            # Compression name as Pascal string
            cname = self._compname
            if isinstance(cname, str):
                cname = cname.encode('ascii')
            self._file.write(bytes([len(cname)]) + cname)
            if len(cname) % 2 == 0:
                self._file.write(b'\x00')

        # Write SSND chunk header
        self._file.write(_SSND)
        self._ssnd_length_pos = self._file.tell()
        self._file.write(_struct.pack('>I', 0))
        self._file.write(_struct.pack('>II', 0, 0))

    def writeframes(self, data):
        self._write_header()
        self._file.write(data)
        nframes = len(data) // (self._sampwidth * self._nchannels) if self._sampwidth and self._nchannels else 0
        self._nframeswritten += nframes

    def writeframesraw(self, data):
        self.writeframes(data)

    def getnframeswritten(self):
        return self._nframeswritten

    def close(self):
        self._write_header()
        if self._opened:
            self._file.close()
        self._file = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def open(f, mode=None):
    if mode is None:
        if hasattr(f, 'mode'):
            mode = f.mode
        else:
            mode = 'rb'
    if mode in ('r', 'rb'):
        return Aifc_read(f)
    elif mode in ('w', 'wb'):
        return Aifc_write(f)
    else:
        raise Error('unknown mode %r' % (mode,))


openfp = open


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def aifc2_error():
    """Error class exists; returns True."""
    return issubclass(Error, Exception)


def aifc2_open():
    """open() function exists; returns True."""
    return callable(open)


def aifc2_constants():
    """AIFC compression type constants exist; returns True."""
    return (NONE == b'NONE' and
            ULAW == b'ulaw' and
            ALAW == b'alaw')


__all__ = [
    'open', 'openfp', 'Aifc_read', 'Aifc_write', 'Error',
    'NONE', 'ULAW', 'ALAW', 'G722',
    'aifc2_error', 'aifc2_open', 'aifc2_constants',
]
