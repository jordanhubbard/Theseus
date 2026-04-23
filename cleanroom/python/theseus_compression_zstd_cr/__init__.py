"""
theseus_compression_zstd_cr — Clean-room compression.zstd module (Python 3.14+).
No import of the standard `compression.zstd` module.
Uses the underlying _zstd C extension directly.
"""

import _zstd as _z
import enum as _enum

# Re-export classes
ZstdCompressor = _z.ZstdCompressor
ZstdDecompressor = _z.ZstdDecompressor
ZstdDict = _z.ZstdDict
ZstdError = _z.ZstdError

# Version info
zstd_version = _z.zstd_version
# Build version_info tuple from version string e.g. "1.5.7"
_parts = zstd_version.split('.')
zstd_version_info = tuple(int(p) for p in _parts)

# Constants
COMPRESSION_LEVEL_DEFAULT = _z.ZSTD_CLEVEL_DEFAULT


class FrameInfo:
    """Information about a zstd frame."""
    __slots__ = ('decompressed_size', 'dictionary_id')

    def __init__(self, decompressed_size, dictionary_id):
        self.decompressed_size = decompressed_size
        self.dictionary_id = dictionary_id

    def __repr__(self):
        return (f'FrameInfo(decompressed_size={self.decompressed_size!r}, '
                f'dictionary_id={self.dictionary_id!r})')


class Strategy(_enum.IntEnum):
    fast = _z.ZSTD_fast
    dfast = _z.ZSTD_dfast
    greedy = _z.ZSTD_greedy
    lazy = _z.ZSTD_lazy
    lazy2 = _z.ZSTD_lazy2
    btlazy2 = _z.ZSTD_btlazy2
    btopt = _z.ZSTD_btopt
    btultra = _z.ZSTD_btultra
    btultra2 = _z.ZSTD_btultra2


class CompressionParameter(_enum.IntEnum):
    compression_level = _z.ZSTD_c_compressionLevel
    window_log = _z.ZSTD_c_windowLog
    hash_log = _z.ZSTD_c_hashLog
    chain_log = _z.ZSTD_c_chainLog
    search_log = _z.ZSTD_c_searchLog
    min_match = _z.ZSTD_c_minMatch
    target_length = _z.ZSTD_c_targetLength
    strategy = _z.ZSTD_c_strategy
    nb_workers = _z.ZSTD_c_nbWorkers
    job_size = _z.ZSTD_c_jobSize
    content_size_flag = _z.ZSTD_c_contentSizeFlag
    checksum_flag = _z.ZSTD_c_checksumFlag
    dict_id_flag = _z.ZSTD_c_dictIDFlag


class DecompressionParameter(_enum.IntEnum):
    window_log_max = _z.ZSTD_d_windowLogMax


def compress(data, level=COMPRESSION_LEVEL_DEFAULT):
    """Compress data using zstd compression."""
    c = ZstdCompressor(level=level)
    return c.compress(data, mode=ZstdCompressor.FLUSH_FRAME)


def decompress(data):
    """Decompress zstd-compressed data."""
    d = ZstdDecompressor()
    return d.decompress(data)


def get_frame_info(data):
    """Get information about a zstd frame."""
    raw = _z.get_frame_info(data)
    return FrameInfo(raw[0], raw[1])


def get_frame_size(data):
    """Get the size of a zstd frame."""
    return _z.get_frame_size(data)


def finalize_dict(zstd_dict, samples, dict_size):
    """Finalize a ZstdDict by training on samples."""
    return _z.finalize_dict(zstd_dict, samples, dict_size)


def train_dict(samples, dict_size):
    """Train a zstd dictionary on samples."""
    return _z.train_dict(samples, dict_size)


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def czstd2_compress():
    """compress/decompress roundtrip works; returns True."""
    data = b'Hello, World! This is zstd compression test data. ' * 10
    compressed = compress(data)
    decompressed = decompress(compressed)
    return (isinstance(compressed, bytes) and
            len(compressed) > 0 and
            decompressed == data)


def czstd2_classes():
    """ZstdCompressor and ZstdDecompressor classes exist; returns True."""
    return (isinstance(ZstdCompressor, type) and
            isinstance(ZstdDecompressor, type) and
            isinstance(ZstdError, type) and
            issubclass(ZstdError, Exception))


def czstd2_version():
    """zstd_version string is accessible; returns True."""
    return (isinstance(zstd_version, str) and
            len(zstd_version) > 0 and
            isinstance(zstd_version_info, tuple) and
            len(zstd_version_info) == 3)


__all__ = [
    'ZstdCompressor', 'ZstdDecompressor', 'ZstdDict', 'ZstdError', 'FrameInfo',
    'compress', 'decompress', 'get_frame_info', 'get_frame_size',
    'train_dict', 'finalize_dict',
    'zstd_version', 'zstd_version_info', 'COMPRESSION_LEVEL_DEFAULT',
    'CompressionParameter', 'DecompressionParameter', 'Strategy',
    'czstd2_compress', 'czstd2_classes', 'czstd2_version',
]
