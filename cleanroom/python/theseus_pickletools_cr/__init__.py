"""Clean-room re-implementation of a small subset of pickletools.

Exports three invariant functions that exercise:
  * an opcode table,
  * a pickle disassembler,
  * a pickle optimizer (strips unused PUT / MEMOIZE ops).

No part of the standard library `pickletools` is imported or referenced.
"""

import io
import struct as _struct


# ---------------------------------------------------------------------------
# Opcode table
# ---------------------------------------------------------------------------
#
# Each entry: (name, byte, arg_kind)
# arg_kind describes how the argument bytes following the opcode are read:
#   'none'      no argument
#   'u1'        one unsigned byte = length, followed by that many bytes (string)
#   'u4'        four little-endian bytes = length, followed by that many bytes
#   'u8'        eight little-endian bytes = length, followed by that many bytes
#   'line'      a newline-terminated line (utf-8/latin-1 text)
#   'ub1'       one unsigned byte (literal int 0..255)
#   'sb2'       two-byte signed little-endian int
#   'sb4'       four-byte signed little-endian int
#   'sb8'       eight-byte signed little-endian int
#

_OPCODES = [
    ("MARK",            b"(",  "none"),
    ("STOP",            b".",  "none"),
    ("POP",             b"0",  "none"),
    ("POP_MARK",        b"1",  "none"),
    ("DUP",             b"2",  "none"),
    ("FLOAT",           b"F",  "line"),
    ("INT",             b"I",  "line"),
    ("BININT",          b"J",  "sb4"),
    ("BININT1",         b"K",  "ub1"),
    ("LONG",            b"L",  "line"),
    ("BININT2",         b"M",  "sb2"),
    ("NONE",            b"N",  "none"),
    ("PERSID",          b"P",  "line"),
    ("BINPERSID",       b"Q",  "none"),
    ("REDUCE",          b"R",  "none"),
    ("STRING",          b"S",  "line"),
    ("BINSTRING",       b"T",  "u4"),
    ("SHORT_BINSTRING", b"U",  "u1"),
    ("UNICODE",         b"V",  "line"),
    ("BINUNICODE",      b"X",  "u4"),
    ("APPEND",          b"a",  "none"),
    ("BUILD",           b"b",  "none"),
    ("GLOBAL",          b"c",  "twolines"),
    ("DICT",            b"d",  "none"),
    ("EMPTY_DICT",      b"}",  "none"),
    ("APPENDS",         b"e",  "none"),
    ("GET",             b"g",  "line"),
    ("BINGET",          b"h",  "ub1"),
    ("INST",            b"i",  "twolines"),
    ("LONG_BINGET",     b"j",  "sb4"),
    ("LIST",            b"l",  "none"),
    ("EMPTY_LIST",      b"]",  "none"),
    ("OBJ",             b"o",  "none"),
    ("PUT",             b"p",  "line"),
    ("BINPUT",          b"q",  "ub1"),
    ("LONG_BINPUT",     b"r",  "sb4"),
    ("SETITEM",         b"s",  "none"),
    ("TUPLE",           b"t",  "none"),
    ("EMPTY_TUPLE",     b")",  "none"),
    ("SETITEMS",        b"u",  "none"),
    ("BINFLOAT",        b">",  "fb8"),
    # Protocol 2.
    ("PROTO",           b"\x80", "ub1"),
    ("NEWOBJ",          b"\x81", "none"),
    ("EXT1",            b"\x82", "ub1"),
    ("EXT2",            b"\x83", "sb2"),
    ("EXT4",            b"\x84", "sb4"),
    ("TUPLE1",          b"\x85", "none"),
    ("TUPLE2",          b"\x86", "none"),
    ("TUPLE3",          b"\x87", "none"),
    ("NEWTRUE",         b"\x88", "none"),
    ("NEWFALSE",        b"\x89", "none"),
    ("LONG1",           b"\x8a", "u1"),
    ("LONG4",           b"\x8b", "sb4"),
    # Protocol 3.
    ("BINBYTES",        b"B",   "u4"),
    ("SHORT_BINBYTES",  b"C",   "u1"),
    # Protocol 4.
    ("SHORT_BINUNICODE", b"\x8c", "u1"),
    ("BINUNICODE8",      b"\x8d", "u8"),
    ("BINBYTES8",        b"\x8e", "u8"),
    ("EMPTY_SET",        b"\x8f", "none"),
    ("ADDITEMS",         b"\x90", "none"),
    ("FROZENSET",        b"\x91", "none"),
    ("NEWOBJ_EX",        b"\x92", "none"),
    ("STACK_GLOBAL",     b"\x93", "none"),
    ("MEMOIZE",          b"\x94", "none"),
    ("FRAME",            b"\x95", "frame"),
    # Protocol 5.
    ("BYTEARRAY8",       b"\x96", "u8"),
    ("NEXT_BUFFER",      b"\x97", "none"),
    ("READONLY_BUFFER",  b"\x98", "none"),
]


# Quick lookup: byte -> (name, arg_kind)
_BY_BYTE = {byte: (name, kind) for (name, byte, kind) in _OPCODES}

# The PUT-family and the GET-family share semantics that the optimizer cares about.
_PUT_NAMES = ("PUT", "BINPUT", "LONG_BINPUT", "MEMOIZE")
_GET_NAMES = ("GET", "BINGET", "LONG_BINGET")


# ---------------------------------------------------------------------------
# Low-level reader
# ---------------------------------------------------------------------------

def _read_line(buf, pos):
    """Read until newline; return (text-bytes-without-newline, new_pos)."""
    end = buf.find(b"\n", pos)
    if end < 0:
        raise ValueError("unterminated line argument at offset %d" % pos)
    return buf[pos:end], end + 1


def _decode_arg(buf, pos, kind):
    """Decode the argument that follows an opcode at byte position `pos`.

    Returns (value, new_pos) where `value` is a Python object representation
    of the argument suitable for human display.
    """
    if kind == "none":
        return None, pos
    if kind == "ub1":
        if pos >= len(buf):
            raise ValueError("truncated ub1 arg")
        return buf[pos], pos + 1
    if kind == "sb2":
        if pos + 2 > len(buf):
            raise ValueError("truncated sb2 arg")
        return _struct.unpack("<H", buf[pos:pos + 2])[0], pos + 2
    if kind == "sb4":
        if pos + 4 > len(buf):
            raise ValueError("truncated sb4 arg")
        return _struct.unpack("<i", buf[pos:pos + 4])[0], pos + 4
    if kind == "sb8":
        if pos + 8 > len(buf):
            raise ValueError("truncated sb8 arg")
        return _struct.unpack("<q", buf[pos:pos + 8])[0], pos + 8
    if kind == "fb8":
        if pos + 8 > len(buf):
            raise ValueError("truncated fb8 arg")
        return _struct.unpack(">d", buf[pos:pos + 8])[0], pos + 8
    if kind == "u1":
        if pos >= len(buf):
            raise ValueError("truncated u1 length")
        n = buf[pos]
        pos += 1
        if pos + n > len(buf):
            raise ValueError("truncated u1 payload")
        return buf[pos:pos + n], pos + n
    if kind == "u4":
        if pos + 4 > len(buf):
            raise ValueError("truncated u4 length")
        n = _struct.unpack("<I", buf[pos:pos + 4])[0]
        pos += 4
        if pos + n > len(buf):
            raise ValueError("truncated u4 payload")
        return buf[pos:pos + n], pos + n
    if kind == "u8":
        if pos + 8 > len(buf):
            raise ValueError("truncated u8 length")
        n = _struct.unpack("<Q", buf[pos:pos + 8])[0]
        pos += 8
        if pos + n > len(buf):
            raise ValueError("truncated u8 payload")
        return buf[pos:pos + n], pos + n
    if kind == "line":
        text, pos = _read_line(buf, pos)
        return text, pos
    if kind == "twolines":
        a, pos = _read_line(buf, pos)
        b, pos = _read_line(buf, pos)
        return (a, b), pos
    if kind == "frame":
        if pos + 8 > len(buf):
            raise ValueError("truncated FRAME length")
        n = _struct.unpack("<Q", buf[pos:pos + 8])[0]
        return n, pos + 8
    raise ValueError("unknown arg kind %r" % (kind,))


def _iter_ops(buf):
    """Yield (offset, name, arg, next_offset) for every opcode in `buf`.

    Stops after STOP. Raises ValueError on malformed input.
    """
    pos = 0
    n = len(buf)
    while pos < n:
        b = buf[pos:pos + 1]
        info = _BY_BYTE.get(b)
        if info is None:
            raise ValueError("unknown opcode %r at offset %d" % (b, pos))
        name, kind = info
        start = pos
        pos += 1
        arg, pos = _decode_arg(buf, pos, kind)
        yield (start, name, arg, pos)
        if name == "STOP":
            return
    raise ValueError("pickle exhausted without STOP")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def opcodes():
    """Return the opcode table as a list of (name, byte, arg_kind) tuples."""
    return list(_OPCODES)


def _format_arg(name, arg):
    if arg is None:
        return ""
    if isinstance(arg, tuple):  # twolines
        a, b = arg
        return " %s %s" % (a.decode("latin-1"), b.decode("latin-1"))
    if isinstance(arg, bytes):
        try:
            return " " + repr(arg.decode("utf-8"))
        except UnicodeDecodeError:
            return " " + repr(arg)
    return " " + repr(arg)


def dis(pickle, out=None):
    """Disassemble `pickle` (bytes) to `out` (a text stream).

    If `out` is None, returns the disassembly as a string.
    """
    if isinstance(pickle, (bytearray,)):
        pickle = bytes(pickle)
    elif not isinstance(pickle, (bytes,)):
        raise TypeError("dis() expects bytes-like input")

    return_string = out is None
    sink = io.StringIO() if return_string else out

    indent = 0
    for offset, name, arg, _next in _iter_ops(pickle):
        # Cosmetic: MARK pushes a marker that closing ops consume.
        if name in ("POP_MARK", "LIST", "TUPLE", "DICT", "SETITEMS",
                    "APPENDS", "ADDITEMS", "FROZENSET", "OBJ", "INST",
                    "BUILD"):
            indent = max(indent - 1, 0)
        line = "%5d: %-2s %s%s\n" % (
            offset,
            pickle[offset:offset + 1].hex(),
            "    " * indent + name,
            _format_arg(name, arg),
        )
        sink.write(line)
        if name == "MARK":
            indent += 1

    if return_string:
        return sink.getvalue()
    return None


def optimize(pickle):
    """Return a new pickle with unused PUT/MEMOIZE ops stripped.

    Walks the input twice:
      * first pass collects which memo ids are referenced by GET ops,
      * second pass copies all bytes verbatim except PUT-family ops whose
        memo id has no corresponding GET.

    This is a structural optimization that preserves the deserialized value.
    """
    if isinstance(pickle, bytearray):
        pickle = bytes(pickle)
    if not isinstance(pickle, bytes):
        raise TypeError("optimize() expects bytes-like input")

    # Pass 1 — figure out which memo slots are read.
    used = set()
    memo_counter = 0  # auto-incrementing id used by MEMOIZE
    put_ids = []      # aligned to MEMOIZE / PUT order
    for offset, name, arg, nxt in _iter_ops(pickle):
        if name in _GET_NAMES:
            try:
                idx = int(arg) if name == "GET" else int(arg)
            except (TypeError, ValueError):
                idx = arg
            used.add(idx)
        elif name == "MEMOIZE":
            put_ids.append(memo_counter)
            memo_counter += 1
        elif name in ("PUT", "BINPUT", "LONG_BINPUT"):
            try:
                idx = int(arg)
            except (TypeError, ValueError):
                idx = arg
            put_ids.append(idx)

    # Pass 2 — emit, dropping unused PUT/MEMOIZE ops.
    out = bytearray()
    memo_counter = 0
    put_index = 0
    for offset, name, arg, nxt in _iter_ops(pickle):
        if name in _PUT_NAMES:
            this_id = put_ids[put_index]
            put_index += 1
            if name == "MEMOIZE":
                memo_counter += 1
            if this_id in used:
                out.extend(pickle[offset:nxt])
            # else: skip the bytes entirely
        else:
            out.extend(pickle[offset:nxt])
    return bytes(out)


# ---------------------------------------------------------------------------
# Invariant probes
# ---------------------------------------------------------------------------

def _self_test_opcodes():
    table = opcodes()
    if not isinstance(table, list) or not table:
        return False
    seen = set()
    for entry in table:
        if not (isinstance(entry, tuple) and len(entry) == 3):
            return False
        name, byte, kind = entry
        if not isinstance(name, str) or not isinstance(byte, bytes):
            return False
        if len(byte) != 1:
            return False
        if byte in seen:
            return False
        seen.add(byte)
    # A few well-known opcodes must be present.
    names = {n for (n, _b, _k) in table}
    must_have = {"MARK", "STOP", "EMPTY_LIST", "EMPTY_DICT", "PROTO",
                 "BININT1", "TUPLE2", "MEMOIZE", "BINGET"}
    return must_have.issubset(names)


def _build_sample_pickle():
    """Build a small, hand-crafted protocol-2 pickle equivalent to (1, 2, 3).

    Hand-rolled here so the test does not depend on the stdlib `pickle`.
    """
    parts = []
    parts.append(b"\x80\x02")          # PROTO 2
    parts.append(b"K\x01")              # BININT1 1
    parts.append(b"q\x00")              # BINPUT 0   (unused -> optimized away)
    parts.append(b"K\x02")              # BININT1 2
    parts.append(b"q\x01")              # BINPUT 1   (used)
    parts.append(b"K\x03")              # BININT1 3
    parts.append(b"\x87")               # TUPLE3
    parts.append(b"q\x02")              # BINPUT 2   (unused)
    parts.append(b"h\x01")              # BINGET 1   (consumes memo 1)
    parts.append(b"0")                  # POP        (drop the duplicate)
    parts.append(b".")                  # STOP
    return b"".join(parts)


def _self_test_dis():
    pkl = _build_sample_pickle()
    text = dis(pkl)
    if not isinstance(text, str):
        return False
    expected_tokens = ("PROTO", "BININT1", "BINPUT", "TUPLE3", "BINGET",
                       "POP", "STOP")
    return all(tok in text for tok in expected_tokens)


def _self_test_optimize():
    pkl = _build_sample_pickle()
    smaller = optimize(pkl)
    if not isinstance(smaller, bytes):
        return False
    if len(smaller) >= len(pkl):
        return False
    # The unused BINPUT 0 / BINPUT 2 must be gone, BINPUT 1 must remain.
    # We re-disassemble and count BINPUT occurrences.
    text = dis(smaller)
    if text.count("BINPUT") != 1:
        return False
    # The optimized stream must still parse end-to-end.
    ops = list(_iter_ops(smaller))
    return ops[-1][1] == "STOP"


def pickletools2_opcodes():
    try:
        return _self_test_opcodes()
    except Exception:
        return False


def pickletools2_dis():
    try:
        return _self_test_dis()
    except Exception:
        return False


def pickletools2_optimize():
    try:
        return _self_test_optimize()
    except Exception:
        return False


__all__ = [
    "opcodes",
    "dis",
    "optimize",
    "pickletools2_opcodes",
    "pickletools2_dis",
    "pickletools2_optimize",
]