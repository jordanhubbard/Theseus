"""Clean-room implementation of a wave (WAV/RIFF) file module.

Implements reading and writing of PCM .wav files from scratch using only
struct, io, and os from the standard library.  Does NOT import the standard
library `wave` module.
"""

import struct
import io
import os
import builtins
import tempfile
from collections import namedtuple

__all__ = [
    'open', 'Error', 'Wave_read', 'Wave_write',
    'wave2_write_read', 'wave2_params', 'wave2_error',
]

WAVE_FORMAT_PCM = 0x0001

_wave_params = namedtuple(
    '_wave_params',
    'nchannels sampwidth framerate nframes comptype compname'
)


class Error(Exception):
    """Errors raised by the wave module."""
    pass


# ---------------------------------------------------------------------------
# Wave_read
# ---------------------------------------------------------------------------
class Wave_read:
    def __init__(self, f):
        self._i_opened_the_file = None
        self._file = None
        if isinstance(f, str):
            f = builtins.open(f, 'rb')
            self._i_opened_the_file = f
        try:
            self._init_riff(f)
        except Exception:
            if self._i_opened_the_file is not None:
                self._i_opened_the_file.close()
                self._i_opened_the_file = None
            raise

    def _init_riff(self, f):
        self._file = f
        riff = f.read(4)
        if riff != b'RIFF':
            raise Error('file does not start with RIFF id')
        size_bytes = f.read(4)
        if len(size_bytes) < 4:
            raise Error('truncated RIFF header')
        wave = f.read(4)
        if wave != b'WAVE':
            raise Error('not a WAVE file')

        self._fmt_read = False
        self._data_chunk_pos = None
        self._data_size = 0
        self._nchannels = 0
        self._sampwidth = 0
        self._framerate = 0
        self._framesize = 0

        while True:
            chunk_id = f.read(4)
            if len(chunk_id) < 4:
                break
            sz_bytes = f.read(4)
            if len(sz_bytes) < 4:
                break
            chunk_size = struct.unpack('<I', sz_bytes)[0]

            if chunk_id == b'fmt ':
                self._read_fmt(f, chunk_size)
            elif chunk_id == b'data':
                self._data_size = chunk_size
                self._data_chunk_pos = f.tell()
                # Don't read past data chunk; user can read frames directly.
                break
            else:
                # Skip unknown chunk (and pad byte if odd-sized)
                f.seek(chunk_size, 1)
                if chunk_size % 2:
                    f.seek(1, 1)

        if not self._fmt_read:
            raise Error('fmt chunk missing')
        if self._data_chunk_pos is None:
            raise Error('data chunk missing')
        if self._framesize == 0:
            raise Error('invalid frame size')

        self._nframes = self._data_size // self._framesize
        self._pos = 0

    def _read_fmt(self, f, size):
        if size < 16:
            raise Error('fmt chunk too small')
        data = f.read(size)
        if len(data) < 16:
            raise Error('truncated fmt chunk')
        if size % 2:
            f.seek(1, 1)
        (wFormatTag, nChannels, nSamplesPerSec,
         nAvgBytesPerSec, nBlockAlign, wBitsPerSample) = struct.unpack(
            '<HHIIHH', data[:16]
        )
        if wFormatTag != WAVE_FORMAT_PCM:
            raise Error('unknown format: %r' % (wFormatTag,))
        if nChannels < 1:
            raise Error('bad # of channels')
        if wBitsPerSample < 1:
            raise Error('bad sample width')
        self._nchannels = nChannels
        self._framerate = nSamplesPerSec
        self._sampwidth = (wBitsPerSample + 7) // 8
        self._framesize = self._nchannels * self._sampwidth
        self._comptype = 'NONE'
        self._compname = 'not compressed'
        self._fmt_read = True

    def getnchannels(self):
        return self._nchannels

    def getsampwidth(self):
        return self._sampwidth

    def getframerate(self):
        return self._framerate

    def getnframes(self):
        return self._nframes

    def getcomptype(self):
        return self._comptype

    def getcompname(self):
        return self._compname

    def getparams(self):
        return _wave_params(
            self._nchannels, self._sampwidth, self._framerate,
            self._nframes, self._comptype, self._compname,
        )

    def readframes(self, nframes):
        if self._pos >= self._nframes:
            return b''
        if nframes > self._nframes - self._pos:
            nframes = self._nframes - self._pos
        if nframes <= 0:
            return b''
        nbytes = nframes * self._framesize
        self._file.seek(self._data_chunk_pos + self._pos * self._framesize)
        data = self._file.read(nbytes)
        self._pos += nframes
        return data

    def rewind(self):
        self._pos = 0

    def tell(self):
        return self._pos

    def setpos(self, pos):
        if pos < 0 or pos > self._nframes:
            raise Error('position out of range')
        self._pos = pos

    def close(self):
        if self._i_opened_the_file is not None:
            self._i_opened_the_file.close()
            self._i_opened_the_file = None
        self._file = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


# ---------------------------------------------------------------------------
# Wave_write
# ---------------------------------------------------------------------------
class Wave_write:
    def __init__(self, f):
        self._i_opened_the_file = None
        if isinstance(f, str):
            f = builtins.open(f, 'wb')
            self._i_opened_the_file = f
        self._file = f
        self._nchannels = 0
        self._sampwidth = 0
        self._framerate = 0
        self._nframes = 0
        self._comptype = 'NONE'
        self._compname = 'not compressed'
        self._datawritten = 0
        self._headerwritten = False
        self._form_length_pos = None
        self._data_length_pos = None

    def setnchannels(self, n):
        if n < 1:
            raise Error('bad # of channels')
        self._nchannels = n

    def setsampwidth(self, n):
        if n < 1 or n > 4:
            raise Error('bad sample width')
        self._sampwidth = n

    def setframerate(self, n):
        if n <= 0:
            raise Error('bad framerate')
        self._framerate = int(round(n))

    def setnframes(self, n):
        if n < 0:
            raise Error('bad # of frames')
        self._nframes = n

    def setcomptype(self, comptype, compname):
        if comptype != 'NONE':
            raise Error('unsupported compression type')
        self._comptype = comptype
        self._compname = compname

    def setparams(self, params):
        nchannels, sampwidth, framerate, nframes, comptype, compname = params
        if self._datawritten:
            raise Error('cannot change parameters after writing data')
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
        return self._nframes

    def getcomptype(self):
        return self._comptype

    def getcompname(self):
        return self._compname

    def getparams(self):
        return _wave_params(
            self._nchannels, self._sampwidth, self._framerate,
            self._nframes, self._comptype, self._compname,
        )

    def _ensure_header(self):
        if self._headerwritten:
            return
        if not self._nchannels:
            raise Error('# channels not specified')
        if not self._sampwidth:
            raise Error('sample width not specified')
        if not self._framerate:
            raise Error('sampling rate not specified')

        framesize = self._nchannels * self._sampwidth
        bits = self._sampwidth * 8
        byterate = self._nchannels * self._framerate * self._sampwidth

        self._file.write(b'RIFF')
        try:
            self._form_length_pos = self._file.tell()
        except (AttributeError, OSError):
            self._form_length_pos = None
        self._file.write(struct.pack('<I', 0))  # placeholder
        self._file.write(b'WAVE')
        self._file.write(b'fmt ')
        self._file.write(struct.pack('<I', 16))
        self._file.write(struct.pack(
            '<HHIIHH',
            WAVE_FORMAT_PCM,
            self._nchannels,
            self._framerate,
            byterate,
            framesize,
            bits,
        ))
        self._file.write(b'data')
        try:
            self._data_length_pos = self._file.tell()
        except (AttributeError, OSError):
            self._data_length_pos = None
        self._file.write(struct.pack('<I', 0))  # placeholder
        self._headerwritten = True

    def writeframesraw(self, data):
        self._ensure_header()
        if not isinstance(data, (bytes, bytearray)):
            data = bytes(data)
        self._file.write(data)
        self._datawritten += len(data)

    def writeframes(self, data):
        self.writeframesraw(data)
        self._patch_header()

    def _patch_header(self):
        if self._form_length_pos is None or self._data_length_pos is None:
            return
        try:
            cur = self._file.tell()
            self._file.seek(self._form_length_pos)
            self._file.write(struct.pack('<I', 36 + self._datawritten))
            self._file.seek(self._data_length_pos)
            self._file.write(struct.pack('<I', self._datawritten))
            self._file.seek(cur)
        except (AttributeError, OSError):
            pass

    def close(self):
        try:
            if self._file is not None:
                self._ensure_header()
                self._patch_header()
                try:
                    self._file.flush()
                except (AttributeError, OSError):
                    pass
        finally:
            if self._i_opened_the_file is not None:
                self._i_opened_the_file.close()
                self._i_opened_the_file = None
            self._file = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


# ---------------------------------------------------------------------------
# Module-level open
# ---------------------------------------------------------------------------
def open(f, mode=None):
    if mode is None:
        if hasattr(f, 'mode'):
            mode = f.mode
        else:
            mode = 'rb'
    if mode in ('r', 'rb'):
        return Wave_read(f)
    elif mode in ('w', 'wb'):
        return Wave_write(f)
    else:
        raise Error("mode must be 'r', 'rb', 'w', or 'wb'")


# ---------------------------------------------------------------------------
# Invariants
# ---------------------------------------------------------------------------
def wave2_write_read():
    """Verify that writing then reading back a WAV file roundtrips."""
    fd, path = tempfile.mkstemp(suffix='.wav')
    os.close(fd)
    try:
        # Write
        w = open(path, 'wb')
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(44100)
        # 100 frames, 2 bytes each (16-bit mono)
        data = b''.join(
            struct.pack('<h', (i * 17) % 32768) for i in range(100)
        )
        w.writeframes(data)
        w.close()

        # Read
        r = open(path, 'rb')
        try:
            if r.getnchannels() != 1:
                return False
            if r.getsampwidth() != 2:
                return False
            if r.getframerate() != 44100:
                return False
            if r.getnframes() != 100:
                return False
            if r.getcomptype() != 'NONE':
                return False
            out = r.readframes(100)
            if out != data:
                return False
            # readframes past end yields b''
            if r.readframes(10) != b'':
                return False
            r.rewind()
            if r.tell() != 0:
                return False
            r.setpos(50)
            if r.tell() != 50:
                return False
            tail = r.readframes(50)
            if tail != data[50 * 2:]:
                return False
        finally:
            r.close()
        return True
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


def wave2_params():
    """Verify that getparams/setparams preserve all six fields."""
    fd, path = tempfile.mkstemp(suffix='.wav')
    os.close(fd)
    try:
        params_in = (2, 2, 22050, 0, 'NONE', 'not compressed')
        w = open(path, 'wb')
        w.setparams(params_in)
        # 50 stereo frames of 16-bit samples = 50 * 2 * 2 = 200 bytes
        frame_data = b'\x00\x01\x02\x03' * 50
        w.writeframes(frame_data)
        w.close()

        r = open(path, 'rb')
        try:
            p = r.getparams()
        finally:
            r.close()

        if p.nchannels != 2:
            return False
        if p.sampwidth != 2:
            return False
        if p.framerate != 22050:
            return False
        if p.nframes != 50:
            return False
        if p.comptype != 'NONE':
            return False
        if p.compname != 'not compressed':
            return False

        # Tuple-style unpacking should also work (namedtuple)
        nch, sw, fr, nf, ct, cn = p
        if (nch, sw, fr, nf, ct, cn) != (2, 2, 22050, 50, 'NONE',
                                          'not compressed'):
            return False
        return True
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


def wave2_error():
    """Verify that bad inputs raise Error."""
    # 1. Garbage data should raise Error on read.
    bad = io.BytesIO(b'NOT A WAVE FILE AT ALL')
    try:
        open(bad, 'rb')
    except Error:
        pass
    else:
        return False

    # 2. Truncated RIFF (no WAVE id) should raise Error.
    bad2 = io.BytesIO(b'RIFF\x00\x00\x00\x00XXXX')
    try:
        open(bad2, 'rb')
    except Error:
        pass
    else:
        return False

    # 3. Setting bad sample width should raise Error.
    sink = io.BytesIO()
    w = Wave_write(sink)
    try:
        w.setsampwidth(0)
    except Error:
        pass
    else:
        return False

    # 4. Setting bad number of channels should raise Error.
    try:
        w.setnchannels(0)
    except Error:
        pass
    else:
        return False

    # 5. Unknown compression type should raise Error.
    try:
        w.setcomptype('ALAW', 'a-law')
    except Error:
        pass
    else:
        return False

    # 6. Bad mode for open() should raise Error.
    try:
        open(io.BytesIO(), 'x')
    except Error:
        pass
    else:
        return False

    # 7. Error must be a subclass of Exception.
    if not issubclass(Error, Exception):
        return False

    return True