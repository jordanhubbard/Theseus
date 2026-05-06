"""
theseus_uu_cr — Clean-room uu (uuencode/uudecode) module.
No import of the standard `uu` module or any third-party library.
"""

import io as _io
import os as _os

_MAX_PER_LINE = 45


class Error(Exception):
    """Exception raised by uuencode/uudecode operations."""
    pass


# ---------------------------------------------------------------------------
# Low-level encode / decode primitives
# ---------------------------------------------------------------------------

def _encode_chunk(chunk):
    """Encode up to 45 bytes into one uuencoded line (no trailing newline).

    Format: <length-char><four-encoded-chars>* where each group of 3 input
    bytes becomes 4 output chars. A 6-bit value v maps to chr(v + 32),
    except v == 0 which is rendered as a backtick (avoids trailing-space
    truncation by mailers).
    """
    n = len(chunk)
    if n == 0:
        return '`'
    out = [chr(32 + n)]

    # Pad to a multiple of 3 with zero bytes.
    pad = (3 - (n % 3)) % 3
    padded = chunk + bytes(pad)

    for i in range(0, len(padded), 3):
        b0 = padded[i]
        b1 = padded[i + 1]
        b2 = padded[i + 2]
        c0 = (b0 >> 2) & 0x3F
        c1 = ((b0 & 0x03) << 4) | ((b1 >> 4) & 0x0F)
        c2 = ((b1 & 0x0F) << 2) | ((b2 >> 6) & 0x03)
        c3 = b2 & 0x3F
        for v in (c0, c1, c2, c3):
            out.append('`' if v == 0 else chr(32 + v))

    return ''.join(out)


def _decode_char(c):
    """Convert one encoded character back to its 6-bit value."""
    if c == '`':
        return 0
    return (ord(c) - 32) & 0x3F


def _decode_line(line):
    """Decode a single uuencoded line into bytes."""
    if not line:
        return b''
    n = _decode_char(line[0])
    if n == 0:
        return b''

    out = bytearray()
    pos = 1
    line_len = len(line)

    while len(out) < n:
        # Read four characters (treating any missing trailing chars as zero).
        v0 = _decode_char(line[pos]) if pos < line_len else 0
        v1 = _decode_char(line[pos + 1]) if pos + 1 < line_len else 0
        v2 = _decode_char(line[pos + 2]) if pos + 2 < line_len else 0
        v3 = _decode_char(line[pos + 3]) if pos + 3 < line_len else 0

        out.append(((v0 << 2) | (v1 >> 4)) & 0xFF)
        if len(out) < n:
            out.append((((v1 & 0x0F) << 4) | (v2 >> 2)) & 0xFF)
        if len(out) < n:
            out.append((((v2 & 0x03) << 6) | v3) & 0xFF)

        pos += 4
        if pos >= line_len and len(out) < n:
            # Ran out of input characters before satisfying length char.
            break

    return bytes(out[:n])


# ---------------------------------------------------------------------------
# Public API: encode / decode
# ---------------------------------------------------------------------------

def encode(in_file, out_file, name=None, mode=None, *, backtick=False):
    """Uuencode `in_file` into `out_file`.

    `in_file` may be a path, '-' for stdin, or a binary file-like object.
    `out_file` may be a path, '-' for stdout, or a text file-like object.
    """
    opened = []
    try:
        # Resolve in_file
        if in_file == '-':
            in_file = _io.TextIOWrapper.__class__  # placeholder; replaced below
            in_file = _os.fdopen(0, 'rb', closefd=False) if hasattr(_os, 'fdopen') else None
            if name is None:
                name = '-'
            if mode is None:
                mode = 0o666
        elif isinstance(in_file, str):
            if name is None:
                name = _os.path.basename(in_file)
            if mode is None:
                try:
                    mode = _os.stat(in_file).st_mode & 0o777
                except OSError:
                    mode = 0o666
            f = open(in_file, 'rb')
            opened.append(f)
            in_file = f
        else:
            if mode is None:
                mode = 0o666

        if name is None:
            name = '-'

        # Resolve out_file
        if out_file == '-':
            out_file = _io.TextIOWrapper(_os.fdopen(1, 'wb', closefd=False), write_through=True)
        elif isinstance(out_file, str):
            f = open(out_file, 'w')
            opened.append(f)
            out_file = f

        # Header
        out_file.write('begin %o %s\n' % (mode & 0o777, name))

        # Body
        while True:
            chunk = in_file.read(_MAX_PER_LINE)
            if not chunk:
                break
            out_file.write(_encode_chunk(chunk) + '\n')

        # Footer: zero-length data marker line + 'end'
        out_file.write('`\n')
        out_file.write('end\n')
    finally:
        for f in opened:
            try:
                f.close()
            except Exception:
                pass


def decode(in_file, out_file=None, mode=None, quiet=False):
    """Decode a uuencoded `in_file` into `out_file`.

    `in_file` may be a path, '-' for stdin, or a text file-like object.
    `out_file` may be a path, '-' for stdout, a binary file-like object,
    or None (in which case the file named in the begin line is used).
    """
    opened = []
    try:
        # Resolve in_file
        if in_file == '-':
            in_file = _io.TextIOWrapper(_os.fdopen(0, 'rb', closefd=False))
        elif isinstance(in_file, str):
            f = open(in_file, 'r')
            opened.append(f)
            in_file = f

        # Find the begin line
        parsed_mode = None
        parsed_name = '-'
        while True:
            line = in_file.readline()
            if not line:
                raise Error('No valid begin line found in input file')
            line = line.rstrip('\r\n')
            if line.startswith('begin '):
                parts = line.split(' ', 2)
                if len(parts) >= 3:
                    try:
                        parsed_mode = int(parts[1], 8)
                        parsed_name = parts[2]
                        break
                    except ValueError:
                        continue

        if mode is None:
            mode = parsed_mode if parsed_mode is not None else 0o666

        # Resolve out_file
        close_out = False
        if out_file is None:
            out_file = parsed_name
            if _os.path.exists(out_file):
                raise Error('Cannot overwrite existing file: %s' % out_file)

        if out_file == '-':
            out_file = _os.fdopen(1, 'wb', closefd=False)
        elif isinstance(out_file, str):
            fp = open(out_file, 'wb')
            opened.append(fp)
            try:
                _os.chmod(fp.name, mode)
            except OSError:
                pass
            out_file = fp
            close_out = True

        # Decode body lines until we hit 'end' or zero-length sentinel.
        while True:
            line = in_file.readline()
            if not line:
                break
            stripped = line.rstrip('\r\n')
            if stripped == 'end':
                break
            if not stripped:
                continue
            n = _decode_char(stripped[0])
            if n == 0:
                # Zero-length data line — typically the footer marker.
                # Continue: the next line should be 'end'.
                continue
            decoded = _decode_line(stripped)
            out_file.write(decoded)
    finally:
        for f in opened:
            try:
                f.close()
            except Exception:
                pass


# ---------------------------------------------------------------------------
# Invariant entry points
# ---------------------------------------------------------------------------

def uu2_encode_decode():
    """Uuencode then decode round-trips the data."""
    samples = [
        b'',
        b'A',
        b'AB',
        b'ABC',
        b'Hello, World! This is test data.',
        bytes(range(256)),
        b'x' * 100,
        b'\x00\x01\x02\x03 trailing spaces   ',
    ]
    for data in samples:
        in_buf = _io.BytesIO(data)
        out_buf = _io.StringIO()
        encode(in_buf, out_buf, name='test.bin')
        out_buf.seek(0)
        result_buf = _io.BytesIO()
        decode(out_buf, result_buf)
        if result_buf.getvalue() != data:
            return False
    return True


def uu2_header():
    """Encoded output begins with a properly-formed 'begin MODE NAME' header."""
    in_buf = _io.BytesIO(b'test')
    out_buf = _io.StringIO()
    encode(in_buf, out_buf, name='test.txt', mode=0o644)
    out_buf.seek(0)
    content = out_buf.read()
    first_line = content.split('\n', 1)[0]
    if not first_line.startswith('begin '):
        return False
    parts = first_line.split(' ', 2)
    if len(parts) != 3:
        return False
    if parts[0] != 'begin':
        return False
    try:
        if int(parts[1], 8) != 0o644:
            return False
    except ValueError:
        return False
    if parts[2] != 'test.txt':
        return False
    return True


def uu2_footer():
    """Encoded output ends with the zero-length sentinel line followed by 'end'."""
    in_buf = _io.BytesIO(b'test')
    out_buf = _io.StringIO()
    encode(in_buf, out_buf, name='test.txt', mode=0o644)
    out_buf.seek(0)
    content = out_buf.read()
    stripped = content.rstrip()
    if not stripped.endswith('end'):
        return False
    # The line preceding 'end' should be the zero-length sentinel
    # (a single '`' or ' '), indicating no further data.
    lines = stripped.split('\n')
    if len(lines) < 2:
        return False
    sentinel = lines[-2]
    if sentinel not in ('`', ' '):
        return False
    if lines[-1] != 'end':
        return False
    return True


__all__ = [
    'Error', 'encode', 'decode',
    'uu2_encode_decode', 'uu2_header', 'uu2_footer',
]