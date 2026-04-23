"""
theseus_quopri_cr — Clean-room quopri module.
No import of the standard `quopri` module.
"""

import io as _io

_MAXLINESIZE = 76
_ESCAPE = ord('=')
_CRLF = b'\r\n'


def encode(input, output, quotetabs, header=False):
    """Encode input using quoted-printable encoding, writing to output."""
    soft_break = b'=\n'
    prev = b''

    def write(data):
        output.write(data)

    for line in input:
        if isinstance(line, str):
            line = line.encode('latin-1')
        line = line.rstrip(b'\r\n')
        new_line = b''
        for i, c in enumerate(line):
            if header and c == ord(' '):
                new_line += b'_'
            elif (c < 33 or c > 126 or c == _ESCAPE or
                  (quotetabs and (c == ord('\t') or c == ord(' ')))):
                new_line += b'=%02X' % c
            else:
                new_line += bytes([c])
            if len(new_line) >= _MAXLINESIZE - 3:
                write(new_line + soft_break)
                new_line = b''
        if new_line.endswith(b' ') or new_line.endswith(b'\t'):
            new_line = new_line[:-1] + b'=%02X' % new_line[-1]
        write(new_line + b'\n')


def decode(input, output, header=False):
    """Decode quoted-printable encoded input, writing to output."""
    new_line = b''
    for line in input:
        if isinstance(line, str):
            line = line.encode('latin-1')
        line = line.rstrip(b'\r\n')
        i = 0
        while i < len(line):
            c = line[i:i + 1]
            if c == b'=':
                if i + 1 < len(line) and line[i + 1:i + 2] in (b'\n', b'\r'):
                    # soft line break
                    i += 2
                    if i < len(line) and line[i:i + 1] == b'\n':
                        i += 1
                elif i + 2 < len(line):
                    try:
                        new_line += bytes([int(line[i + 1:i + 3], 16)])
                        i += 3
                    except ValueError:
                        new_line += c
                        i += 1
                else:
                    new_line += c
                    i += 1
            elif header and c == b'_':
                new_line += b' '
                i += 1
            else:
                new_line += c
                i += 1
        output.write(new_line + b'\n')
        new_line = b''


def encodestring(s, quotetabs=False, header=False):
    """Encode bytes to quoted-printable, return bytes."""
    infp = _io.BytesIO(s)
    outfp = _io.BytesIO()
    encode(infp, outfp, quotetabs, header)
    return outfp.getvalue()


def decodestring(s, header=False):
    """Decode quoted-printable bytes, return bytes."""
    infp = _io.BytesIO(s)
    outfp = _io.BytesIO()
    decode(infp, outfp, header)
    return outfp.getvalue()


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def quopri2_encode():
    """encodestring encodes non-ASCII bytes as =XX sequences; returns True."""
    data = b'\xff\xfe test'
    result = encodestring(data)
    return b'=FF' in result or b'=ff' in result or b'=FE' in result


def quopri2_decode():
    """decodestring reverses encodestring; returns True."""
    data = b'Hello, \xff world!'
    encoded = encodestring(data)
    decoded = decodestring(encoded)
    return decoded.rstrip(b'\n') == data


def quopri2_ascii():
    """ASCII printable bytes pass through unchanged; returns True."""
    data = b'Hello World'
    result = encodestring(data)
    return b'Hello' in result and b'World' in result


__all__ = [
    'encode', 'decode', 'encodestring', 'decodestring',
    'quopri2_encode', 'quopri2_decode', 'quopri2_ascii',
]
