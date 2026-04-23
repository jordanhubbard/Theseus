"""
theseus_uu_cr — Clean-room uu module.
No import of the standard `uu` module.
"""

import binascii as _binascii
import io as _io
import os as _os

_MAXPERLINE = 45

# Translation table: 0 -> chr(32), ..., 63 -> chr(95)
_ENC_TABLE = bytes(range(32, 96))
_DEC_TABLE = bytes(range(256))  # not needed, computed inline


class Error(Exception):
    pass


def encode(in_file, out_file, name='-', mode=None):
    """Encode a file using uuencode."""
    if isinstance(in_file, str):
        if name == '-':
            name = in_file
        in_file = open(in_file, 'rb')
        close_in = True
    else:
        close_in = False

    if isinstance(out_file, str):
        out_file = open(out_file, 'w')
        close_out = True
    else:
        close_out = False

    if mode is None:
        try:
            mode = _os.stat(in_file.name).st_mode & 0o666
        except AttributeError:
            mode = 0o666

    out_file.write(f'begin {mode:o} {name}\n')

    try:
        while True:
            data = in_file.read(_MAXPERLINE)
            if not data:
                break
            out_file.write(_encode_line(data) + '\n')
        out_file.write(' \n')
        out_file.write('end\n')
    finally:
        if close_in:
            in_file.close()
        if close_out:
            out_file.close()


def _encode_line(data):
    """Encode one line of data."""
    result = [chr(32 + len(data))]
    i = 0
    while i < len(data):
        b0 = data[i] if i < len(data) else 0
        b1 = data[i + 1] if i + 1 < len(data) else 0
        b2 = data[i + 2] if i + 2 < len(data) else 0
        result.append(chr(32 + ((b0 >> 2) & 0x3F)) if (b0 >> 2) & 0x3F else '`')
        result.append(chr(32 + (((b0 & 3) << 4) | ((b1 >> 4) & 0xF))) if (((b0 & 3) << 4) | ((b1 >> 4) & 0xF)) else '`')
        result.append(chr(32 + (((b1 & 0xF) << 2) | ((b2 >> 6) & 3))) if (((b1 & 0xF) << 2) | ((b2 >> 6) & 3)) else '`')
        result.append(chr(32 + (b2 & 0x3F)) if (b2 & 0x3F) else '`')
        i += 3
    return ''.join(result)


def _decode_char(c):
    """Decode a single uu character."""
    val = (ord(c) - 32) & 0x3F
    return val


def decode(in_file, out_file=None, ignore_garbage=False):
    """Decode a uuencoded file."""
    if isinstance(in_file, str):
        in_file = open(in_file, 'r')
        close_in = True
    else:
        close_in = False

    try:
        # Find begin line
        for line in in_file:
            line = line.rstrip('\r\n')
            if line.startswith('begin '):
                parts = line.split(' ', 2)
                mode_str = parts[1]
                name = parts[2] if len(parts) > 2 else '-'
                mode = int(mode_str, 8)
                break
        else:
            raise Error("No begin line")

        if out_file is None:
            out_file = open(name, 'wb')
            close_out = True
        elif isinstance(out_file, str):
            out_file = open(out_file, 'wb')
            close_out = True
        else:
            close_out = False

        try:
            for line in in_file:
                line = line.rstrip('\r\n')
                if not line:
                    continue
                if line == 'end':
                    break
                if line == ' ' or line == '`':
                    continue
                nbytes = _decode_char(line[0])
                if nbytes == 0:
                    break
                data = bytearray()
                i = 1
                while len(data) < nbytes and i + 3 < len(line) + 1:
                    c0 = _decode_char(line[i]) if i < len(line) else 0
                    c1 = _decode_char(line[i + 1]) if i + 1 < len(line) else 0
                    c2 = _decode_char(line[i + 2]) if i + 2 < len(line) else 0
                    c3 = _decode_char(line[i + 3]) if i + 3 < len(line) else 0
                    data.append((c0 << 2) | (c1 >> 4))
                    if len(data) < nbytes:
                        data.append(((c1 & 0xF) << 4) | (c2 >> 2))
                    if len(data) < nbytes:
                        data.append(((c2 & 3) << 6) | c3)
                    i += 4
                out_file.write(bytes(data[:nbytes]))
        finally:
            if close_out:
                out_file.close()
    finally:
        if close_in:
            in_file.close()


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def uu2_encode_decode():
    """uuencode then decode round-trips data; returns True."""
    data = b'Hello, World! This is test data.'
    in_buf = _io.BytesIO(data)
    out_buf = _io.StringIO()
    encode(in_buf, out_buf, name='test.txt')
    out_buf.seek(0)
    result_buf = _io.BytesIO()
    decode(out_buf, result_buf)
    return result_buf.getvalue() == data


def uu2_header():
    """Encoded data starts with 'begin' header; returns True."""
    in_buf = _io.BytesIO(b'test')
    out_buf = _io.StringIO()
    encode(in_buf, out_buf, name='test.txt', mode=0o644)
    out_buf.seek(0)
    content = out_buf.read()
    return content.startswith('begin ')


def uu2_footer():
    """Encoded data ends with 'end' footer; returns True."""
    in_buf = _io.BytesIO(b'test')
    out_buf = _io.StringIO()
    encode(in_buf, out_buf, name='test.txt', mode=0o644)
    out_buf.seek(0)
    content = out_buf.read()
    return content.rstrip().endswith('end')


__all__ = [
    'Error', 'encode', 'decode',
    'uu2_encode_decode', 'uu2_header', 'uu2_footer',
]
