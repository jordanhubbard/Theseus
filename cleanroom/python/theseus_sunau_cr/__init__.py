"""Clean-room implementation of the Sun AU audio file module.

Implements reading and writing of Sun/NeXT .au audio files from scratch
using only the Python standard library. Does NOT import or wrap the
original `sunau` module.
"""

import builtins
import struct


# --- Constants ----------------------------------------------------------

AUDIO_UNKNOWN_SIZE = 0xFFFFFFFF  # ((unsigned)(~0))

AUDIO_FILE_MAGIC = 0x2e736e64  # ".snd"

AUDIO_FILE_ENCODING_MULAW_8 = 1
AUDIO_FILE_ENCODING_LINEAR_8 = 2
AUDIO_FILE_ENCODING_LINEAR_16 = 3
AUDIO_FILE_ENCODING_LINEAR_24 = 4
AUDIO_FILE_ENCODING_LINEAR_32 = 5
AUDIO_FILE_ENCODING_FLOAT = 6
AUDIO_FILE_ENCODING_DOUBLE = 7
AUDIO_FILE_ENCODING_ADPCM_G721 = 23
AUDIO_FILE_ENCODING_ADPCM_G722 = 24
AUDIO_FILE_ENCODING_ADPCM_G723_3 = 25
AUDIO_FILE_ENCODING_ADPCM_G723_5 = 26
AUDIO_FILE_ENCODING_ALAW_8 = 27


_AU_HEADER_SIZE = 24


# --- Error class --------------------------------------------------------

class Error(Exception):
    """Exception raised on AU format errors."""
    pass


# --- mu-law / A-law helpers --------------------------------------------

def _mulaw_to_linear(data):
    out = bytearray()
    for b in data:
        b = (~b) & 0xFF
        sign = b & 0x80
        exponent = (b >> 4) & 0x07
        mantissa = b & 0x0F
        sample = ((mantissa << 3) + 0x84) << exponent
        sample -= 0x84
        if sign:
            sample = -sample
        if sample < -32768:
            sample = -32768
        elif sample > 32767:
            sample = 32767
        out.extend(struct.pack('>h', sample))
    return bytes(out)


def _alaw_to_linear(data):
    out = bytearray()
    for b in data:
        b ^= 0x55
        sign = b & 0x80
        exponent = (b >> 4) & 0x07
        mantissa = b & 0x0F
        if exponent:
            sample = ((mantissa << 4) + 0x108) << (exponent - 1)
        else:
            sample = (mantissa << 4) + 0x8
        if sign:
            sample = -sample
        if sample < -32768:
            sample = -32768
        elif sample > 32767:
            sample = 32767
        out.extend(struct.pack('>h', sample))
    return bytes(out)


def _linear_to_mulaw(data):
    out = bytearray()
    n = len(data) - (len(data) % 2)
    for i in range(0, n, 2):
        sample = struct.unpack('>h', bytes(data[i:i + 2]))[0]
        sign = 0x80 if sample < 0 else 0
        if sample < 0:
            sample = -sample
        if sample > 32635:
            sample = 32635
        sample += 0x84
        exponent = 7
        for mask in (0x4000, 0x2000, 0x1000, 0x0800,
                     0x0400, 0x0200, 0x0100):
            if sample & mask:
                break
            exponent -= 1
        mantissa = (sample >> (exponent + 3)) & 0x0F
        byte = (~(sign | (exponent << 4) | mantissa)) & 0xFF
        out.append(byte)
    return bytes(out)


# --- Reader -------------------------------------------------------------

class Au_read:
    def __init__(self, f):
        self._opened = False
        if isinstance(f, str):
            f = builtins.open(f, 'rb')
            self._opened = True
        self._file = f
        try:
            self._read_header()
        except Exception:
            if self._opened:
                self._file.close()
            raise

    def _read_header(self):
        header = self._file.read(_AU_HEADER_SIZE)
        if len(header) < _AU_HEADER_SIZE:
            raise Error('not a sun/next audio file')
        magic, hdr_size, data_size, encoding, sample_rate, channels = \
            struct.unpack('>IIIIII', header)
        if magic != AUDIO_FILE_MAGIC:
            raise Error('bad magic number')
        self._hdr_size = hdr_size
        self._data_size = data_size
        self._encoding = encoding
        self._framerate = sample_rate
        self._nchannels = channels
        if channels <= 0:
            raise Error('bad # of channels')

        if encoding == AUDIO_FILE_ENCODING_MULAW_8:
            self._sampwidth = 2
            self._frame_in_size = channels * 1
            self._framesize = channels * 2
        elif encoding == AUDIO_FILE_ENCODING_ALAW_8:
            self._sampwidth = 2
            self._frame_in_size = channels * 1
            self._framesize = channels * 2
        elif encoding == AUDIO_FILE_ENCODING_LINEAR_8:
            self._sampwidth = 1
            self._frame_in_size = channels * 1
            self._framesize = channels * 1
        elif encoding == AUDIO_FILE_ENCODING_LINEAR_16:
            self._sampwidth = 2
            self._frame_in_size = channels * 2
            self._framesize = channels * 2
        elif encoding == AUDIO_FILE_ENCODING_LINEAR_24:
            self._sampwidth = 3
            self._frame_in_size = channels * 3
            self._framesize = channels * 3
        elif encoding == AUDIO_FILE_ENCODING_LINEAR_32:
            self._sampwidth = 4
            self._frame_in_size = channels * 4
            self._framesize = channels * 4
        else:
            raise Error('unknown encoding')

        if hdr_size > _AU_HEADER_SIZE:
            self._file.read(hdr_size - _AU_HEADER_SIZE)

        if data_size != AUDIO_UNKNOWN_SIZE:
            self._nframes = data_size // self._frame_in_size
        else:
            self._nframes = AUDIO_UNKNOWN_SIZE

    def getfp(self):
        return self._file

    def getnchannels(self):
        return self._nchannels

    def getsampwidth(self):
        return self._sampwidth

    def getframerate(self):
        return self._framerate

    def getnframes(self):
        return self._nframes

    def getcomptype(self):
        if self._encoding == AUDIO_FILE_ENCODING_MULAW_8:
            return 'ULAW'
        if self._encoding == AUDIO_FILE_ENCODING_ALAW_8:
            return 'ALAW'
        return 'NONE'

    def getcompname(self):
        ct = self.getcomptype()
        if ct == 'ULAW':
            return 'CCITT G.711 u-law'
        if ct == 'ALAW':
            return 'CCITT G.711 A-law'
        return 'not compressed'

    def getparams(self):
        return (self.getnchannels(), self.getsampwidth(),
                self.getframerate(), self.getnframes(),
                self.getcomptype(), self.getcompname())

    def getmarkers(self):
        return None

    def getmark(self, id):
        raise Error('no marks')

    def readframes(self, nframes):
        if nframes <= 0:
            return b''
        data = self._file.read(nframes * self._frame_in_size)
        if self._encoding == AUDIO_FILE_ENCODING_MULAW_8:
            data = _mulaw_to_linear(data)
        elif self._encoding == AUDIO_FILE_ENCODING_ALAW_8:
            data = _alaw_to_linear(data)
        return data

    def rewind(self):
        try:
            self._file.seek(self._hdr_size)
        except (AttributeError, OSError):
            raise Error('cannot rewind unseekable stream')

    def tell(self):
        try:
            pos = self._file.tell()
        except (AttributeError, OSError):
            raise Error('cannot tell on unseekable stream')
        return (pos - self._hdr_size) // self._frame_in_size

    def setpos(self, pos):
        if pos < 0:
            raise Error('position out of range')
        if (self._nframes != AUDIO_UNKNOWN_SIZE and pos > self._nframes):
            raise Error('position out of range')
        try:
            self._file.seek(self._hdr_size + pos * self._frame_in_size)
        except (AttributeError, OSError):
            raise Error('cannot seek on unseekable stream')

    def close(self):
        if self._file is None:
            return
        f = self._file
        self._file = None
        if self._opened:
            f.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


# --- Writer -------------------------------------------------------------

class Au_write:
    def __init__(self, f):
        self._opened = False
        if isinstance(f, str):
            f = builtins.open(f, 'wb')
            self._opened = True
        self._file = f
        self._nchannels = 0
        self._sampwidth = 0
        self._framerate = 0
        self._nframes = AUDIO_UNKNOWN_SIZE
        self._nframeswritten = 0
        self._comptype = 'NONE'
        self._compname = 'not compressed'
        self._datawritten = 0
        self._datalength = 0
        self._headerwritten = False

    def setnchannels(self, nchannels):
        if nchannels not in (1, 2, 4):
            raise Error('only 1, 2, or 4 channels supported')
        if self._headerwritten:
            raise Error('cannot change parameters after starting to write')
        self._nchannels = nchannels

    def getnchannels(self):
        if not self._nchannels:
            raise Error('number of channels not set')
        return self._nchannels

    def setsampwidth(self, sampwidth):
        if sampwidth not in (1, 2, 4):
            raise Error('bad sample width')
        if self._headerwritten:
            raise Error('cannot change parameters after starting to write')
        self._sampwidth = sampwidth

    def getsampwidth(self):
        if not self._sampwidth:
            raise Error('sample width not set')
        return self._sampwidth

    def setframerate(self, framerate):
        if framerate <= 0:
            raise Error('bad frame rate')
        if self._headerwritten:
            raise Error('cannot change parameters after starting to write')
        self._framerate = int(framerate)

    def getframerate(self):
        if not self._framerate:
            raise Error('frame rate not set')
        return self._framerate

    def setnframes(self, nframes):
        if self._headerwritten:
            raise Error('cannot change parameters after starting to write')
        if nframes < 0:
            raise Error('# of frames cannot be negative')
        self._nframes = nframes

    def getnframes(self):
        return self._nframeswritten

    def setcomptype(self, comptype, compname):
        if self._headerwritten:
            raise Error('cannot change parameters after starting to write')
        if comptype not in ('NONE', 'ULAW'):
            raise Error('unsupported compression type')
        self._comptype = comptype
        self._compname = compname

    def getcomptype(self):
        return self._comptype

    def getcompname(self):
        return self._compname

    def setparams(self, params):
        nchannels, sampwidth, framerate, nframes, comptype, compname = params
        if self._headerwritten:
            raise Error('cannot change parameters after starting to write')
        self.setnchannels(nchannels)
        self.setsampwidth(sampwidth)
        self.setframerate(framerate)
        self.setnframes(nframes)
        self.setcomptype(comptype, compname)

    def getparams(self):
        return (self.getnchannels(), self.getsampwidth(),
                self.getframerate(), self._nframes,
                self.getcomptype(), self.getcompname())

    def tell(self):
        return self._nframeswritten

    def writeframesraw(self, data):
        if not isinstance(data, (bytes, bytearray)):
            try:
                data = bytes(memoryview(data).cast('B'))
            except (TypeError, ValueError):
                data = bytes(data)
        self._ensure_header_written()
        if self._comptype == 'ULAW':
            data = _linear_to_mulaw(data)
        nframes = len(data) // self._out_frame_size
        self._file.write(data)
        self._nframeswritten += nframes
        self._datawritten += len(data)

    def writeframes(self, data):
        self.writeframesraw(data)
        if self._nframeswritten != self._datalength_frames():
            self._patchheader()

    def _datalength_frames(self):
        # Number of frames implied by the declared data length
        if self._datalength == AUDIO_UNKNOWN_SIZE:
            return AUDIO_UNKNOWN_SIZE
        return self._datalength // self._out_frame_size

    def _ensure_header_written(self):
        if not self._headerwritten:
            if not self._nchannels:
                raise Error('# channels not specified')
            if not self._sampwidth:
                raise Error('sample width not specified')
            if not self._framerate:
                raise Error('frame rate not specified')
            self._write_header()

    def _write_header(self):
        if self._comptype == 'NONE':
            if self._sampwidth == 1:
                encoding = AUDIO_FILE_ENCODING_LINEAR_8
                out_sw = 1
            elif self._sampwidth == 2:
                encoding = AUDIO_FILE_ENCODING_LINEAR_16
                out_sw = 2
            elif self._sampwidth == 4:
                encoding = AUDIO_FILE_ENCODING_LINEAR_32
                out_sw = 4
            else:
                raise Error('bad sample width')
        elif self._comptype == 'ULAW':
            encoding = AUDIO_FILE_ENCODING_MULAW_8
            out_sw = 1
        else:
            raise Error('unsupported compression type')

        self._out_frame_size = out_sw * self._nchannels

        if self._nframes == AUDIO_UNKNOWN_SIZE:
            data_size = AUDIO_UNKNOWN_SIZE
        else:
            data_size = self._nframes * self._out_frame_size
        self._datalength = data_size
        header = struct.pack(
            '>IIIIII',
            AUDIO_FILE_MAGIC,
            _AU_HEADER_SIZE,
            data_size & 0xFFFFFFFF,
            encoding,
            self._framerate,
            self._nchannels,
        )
        self._file.write(header)
        self._headerwritten = True

    def _patchheader(self):
        if not self._headerwritten:
            return
        if self._datawritten == self._datalength:
            return
        try:
            curpos = self._file.tell()
            self._file.seek(8)
            self._file.write(struct.pack('>I', self._datawritten & 0xFFFFFFFF))
            self._file.seek(curpos)
        except (AttributeError, OSError):
            # Stream not seekable; leave size as AUDIO_UNKNOWN_SIZE
            return
        self._datalength = self._datawritten

    def close(self):
        if self._file is None:
            return
        try:
            if self._headerwritten:
                self._patchheader()
        finally:
            f = self._file
            self._file = None
            if self._opened:
                f.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


# --- open / openfp ------------------------------------------------------

def open(f, mode=None):
    if mode is None:
        if hasattr(f, 'mode'):
            mode = f.mode
        else:
            mode = 'rb'
    if mode in ('r', 'rb'):
        return Au_read(f)
    if mode in ('w', 'wb'):
        return Au_write(f)
    raise Error("mode must be 'r', 'rb', 'w', or 'wb'")


openfp = open


# --- Invariant verification functions ----------------------------------

def sunau2_error():
    """Verify that the Error class is defined and is an Exception."""
    try:
        raise Error('test')
    except Error as e:
        if not isinstance(e, Exception):
            return False
        if str(e) != 'test':
            return False
    return issubclass(Error, Exception)


def sunau2_open():
    """Verify that open() and the reader/writer classes are usable."""
    if not callable(open):
        return False
    if not callable(openfp):
        return False
    if not callable(Au_read):
        return False
    if not callable(Au_write):
        return False
    # Quick round-trip exercise using an in-memory stream.
    import io
    buf = io.BytesIO()
    w = Au_write(buf)
    w.setnchannels(1)
    w.setsampwidth(2)
    w.setframerate(8000)
    w.setcomptype('NONE', 'not compressed')
    w.writeframes(b'\x00\x01\x00\x02\x00\x03\x00\x04')
    w.close()
    buf.seek(0)
    r = Au_read(buf)
    if r.getnchannels() != 1:
        return False
    if r.getsampwidth() != 2:
        return False
    if r.getframerate() != 8000:
        return False
    if r.getcomptype() != 'NONE':
        return False
    data = r.readframes(4)
    r.close()
    return data == b'\x00\x01\x00\x02\x00\x03\x00\x04'


def sunau2_constants():
    """Verify that AU constants have the expected canonical values."""
    return (
        AUDIO_FILE_MAGIC == 0x2e736e64
        and AUDIO_FILE_ENCODING_MULAW_8 == 1
        and AUDIO_FILE_ENCODING_LINEAR_8 == 2
        and AUDIO_FILE_ENCODING_LINEAR_16 == 3
        and AUDIO_FILE_ENCODING_LINEAR_24 == 4
        and AUDIO_FILE_ENCODING_LINEAR_32 == 5
        and AUDIO_FILE_ENCODING_FLOAT == 6
        and AUDIO_FILE_ENCODING_DOUBLE == 7
        and AUDIO_FILE_ENCODING_ADPCM_G721 == 23
        and AUDIO_FILE_ENCODING_ADPCM_G722 == 24
        and AUDIO_FILE_ENCODING_ADPCM_G723_3 == 25
        and AUDIO_FILE_ENCODING_ADPCM_G723_5 == 26
        and AUDIO_FILE_ENCODING_ALAW_8 == 27
        and AUDIO_UNKNOWN_SIZE == 0xFFFFFFFF
    )