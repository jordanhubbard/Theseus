"""
theseus_sndhdr_cr — Clean-room sndhdr module.
No import of the standard `sndhdr` module.
"""

import io as _io
import struct as _struct

tests = []


def test_aifc(h, f):
    if h[:4] == b'FORM' and h[8:12] == b'AIFF':
        return 'aiff', 0, 0, 0, 0
    if h[:4] == b'FORM' and h[8:12] == b'AIFC':
        return 'aifc', 0, 0, 0, 0
    return None


def test_au(h, f):
    if h[:4] == b'.snd':
        return 'au', 0, 0, 0, 0
    return None


def test_wav(h, f):
    if h[:4] == b'RIFF' and h[8:12] == b'WAVE':
        if h[12:16] == b'fmt ':
            return 'wav', 0, 0, 0, 0
    return None


def test_hcom(h, f):
    if h[65:69] == b'FSSD' and h[128:132] == b'HCOM':
        return 'hcom', 0, 0, 0, 0
    return None


def test_voc(h, f):
    if h[:20] == b'Creative Voice File\x1a':
        return 'voc', 0, 0, 0, 0
    return None


def test_sndr(h, f):
    if 4000 <= _struct.unpack('<H', h[:2])[0] <= 25000:
        return 'sndr', 0, 0, 0, 0
    return None


def test_sndt(h, f):
    if h[:2] == b'Sd':
        return 'sndt', 0, 0, 0, 0
    return None


def test_svx(h, f):
    if h[:4] == b'FORM' and h[8:12] == b'8SVX':
        return '8svx', 0, 0, 0, 0
    return None


def test_8svx(h, f):
    return test_svx(h, f)


def test_cvs(h, f):
    if h[:4] == b'cvsd':
        return 'cvsd', 0, 0, 0, 0
    return None


tests.extend([
    test_aifc, test_au, test_wav, test_hcom, test_voc,
    test_sndr, test_sndt, test_svx, test_8svx, test_cvs,
])


def whathdr(filename):
    """Recognize sound headers."""
    with open(filename, 'rb') as f:
        h = f.read(512)
        for tf in tests:
            res = tf(h, f)
            if res:
                return res
    return None


def what(filename):
    """Recognize sound files."""
    res = whathdr(filename)
    return res


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def sndhdr2_what():
    """what() function returns None for non-sound files; returns True."""
    import tempfile as _tmp
    import os as _os
    # Create a file that is clearly not audio
    with _tmp.NamedTemporaryFile(suffix='.bin', delete=False) as f:
        f.write(b'\x00\x01\x02\x03\x04')
        tmpname = f.name
    try:
        result = what(tmpname)
        return result is None
    finally:
        _os.unlink(tmpname)


def sndhdr2_whathdr():
    """whathdr() detects file types by header; returns True."""
    import tempfile as _tmp
    import os as _os
    # Create a fake AU file header
    with _tmp.NamedTemporaryFile(suffix='.au', delete=False) as f:
        f.write(b'.snd' + b'\x00' * 20)
        tmpname = f.name
    try:
        result = whathdr(tmpname)
        return result is not None and result[0] == 'au'
    finally:
        _os.unlink(tmpname)


def sndhdr2_tests():
    """tests list contains type-detection functions; returns True."""
    return isinstance(tests, list) and len(tests) > 0 and callable(tests[0])


__all__ = [
    'what', 'whathdr', 'tests',
    'sndhdr2_what', 'sndhdr2_whathdr', 'sndhdr2_tests',
]
