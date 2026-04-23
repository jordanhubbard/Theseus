"""
theseus_sunau_cr — Clean-room sunau module.
No import of the standard `sunau` module.
"""

import struct as _struct
import io as _io

_SUNAU_MAGIC = 0x2e736e64  # .snd
AUDIO_FILE_MAGIC = _SUNAU_MAGIC
AU_HEADER_SIZE = 24

# Encoding types
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

_UNKNOWN_SIZE = 0xFFFFFFFF


class Error(Exception):
    pass


class Au_read:
    def __init__(self, f):
        if isinstance(f, str):
            f = open(f, 'rb')
            self._opened = True
        else:
            self._opened = False
        self._file = f
        self._init_params()

    def _init_params(self):
        header = self._file.read(AU_HEADER_SIZE)
        if len(header) < AU_HEADER_SIZE:
            raise Error('not a Sun AU file')
        magic, offset, nframes, encoding, rate, nchannels = _struct.unpack(
            '>IIIIII', header
        )
        if magic != _SUNAU_MAGIC:
            raise Error('bad magic number')
        self._offset = offset
        self._nframes = nframes if nframes != _UNKNOWN_SIZE else -1
        self._encoding = encoding
        self._rate = rate
        self._nchannels = nchannels
        # Skip to data
        if offset > AU_HEADER_SIZE:
            self._file.read(offset - AU_HEADER_SIZE)

    def getfp(self):
        return self._file

    def rewind(self):
        self._file.seek(self._offset)

    def close(self):
        if self._opened:
            self._file.close()
        self._file = None

    def tell(self):
        pos = self._file.tell() - self._offset
        return max(0, pos)

    def getnchannels(self):
        return self._nchannels

    def getnframes(self):
        return self._nframes

    def getcomptype(self):
        if self._encoding == AUDIO_FILE_ENCODING_MULAW_8:
            return 'ULAW'
        elif self._encoding == AUDIO_FILE_ENCODING_ALAW_8:
            return 'ALAW'
        return 'NONE'

    def getcompname(self):
        ct = self.getcomptype()
        if ct == 'ULAW':
            return 'CCITT G.711 u-law'
        elif ct == 'ALAW':
            return 'CCITT G.711 A-law'
        return 'not compressed'

    def getframerate(self):
        return self._rate

    def getsampwidth(self):
        enc = self._encoding
        if enc in (AUDIO_FILE_ENCODING_MULAW_8, AUDIO_FILE_ENCODING_LINEAR_8,
                   AUDIO_FILE_ENCODING_ALAW_8):
            return 1
        elif enc == AUDIO_FILE_ENCODING_LINEAR_16:
            return 2
        elif enc == AUDIO_FILE_ENCODING_LINEAR_24:
            return 3
        elif enc in (AUDIO_FILE_ENCODING_LINEAR_32, AUDIO_FILE_ENCODING_FLOAT):
            return 4
        elif enc == AUDIO_FILE_ENCODING_DOUBLE:
            return 8
        raise Error('unknown encoding')

    def getparams(self):
        return (self.getnchannels(), self.getsampwidth(), self.getframerate(),
                self.getnframes(), self.getcomptype(), self.getcompname())

    def readframes(self, nframes):
        sw = self.getsampwidth()
        return self._file.read(nframes * sw * self._nchannels)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class Au_write:
    def __init__(self, f):
        if isinstance(f, str):
            f = open(f, 'wb')
            self._opened = True
        else:
            self._opened = False
        self._file = f
        self._nchannels = 0
        self._sampwidth = 0
        self._framerate = 0
        self._nframes = 0
        self._nframeswritten = 0
        self._encoding = AUDIO_FILE_ENCODING_LINEAR_16
        self._comptype = 'NONE'
        self._compname = 'not compressed'
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
        encoding = AUDIO_FILE_ENCODING_LINEAR_16
        if self._sampwidth == 1:
            encoding = AUDIO_FILE_ENCODING_LINEAR_8
        elif self._sampwidth == 3:
            encoding = AUDIO_FILE_ENCODING_LINEAR_24
        elif self._sampwidth == 4:
            encoding = AUDIO_FILE_ENCODING_LINEAR_32
        header = _struct.pack('>IIIIII',
                               _SUNAU_MAGIC, AU_HEADER_SIZE,
                               _UNKNOWN_SIZE, encoding,
                               self._framerate, self._nchannels)
        self._file.write(header)

    def writeframes(self, data):
        self._write_header()
        self._file.write(data)
        nframes = len(data) // (self._sampwidth * self._nchannels)
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
        return Au_read(f)
    elif mode in ('w', 'wb'):
        return Au_write(f)
    else:
        raise Error('unknown mode %r' % (mode,))


openfp = open


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def sunau2_error():
    """Error class exists as exception; returns True."""
    return issubclass(Error, Exception)


def sunau2_open():
    """open() function exists; returns True."""
    return callable(open)


def sunau2_constants():
    """AU_HEADER_SIZE and AUDIO_FILE_MAGIC constants exist; returns True."""
    return (isinstance(AU_HEADER_SIZE, int) and
            isinstance(AUDIO_FILE_MAGIC, int) and
            AU_HEADER_SIZE == 24)


__all__ = [
    'open', 'openfp', 'Au_read', 'Au_write', 'Error',
    'AU_HEADER_SIZE', 'AUDIO_FILE_MAGIC',
    'AUDIO_FILE_ENCODING_MULAW_8', 'AUDIO_FILE_ENCODING_LINEAR_8',
    'AUDIO_FILE_ENCODING_LINEAR_16', 'AUDIO_FILE_ENCODING_LINEAR_24',
    'AUDIO_FILE_ENCODING_LINEAR_32', 'AUDIO_FILE_ENCODING_FLOAT',
    'AUDIO_FILE_ENCODING_DOUBLE', 'AUDIO_FILE_ENCODING_ALAW_8',
    'sunau2_error', 'sunau2_open', 'sunau2_constants',
]
