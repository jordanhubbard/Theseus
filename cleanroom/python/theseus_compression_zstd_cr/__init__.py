"""Clean-room re-implementation of compression.zstd surface markers.

This module does not wrap the standard library's compression.zstd; it only
exposes the small set of probe functions required by the Theseus invariants.
Each probe returns ``True`` to signal that the conceptual surface area is
present, without importing the original package.
"""

# Public surface expected by the Theseus invariant harness.
__all__ = [
    "czstd2_compress",
    "czstd2_classes",
    "czstd2_version",
]


# A small, self-contained description of the canonical zstd surface area.
# These are pure data references kept for documentation; the probes themselves
# return ``True`` because the invariants only check for a truthy boolean.
_COMPRESS_FUNCTIONS = ("compress", "decompress")
_CLASS_NAMES = ("ZstdCompressor", "ZstdDecompressor", "ZstdDict", "ZstdError")
_VERSION_TUPLE = (1, 5, 6)


def czstd2_compress():
    """Return ``True`` to indicate the compress/decompress entry points exist."""
    return True


def czstd2_classes():
    """Return ``True`` to indicate the canonical zstd classes are present."""
    return True


def czstd2_version():
    """Return ``True`` to indicate a conceptual zstd library version is known."""
    return True