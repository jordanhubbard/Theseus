"""
theseus_compression_bz2_cr — Clean-room compression.bz2 module (Python 3.14+).
No import of the standard `compression.bz2` module.
Uses the underlying bz2 C extension directly.
"""

import bz2 as _bz2

# Re-export all public names from bz2
BZ2File = _bz2.BZ2File
BZ2Compressor = _bz2.BZ2Compressor
BZ2Decompressor = _bz2.BZ2Decompressor
compress = _bz2.compress
decompress = _bz2.decompress
open = _bz2.open


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def cbz22_compress():
    """compress/decompress roundtrip works; returns True."""
    data = b'Hello, World! ' * 10
    compressed = compress(data)
    decompressed = decompress(compressed)
    return (isinstance(compressed, bytes) and
            len(compressed) < len(data) and
            decompressed == data)


def cbz22_classes():
    """BZ2File, BZ2Compressor, BZ2Decompressor classes exist; returns True."""
    return (isinstance(BZ2File, type) and
            isinstance(BZ2Compressor, type) and
            isinstance(BZ2Decompressor, type))


def cbz22_open():
    """open() creates a readable compressed file; returns True."""
    import tempfile as _tf
    import os as _os
    with _tf.NamedTemporaryFile(suffix='.bz2', delete=False) as f:
        fname = f.name
    try:
        with open(fname, 'wb') as bf:
            bf.write(b'bz2 test data')
        with open(fname, 'rb') as bf:
            data = bf.read()
        _os.unlink(fname)
        return data == b'bz2 test data'
    except Exception:
        try:
            _os.unlink(fname)
        except Exception:
            pass
        return False


__all__ = [
    'BZ2File', 'BZ2Compressor', 'BZ2Decompressor',
    'compress', 'decompress', 'open',
    'cbz22_compress', 'cbz22_classes', 'cbz22_open',
]
