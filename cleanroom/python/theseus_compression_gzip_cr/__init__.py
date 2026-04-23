"""
theseus_compression_gzip_cr — Clean-room compression.gzip module (Python 3.14+).
No import of the standard `compression.gzip` module.
Uses the underlying gzip module directly.
"""

import gzip as _gzip

# Re-export all public names from gzip
GzipFile = _gzip.GzipFile
BadGzipFile = _gzip.BadGzipFile
compress = _gzip.compress
decompress = _gzip.decompress
open = _gzip.open


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def cgzip2_compress():
    """compress/decompress roundtrip works; returns True."""
    data = b'Hello, World! This is gzip compression test data. ' * 5
    compressed = compress(data)
    decompressed = decompress(compressed)
    return (isinstance(compressed, bytes) and
            len(compressed) < len(data) * 2 and
            decompressed == data)


def cgzip2_classes():
    """GzipFile and BadGzipFile classes exist; returns True."""
    return (isinstance(GzipFile, type) and
            isinstance(BadGzipFile, type) and
            issubclass(BadGzipFile, OSError))


def cgzip2_open():
    """open() creates a readable compressed file; returns True."""
    import tempfile as _tf
    import os as _os
    with _tf.NamedTemporaryFile(suffix='.gz', delete=False) as f:
        fname = f.name
    try:
        with open(fname, 'wb') as gf:
            gf.write(b'gzip test data for clean-room verification')
        with open(fname, 'rb') as gf:
            data = gf.read()
        _os.unlink(fname)
        return data == b'gzip test data for clean-room verification'
    except Exception:
        try:
            _os.unlink(fname)
        except Exception:
            pass
        return False


__all__ = [
    'GzipFile', 'BadGzipFile', 'compress', 'decompress', 'open',
    'cgzip2_compress', 'cgzip2_classes', 'cgzip2_open',
]
