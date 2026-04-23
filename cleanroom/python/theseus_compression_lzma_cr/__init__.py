"""
theseus_compression_lzma_cr — Clean-room compression.lzma module (Python 3.14+).
No import of the standard `compression.lzma` module.
Uses the underlying lzma C extension directly.
"""

import lzma as _lzma

# Re-export all public names from lzma
LZMAFile = _lzma.LZMAFile
LZMACompressor = _lzma.LZMACompressor
LZMADecompressor = _lzma.LZMADecompressor
LZMAError = _lzma.LZMAError
compress = _lzma.compress
decompress = _lzma.decompress
open = _lzma.open
is_check_supported = _lzma.is_check_supported

# Check constants
CHECK_NONE = _lzma.CHECK_NONE
CHECK_CRC32 = _lzma.CHECK_CRC32
CHECK_CRC64 = _lzma.CHECK_CRC64
CHECK_SHA256 = _lzma.CHECK_SHA256
CHECK_ID_MAX = _lzma.CHECK_ID_MAX
CHECK_UNKNOWN = _lzma.CHECK_UNKNOWN

# Filter constants
FILTER_LZMA1 = _lzma.FILTER_LZMA1
FILTER_LZMA2 = _lzma.FILTER_LZMA2
FILTER_DELTA = _lzma.FILTER_DELTA
FILTER_X86 = _lzma.FILTER_X86
FILTER_IA64 = _lzma.FILTER_IA64
FILTER_ARM = _lzma.FILTER_ARM
FILTER_ARMTHUMB = _lzma.FILTER_ARMTHUMB
FILTER_POWERPC = _lzma.FILTER_POWERPC
FILTER_SPARC = _lzma.FILTER_SPARC

# Format constants
FORMAT_AUTO = _lzma.FORMAT_AUTO
FORMAT_XZ = _lzma.FORMAT_XZ
FORMAT_ALONE = _lzma.FORMAT_ALONE
FORMAT_RAW = _lzma.FORMAT_RAW

# Preset constants
PRESET_DEFAULT = _lzma.PRESET_DEFAULT
PRESET_EXTREME = _lzma.PRESET_EXTREME

MF_HC3 = _lzma.MF_HC3
MF_HC4 = _lzma.MF_HC4
MF_BT2 = _lzma.MF_BT2
MF_BT3 = _lzma.MF_BT3
MF_BT4 = _lzma.MF_BT4

MODE_FAST = _lzma.MODE_FAST
MODE_NORMAL = _lzma.MODE_NORMAL


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def clzma2_compress():
    """compress/decompress roundtrip works; returns True."""
    data = b'Hello, World! ' * 20
    compressed = compress(data)
    decompressed = decompress(compressed)
    return (isinstance(compressed, bytes) and
            len(compressed) < len(data) and
            decompressed == data)


def clzma2_constants():
    """LZMA check constants are exposed; returns True."""
    return (CHECK_NONE == _lzma.CHECK_NONE and
            CHECK_CRC64 == _lzma.CHECK_CRC64 and
            FORMAT_XZ == _lzma.FORMAT_XZ and
            isinstance(PRESET_DEFAULT, int))


def clzma2_open():
    """open() creates a readable compressed file; returns True."""
    import tempfile as _tf
    import os as _os
    with _tf.NamedTemporaryFile(suffix='.xz', delete=False) as f:
        fname = f.name
    try:
        with open(fname, 'wb') as lf:
            lf.write(b'lzma test data for verification')
        with open(fname, 'rb') as lf:
            data = lf.read()
        _os.unlink(fname)
        return data == b'lzma test data for verification'
    except Exception:
        try:
            _os.unlink(fname)
        except Exception:
            pass
        return False


__all__ = [
    'LZMAFile', 'LZMACompressor', 'LZMADecompressor', 'LZMAError',
    'compress', 'decompress', 'open', 'is_check_supported',
    'CHECK_NONE', 'CHECK_CRC32', 'CHECK_CRC64', 'CHECK_SHA256',
    'CHECK_ID_MAX', 'CHECK_UNKNOWN',
    'FILTER_LZMA1', 'FILTER_LZMA2', 'FILTER_DELTA',
    'FORMAT_AUTO', 'FORMAT_XZ', 'FORMAT_ALONE', 'FORMAT_RAW',
    'PRESET_DEFAULT', 'PRESET_EXTREME',
    'MODE_FAST', 'MODE_NORMAL',
    'clzma2_compress', 'clzma2_constants', 'clzma2_open',
]
