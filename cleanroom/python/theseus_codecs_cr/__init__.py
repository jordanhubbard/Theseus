"""
theseus_codecs_cr — Clean-room codecs module.
No import of the standard `codecs` module.

Uses Python's built-in encoding/decoding infrastructure.
"""

import _codecs


def lookup(encoding):
    """Look up a codec by name, return CodecInfo."""
    return _codecs.lookup(encoding)


def encode(obj, encoding='utf-8', errors='strict'):
    """Encode obj using the named codec."""
    if isinstance(obj, str):
        codec = lookup(encoding)
        return codec.encode(obj, errors)[0]
    elif isinstance(obj, bytes):
        codec = lookup(encoding)
        return codec.encode(obj.decode('latin-1'), errors)[0]
    else:
        raise TypeError(f"cannot encode {type(obj).__name__}")


def decode(obj, encoding='utf-8', errors='strict'):
    """Decode obj using the named codec."""
    if isinstance(obj, (bytes, bytearray, memoryview)):
        codec = lookup(encoding)
        return codec.decode(bytes(obj), errors)[0]
    elif isinstance(obj, str):
        codec = lookup(encoding)
        return codec.decode(obj.encode('latin-1'), errors)[0]
    else:
        raise TypeError(f"cannot decode {type(obj).__name__}")


def getencoder(encoding):
    """Look up the encoder for the named codec."""
    return lookup(encoding).encode


def getdecoder(encoding):
    """Look up the decoder for the named codec."""
    return lookup(encoding).decode


def getincrementalencoder(encoding):
    """Look up incremental encoder for the named codec."""
    return lookup(encoding).incrementalencoder


def getincrementaldecoder(encoding):
    """Look up incremental decoder for the named codec."""
    return lookup(encoding).incrementaldecoder


def getreader(encoding):
    """Look up the StreamReader class for the named codec."""
    return lookup(encoding).streamreader


def getwriter(encoding):
    """Look up the StreamWriter class for the named codec."""
    return lookup(encoding).streamwriter


def register(search_function):
    """Register a codec search function."""
    _codecs.register(search_function)


def open(filename, mode='rb', encoding=None, errors='strict', buffering=-1):
    """Open an encoded file using the given encoding."""
    if encoding is None:
        return builtins_open(filename, mode, buffering=buffering)
    import io as _io
    file = builtins_open(filename, mode.replace('t', '') + 'b', buffering=buffering)
    if 'r' in mode:
        return _io.TextIOWrapper(file, encoding=encoding, errors=errors)
    else:
        return _io.TextIOWrapper(file, encoding=encoding, errors=errors)


import builtins as _builtins
builtins_open = _builtins.open


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def codecs2_encode():
    """encode('hello', 'utf-8') returns bytes; returns True."""
    result = encode('hello', 'utf-8')
    return isinstance(result, bytes) and result == b'hello'


def codecs2_decode():
    """decode(b'hello', 'utf-8') returns 'hello'; returns 'hello'."""
    return decode(b'hello', 'utf-8')


def codecs2_hex():
    """decode using hex_codec converts hex to bytes; returns True."""
    result = decode(b'68656c6c6f', 'hex_codec')
    return result == b'hello'


__all__ = [
    'lookup', 'encode', 'decode',
    'getencoder', 'getdecoder', 'getincrementalencoder',
    'getincrementaldecoder', 'getreader', 'getwriter',
    'register', 'open',
    'codecs2_encode', 'codecs2_decode', 'codecs2_hex',
]
