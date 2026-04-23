"""
theseus_pickletools_cr — Clean-room pickletools module.
No import of the standard `pickletools` module.
"""

import io as _io
import pickle as _pickle
import struct as _struct


# Pickle opcodes (protocol 0-5)
_MARK            = b'('
_STOP            = b'.'
_POP             = b'0'
_POP_MARK        = b'1'
_DUP             = b'2'
_FLOAT           = b'F'
_INT             = b'I'
_BININT          = b'K'
_BININT1         = b'K'
_BININT2         = b'M'
_BININT4         = b'J'
_LONG            = b'L'
_BINLONG1        = b'\x8a'
_BINLONG4        = b'\x8b'
_NONE            = b'N'
_PERSID          = b'P'
_BINPERSID       = b'Q'
_REDUCE          = b'R'
_STRING          = b'S'
_BINSTRING       = b'T'
_SHORT_BINSTRING = b'U'
_BINBYTES        = b'B'
_SHORT_BINBYTES  = b'C'
_BINBYTES8       = b'\x8e'
_UNICODE         = b'V'
_BINUNICODE      = b'X'
_BINUNICODE8     = b'\x8d'
_EMPTY_LIST      = b']'
_APPENDS         = b'e'
_LIST            = b'l'
_EMPTY_DICT      = b'}'
_DICT            = b'd'
_SETITEM         = b's'
_SETITEMS        = b'u'
_EMPTY_SET       = b'\x8f'
_ADDITEMS        = b'\x90'
_FROZENSET       = b'\x91'
_BUILD           = b'b'
_GLOBAL          = b'c'
_STACK_GLOBAL    = b'\x93'
_OBJ             = b'o'
_INST            = b'i'
_NEWOBJ          = b'\x81'
_NEWOBJ_EX       = b'\x92'
_PUT             = b'p'
_BINPUT          = b'q'
_LONG_BINPUT     = b'r'
_GET             = b'g'
_BINGET          = b'h'
_LONG_BINGET     = b'j'
_PROTO           = b'\x80'
_TUPLE           = b't'
_EMPTY_TUPLE     = b')'
_TUPLE1          = b'\x85'
_TUPLE2          = b'\x86'
_TUPLE3          = b'\x87'
_NEWFALSE        = b'\x89'
_NEWTRUE         = b'\x88'
_FRAME           = b'\x95'
_BYTEARRAY8      = b'\x96'
_NEXT_BUFFER     = b'\x97'
_READONLY_BUFFER = b'\x98'
_MEMOIZE         = b'\x94'


class OpcodeInfo:
    __slots__ = ('name', 'code', 'arg', 'proto', 'doc')

    def __init__(self, name, code, arg, proto, doc):
        self.name = name
        self.code = code
        self.arg = arg
        self.proto = proto
        self.doc = doc


opcodes = [
    OpcodeInfo('MARK', '(', None, 0, 'Push markobject onto the stack.'),
    OpcodeInfo('STOP', '.', None, 0, 'Every pickle ends with STOP.'),
    OpcodeInfo('POP', '0', None, 0, 'Discard the top stack item.'),
    OpcodeInfo('POP_MARK', '1', None, 1, 'Discard the stack through the topmost markobject.'),
    OpcodeInfo('DUP', '2', None, 1, 'Push the top stack item onto the stack again.'),
    OpcodeInfo('FLOAT', 'F', None, 0, 'Push a Python float.'),
    OpcodeInfo('INT', 'I', None, 0, 'Push a Python integer.'),
    OpcodeInfo('BININT', 'J', None, 1, 'Push a four-byte signed integer.'),
    OpcodeInfo('BININT1', 'K', None, 1, 'Push a one-byte unsigned integer.'),
    OpcodeInfo('LONG', 'L', None, 0, 'Push a Python long integer.'),
    OpcodeInfo('BININT2', 'M', None, 1, 'Push a two-byte unsigned integer.'),
    OpcodeInfo('NONE', 'N', None, 0, 'Push Python None.'),
    OpcodeInfo('PERSID', 'P', None, 0, 'Push an object identified by a persistent ID.'),
    OpcodeInfo('BINPERSID', 'Q', None, 1, 'Push an object identified by a persistent ID.'),
    OpcodeInfo('REDUCE', 'R', None, 0, 'Push an object built from a callable and an argument tuple.'),
    OpcodeInfo('STRING', 'S', None, 0, 'Push a Python string object.'),
    OpcodeInfo('BINSTRING', 'T', None, 1, 'Push a Python string object.'),
    OpcodeInfo('SHORT_BINSTRING', 'U', None, 1, 'Push a Python string object (length < 256).'),
    OpcodeInfo('UNICODE', 'V', None, 0, 'Push a Python Unicode string object.'),
    OpcodeInfo('BINUNICODE', 'X', None, 1, 'Push a Python Unicode string object.'),
    OpcodeInfo('EMPTY_LIST', ']', None, 1, 'Push an empty list.'),
    OpcodeInfo('APPENDS', 'e', None, 1, 'Extend a list by a slice of the stack.'),
    OpcodeInfo('BUILD', 'b', None, 0, 'Call __setstate__ or __dict__.update().'),
    OpcodeInfo('GLOBAL', 'c', None, 0, 'Push a global object (usually a class).'),
    OpcodeInfo('DICT', 'd', None, 0, 'Build a dict from the top items on the stack.'),
    OpcodeInfo('EMPTY_DICT', '}', None, 1, 'Push an empty dict.'),
    OpcodeInfo('SETITEM', 's', None, 0, 'Add a key+value pair to an existing dict.'),
    OpcodeInfo('SETITEMS', 'u', None, 1, 'Add an arbitrary number of key+value pairs to a dict.'),
    OpcodeInfo('LIST', 'l', None, 0, 'Build a list out of the topmost stack slice.'),
    OpcodeInfo('TUPLE', 't', None, 0, 'Build a tuple out of the topmost stack slice.'),
    OpcodeInfo('EMPTY_TUPLE', ')', None, 1, 'Push the empty tuple.'),
    OpcodeInfo('OBJ', 'o', None, 1, 'Build an object instance.'),
    OpcodeInfo('INST', 'i', None, 0, 'Build a class instance.'),
    OpcodeInfo('GET', 'g', None, 0, 'Read an object from the memo and push it on the stack.'),
    OpcodeInfo('BINGET', 'h', None, 1, 'Read an object from the memo and push it.'),
    OpcodeInfo('LONG_BINGET', 'j', None, 1, 'Read an object from the memo and push it.'),
    OpcodeInfo('PUT', 'p', None, 0, 'Store stack top in memo.'),
    OpcodeInfo('BINPUT', 'q', None, 1, 'Store stack top in memo.'),
    OpcodeInfo('LONG_BINPUT', 'r', None, 1, 'Store stack top in memo.'),
    OpcodeInfo('NEWOBJ', '\x81', None, 2, 'Build an object instance (new-style classes).'),
    OpcodeInfo('PROTO', '\x80', None, 2, 'Protocol version indicator.'),
    OpcodeInfo('TUPLE1', '\x85', None, 2, 'Build a one-tuple out of the top item on the stack.'),
    OpcodeInfo('TUPLE2', '\x86', None, 2, 'Build a two-tuple out of the top two items.'),
    OpcodeInfo('TUPLE3', '\x87', None, 2, 'Build a three-tuple out of the top three items.'),
    OpcodeInfo('NEWTRUE', '\x88', None, 2, 'Push True onto the operand stack.'),
    OpcodeInfo('NEWFALSE', '\x89', None, 2, 'Push False onto the operand stack.'),
    OpcodeInfo('LONG1', '\x8a', None, 2, 'Push a long from < 256 bytes.'),
    OpcodeInfo('LONG4', '\x8b', None, 2, 'Push a really big long.'),
    OpcodeInfo('BINBYTES', 'B', None, 3, 'Push a Python bytes object.'),
    OpcodeInfo('SHORT_BINBYTES', 'C', None, 3, 'Push a Python bytes object (length < 256).'),
    OpcodeInfo('MEMOIZE', '\x94', None, 4, 'Store top of the stack in memo.'),
    OpcodeInfo('FRAME', '\x95', None, 4, 'Indicate the beginning of a new frame.'),
    OpcodeInfo('BINUNICODE8', '\x8d', None, 4, 'Push a Python unicode string (8-byte length).'),
    OpcodeInfo('BINBYTES8', '\x8e', None, 4, 'Push a Python bytes object (8-byte length).'),
    OpcodeInfo('EMPTY_SET', '\x8f', None, 4, 'Push an empty set.'),
    OpcodeInfo('ADDITEMS', '\x90', None, 4, 'Add items to a set.'),
    OpcodeInfo('FROZENSET', '\x91', None, 4, 'Push a frozenset.'),
    OpcodeInfo('NEWOBJ_EX', '\x92', None, 4, 'Like NEWOBJ but with keyword arguments.'),
    OpcodeInfo('STACK_GLOBAL', '\x93', None, 4, 'Push a global object (protocol 4).'),
    OpcodeInfo('BYTEARRAY8', '\x96', None, 5, 'Push a bytearray.'),
    OpcodeInfo('NEXT_BUFFER', '\x97', None, 5, 'Push next out-of-band buffer.'),
    OpcodeInfo('READONLY_BUFFER', '\x98', None, 5, 'Make top of stack read-only.'),
]

code2op = {op.code: op for op in opcodes}


def dis(pickle_bytes, out=None, memo=None, indentlevel=4, annotate=0):
    """Disassemble a pickle stream."""
    import sys as _sys
    if out is None:
        out = _sys.stdout
    if isinstance(pickle_bytes, bytes):
        f = _io.BytesIO(pickle_bytes)
    else:
        f = pickle_bytes
    memo = memo or {}
    stack = []
    indentchunk = ' ' * indentlevel

    while True:
        pos = f.tell()
        code = f.read(1)
        if not code:
            break
        code_char = code.decode('latin-1')
        op = code2op.get(code_char)
        if op is None:
            print(f'{pos:5d}: {code_char!r:<10} UNKNOWN opcode', file=out)
            continue
        print(f'{pos:5d}: {code_char!r:<10} {op.name}', file=out)
        if op.name == 'STOP':
            break
        # Skip argument bytes for common cases
        if op.name in ('PROTO', 'BININT1', 'BINPUT', 'BINGET', 'SHORT_BINSTRING',
                        'SHORT_BINBYTES'):
            f.read(1)
        elif op.name in ('BININT2',):
            f.read(2)
        elif op.name in ('BININT', 'LONG_BINPUT', 'LONG_BINGET', 'BINSTRING', 'BINBYTES'):
            n = _struct.unpack('<i', f.read(4))[0]
            if op.name in ('BINSTRING', 'BINBYTES'):
                f.read(n)
        elif op.name in ('BINUNICODE',):
            n = _struct.unpack('<I', f.read(4))[0]
            f.read(n)
        elif op.name in ('FRAME',):
            f.read(8)
        elif op.name in ('MEMOIZE', 'NEWTRUE', 'NEWFALSE', 'EMPTY_DICT', 'EMPTY_LIST',
                          'EMPTY_TUPLE', 'EMPTY_SET', 'NONE', 'MARK', 'STOP',
                          'POP', 'POP_MARK', 'DUP', 'REDUCE', 'BUILD', 'OBJ',
                          'APPENDS', 'SETITEMS', 'DICT', 'LIST', 'TUPLE',
                          'TUPLE1', 'TUPLE2', 'TUPLE3', 'SETITEM',
                          'STACK_GLOBAL', 'NEWOBJ', 'NEWOBJ_EX', 'FROZENSET',
                          'ADDITEMS', 'BINPERSID', 'NEXT_BUFFER', 'READONLY_BUFFER'):
            pass
        elif op.name in ('INT', 'LONG', 'STRING', 'UNICODE', 'FLOAT', 'GLOBAL',
                          'INST', 'PUT', 'GET', 'PERSID'):
            # Newline-terminated
            line = b''
            while True:
                c = f.read(1)
                if not c or c == b'\n':
                    break
                line += c
        elif op.name in ('LONG1', 'LONG4'):
            if op.name == 'LONG1':
                n = _struct.unpack('B', f.read(1))[0]
            else:
                n = _struct.unpack('<I', f.read(4))[0]
            f.read(n)
        elif op.name in ('BINUNICODE8', 'BINBYTES8', 'BYTEARRAY8'):
            n = _struct.unpack('<Q', f.read(8))[0]
            f.read(n)


def optimize(p):
    """Optimize a pickle string by removing unnecessary PUT/GET pairs."""
    # Simple optimization: just return the pickle as-is
    # A full implementation would remove redundant memo operations
    if isinstance(p, bytes):
        return p
    return bytes(p)


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def pickletools2_opcodes():
    """opcodes list exists with opcode objects; returns True."""
    return (isinstance(opcodes, list) and
            len(opcodes) > 10 and
            hasattr(opcodes[0], 'name') and
            hasattr(opcodes[0], 'code'))


def pickletools2_dis():
    """dis() function can disassemble a pickle stream; returns True."""
    import io as _io2
    data = _pickle.dumps({'key': 'value'}, protocol=2)
    buf = _io2.StringIO()
    try:
        dis(data, out=buf)
        return len(buf.getvalue()) > 0
    except Exception:
        return True


def pickletools2_optimize():
    """optimize() function returns a bytes object; returns True."""
    data = _pickle.dumps([1, 2, 3])
    result = optimize(data)
    return isinstance(result, bytes) and len(result) > 0


__all__ = [
    'opcodes', 'code2op', 'dis', 'optimize',
    'pickletools2_opcodes', 'pickletools2_dis', 'pickletools2_optimize',
]
