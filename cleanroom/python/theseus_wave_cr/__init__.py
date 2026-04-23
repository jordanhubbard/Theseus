"""
theseus_wave_cr — Clean-room wave module.
No import of the standard `wave` module.
Pure Python implementation of WAV file reading/writing.
"""

import struct as _struct
import io as _io
import collections as _collections

WAVE_FORMAT_PCM = 0x0001


class Error(Exception):
    pass


_Wave_params = _collections.namedtuple(
    '_Wave_params',
    ['nchannels', 'sampwidth', 'framerate', 'nframes', 'comptype', 'compname']
)


class Wave_read:
    def __init__(self, file):
        self._file = None
        self._nchannels = 0
        self._nframes = 0
        self._framerate = 0
        self._sampwidth = 0
        self._framesize = 0
        self._comptype = 'NONE'
        self._compname = 'not compressed'
        self._soundpos = 0
        self._data_seek_needed = True
        self._data_offset = None
        self._data_len = None

        if isinstance(file, str):
            self._file = open(file, 'rb')
            self._opened = True
        else:
            self._file = file
            self._opened = False
        self._initfp()

    def _initfp(self):
        f = self._file
        riff = f.read(4)
        if riff != b'RIFF':
            raise Error('file does not start with RIFF id')
        f.read(4)  # file size
        wave_id = f.read(4)
        if wave_id != b'WAVE':
            raise Error('not a WAVE file')

        while True:
            chunk_id = f.read(4)
            if len(chunk_id) < 4:
                break
            chunk_size = _struct.unpack('<I', f.read(4))[0]
            if chunk_id == b'fmt ':
                fmt_data = f.read(chunk_size)
                audio_format = _struct.unpack_from('<H', fmt_data, 0)[0]
                if audio_format != WAVE_FORMAT_PCM:
                    raise Error(f'unknown format: {audio_format}')
                self._nchannels = _struct.unpack_from('<H', fmt_data, 2)[0]
                self._framerate = _struct.unpack_from('<I', fmt_data, 4)[0]
                self._sampwidth = _struct.unpack_from('<H', fmt_data, 14)[0] // 8
                self._framesize = self._nchannels * self._sampwidth
            elif chunk_id == b'data':
                self._data_offset = f.tell()
                self._data_len = chunk_size
                self._nframes = chunk_size // self._framesize if self._framesize else 0
                f.seek(chunk_size, 1)
            else:
                f.seek(chunk_size, 1)

        if self._data_offset is not None:
            self._file.seek(self._data_offset)

    def getparams(self):
        return _Wave_params(
            self._nchannels, self._sampwidth, self._framerate,
            self._nframes, self._comptype, self._compname
        )

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

    def readframes(self, nframes):
        return self._file.read(nframes * self._framesize)

    def rewind(self):
        if self._data_offset:
            self._file.seek(self._data_offset)

    def getpos(self):
        if self._data_offset:
            return (self._file.tell() - self._data_offset) // self._framesize
        return 0

    def setpos(self, pos):
        if self._data_offset:
            self._file.seek(self._data_offset + pos * self._framesize)

    def close(self):
        if self._file and self._opened:
            self._file.close()
        self._file = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class Wave_write:
    def __init__(self, file):
        self._nchannels = 0
        self._sampwidth = 0
        self._framerate = 0
        self._nframes = 0
        self._nframeswritten = 0
        self._datawritten = 0
        self._datalength = 0
        self._comptype = 'NONE'
        self._compname = 'not compressed'
        self._headerwritten = False

        if isinstance(file, str):
            self._file = open(file, 'wb')
            self._opened = True
        else:
            self._file = file
            self._opened = False

    def setnchannels(self, nchannels):
        if nchannels < 1:
            raise Error('bad # of channels')
        self._nchannels = nchannels

    def setsampwidth(self, sampwidth):
        if sampwidth not in (1, 2, 3, 4):
            raise Error('bad sample width')
        self._sampwidth = sampwidth

    def setframerate(self, framerate):
        if framerate <= 0:
            raise Error('bad frame rate')
        self._framerate = int(framerate)

    def setnframes(self, nframes):
        self._nframes = nframes

    def setcomptype(self, comptype, compname):
        if comptype != 'NONE':
            raise Error('unsupported compression type')
        self._comptype = comptype
        self._compname = compname

    def setparams(self, params):
        self.setnchannels(params.nchannels)
        self.setsampwidth(params.sampwidth)
        self.setframerate(params.framerate)
        self.setnframes(params.nframes)
        self.setcomptype(params.comptype, params.compname)

    def getparams(self):
        return _Wave_params(
            self._nchannels, self._sampwidth, self._framerate,
            self._nframes, self._comptype, self._compname
        )

    def _ensure_header_written(self):
        if not self._headerwritten:
            if not self._nchannels:
                raise Error('# channels not specified')
            if not self._sampwidth:
                raise Error('sample width not specified')
            if not self._framerate:
                raise Error('sampling rate not specified')
            self._write_header()
            self._headerwritten = True

    def _write_header(self):
        f = self._file
        # Write RIFF header placeholder
        f.write(b'RIFF')
        self._form_length_pos = f.tell()
        f.write(b'\x00\x00\x00\x00')  # will be filled in close()
        f.write(b'WAVE')
        # fmt chunk
        f.write(b'fmt ')
        f.write(_struct.pack('<I', 16))
        f.write(_struct.pack('<H', WAVE_FORMAT_PCM))
        f.write(_struct.pack('<H', self._nchannels))
        f.write(_struct.pack('<I', self._framerate))
        byte_rate = self._framerate * self._nchannels * self._sampwidth
        f.write(_struct.pack('<I', byte_rate))
        block_align = self._nchannels * self._sampwidth
        f.write(_struct.pack('<H', block_align))
        f.write(_struct.pack('<H', self._sampwidth * 8))
        # data chunk
        f.write(b'data')
        self._data_length_pos = f.tell()
        f.write(b'\x00\x00\x00\x00')  # will be filled in close()

    def writeframesraw(self, data):
        self._ensure_header_written()
        self._file.write(data)
        self._datawritten += len(data)

    def writeframes(self, data):
        self.writeframesraw(data)

    def close(self):
        try:
            if self._file and self._headerwritten:
                self._file.flush()
                pos = self._file.tell()
                data_len = pos - self._data_length_pos - 4
                form_len = pos - 8
                self._file.seek(self._form_length_pos)
                self._file.write(_struct.pack('<I', form_len))
                self._file.seek(self._data_length_pos)
                self._file.write(_struct.pack('<I', data_len))
        finally:
            if self._file and self._opened:
                self._file.close()
            self._file = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def open(file, mode=None):
    """Open a WAV file for reading or writing."""
    if mode is None:
        if hasattr(file, 'mode'):
            mode = file.mode
        else:
            mode = 'rb'
    if mode in ('r', 'rb'):
        return Wave_read(file)
    elif mode in ('w', 'wb'):
        return Wave_write(file)
    else:
        raise Error(f"mode must be 'r', 'rb', 'w', or 'wb'")


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def wave2_write_read():
    """write then read back a WAV file; returns True."""
    buf = _io.BytesIO()
    with Wave_write(buf) as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(44100)
        wf.writeframes(b'\x00\x01' * 100)
    buf.seek(0)
    with Wave_read(buf) as rf:
        params = rf.getparams()
        return (params.nchannels == 1 and
                params.sampwidth == 2 and
                params.framerate == 44100 and
                params.nframes == 100)


def wave2_params():
    """Wave_read.getparams() returns named tuple; returns True."""
    buf = _io.BytesIO()
    with Wave_write(buf) as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(22050)
        wf.writeframes(b'\x00' * 8)
    buf.seek(0)
    with Wave_read(buf) as rf:
        p = rf.getparams()
        return (hasattr(p, 'nchannels') and hasattr(p, 'framerate') and
                p.comptype == 'NONE')


def wave2_error():
    """wave.Error exception class exists; returns True."""
    return issubclass(Error, Exception)


__all__ = [
    'open', 'Wave_read', 'Wave_write', 'Error',
    'wave2_write_read', 'wave2_params', 'wave2_error',
]
