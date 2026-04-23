"""
theseus_dis_cr — Clean-room dis module.
No import of the standard `dis` module.
Uses _opcode and _opcode_metadata C extensions directly.
"""

import sys as _sys
import types as _types
import _opcode as _c_opcode
from _opcode_metadata import opmap as _opmap, _specialized_opmap, HAVE_ARGUMENT

HAVE_ARGUMENT = HAVE_ARGUMENT

_opname = ['<%r>' % (op,) for op in range(max(_opmap.values()) + 1)]
for _m in (_opmap, _specialized_opmap):
    for _op, _i in _m.items():
        _opname[_i] = _op

opmap = _opmap
opname = _opname
cmp_op = ('<', '<=', '==', '!=', '>', '>=')
EXTENDED_ARG = _opmap.get('EXTENDED_ARG', 144)

from collections import namedtuple as _namedtuple

# Instruction named tuple - subset of fields for compatibility
class Instruction(_namedtuple('Instruction', [
    'opname', 'opcode', 'arg', 'argval', 'argrepr',
    'offset', 'starts_line', 'is_jump_target',
])):
    """Details for a bytecode operation."""
    __slots__ = ()

    def _disassemble(self, lineno_width=3, mark_as_current=False, offset_width=4):
        fields = []
        if lineno_width:
            if self.starts_line:
                fields.append(str(self.starts_line).rjust(lineno_width))
            else:
                fields.append(' ' * lineno_width)
        if self.is_jump_target:
            fields.append('>>')
        else:
            fields.append('  ')
        fields.append(repr(self.offset).rjust(offset_width))
        fields.append(self.opname.ljust(20))
        if self.arg is not None:
            fields.append(repr(self.arg).rjust(5))
            if self.argrepr:
                fields.append('(' + self.argrepr + ')')
        return ' '.join(fields)


def _get_code_object(x):
    """Return code object from function, method, code, or string."""
    if isinstance(x, str):
        return compile(x, '<string>', 'exec')
    if isinstance(x, _types.MethodType):
        x = x.__func__
    if isinstance(x, _types.FunctionType):
        return x.__code__
    if isinstance(x, _types.CodeType):
        return x
    if isinstance(x, type):
        raise TypeError('expected code object, not %s' % type(x).__name__)
    raise TypeError('expected code object, not %s' % type(x).__name__)


def _unpack_opargs(code):
    """Yield (offset, opcode, arg) triples from bytecode."""
    i = 0
    extended_arg = 0
    n = len(code)
    while i < n:
        op = code[i]
        offset = i
        i += 1
        if op == EXTENDED_ARG:
            arg = code[i]
            i += 1
            extended_arg = (extended_arg | arg) << 8
        elif op >= HAVE_ARGUMENT:
            arg = code[i]
            i += 1
            arg = arg | extended_arg
            extended_arg = 0
            yield offset, op, arg
        else:
            extended_arg = 0
            yield offset, op, None


def findlinestarts(code):
    """Find the offsets in a byte code which are start of lines in the source."""
    lastline = None
    for start, end, line in code.co_lines():
        if line is not None and line != lastline:
            lastline = line
            yield start, line


def findlabels(code):
    """Detect all offsets in a byte code which are jump targets."""
    labels = set()
    bytecode = code.co_code
    for offset, op, arg in _unpack_opargs(bytecode):
        if arg is not None and _c_opcode.has_jump(op):
            labels.add(arg)
    return labels


def _get_const_info(const_index, const_list):
    argval = const_index
    if const_list is not None and const_index < len(const_list):
        argval = const_list[const_index]
        argrepr = repr(argval)
    else:
        argrepr = ''
    return argval, argrepr


def _get_name_info(name_index, getname):
    if getname is not None:
        argval = getname(name_index)
        argrepr = argval
    else:
        argval = name_index
        argrepr = ''
    return argval, argrepr


def get_instructions(x, *, first_line=None, show_caches=False, adaptive=False):
    """Iterator over the instructions in the supplied callable."""
    co = _get_code_object(x)
    return _get_instructions_bytes(co, first_line=first_line)


def _get_instructions_bytes(co, first_line=None):
    """Generate Instructions for a code object."""
    bytecode = co.co_code
    labels = findlabels(co)
    starts_line = None
    linestarts = dict(findlinestarts(co))

    for offset, op, arg in _unpack_opargs(bytecode):
        lineno = linestarts.get(offset)
        if lineno is not None:
            starts_line = lineno

        is_jump_target = offset in labels
        opname_str = _opname[op] if op < len(_opname) else '<%d>' % op
        argval = arg
        argrepr = ''

        if arg is not None:
            if _c_opcode.has_const(op):
                argval, argrepr = _get_const_info(arg, co.co_consts)
            elif _c_opcode.has_name(op):
                try:
                    if arg < len(co.co_names):
                        argval = co.co_names[arg]
                        argrepr = argval
                except Exception:
                    pass
            elif _c_opcode.has_local(op):
                try:
                    varnames = co.co_varnames
                    if arg < len(varnames):
                        argval = varnames[arg]
                        argrepr = argval
                except Exception:
                    pass
            elif _c_opcode.has_jump(op):
                argval = arg
                argrepr = 'to ' + repr(arg)
            else:
                argrepr = repr(arg)

        yield Instruction(
            opname=opname_str,
            opcode=op,
            arg=arg,
            argval=argval,
            argrepr=argrepr,
            offset=offset,
            starts_line=starts_line if starts_line == linestarts.get(offset) else None,
            is_jump_target=is_jump_target,
        )


def dis(x=None, *, file=None, depth=None, show_caches=False, adaptive=False):
    """Disassemble classes, methods, functions, or code."""
    if x is None:
        import sys
        frame = sys._getframe(1)
        x = frame.f_code
    if isinstance(x, type):
        for name in dir(x):
            val = getattr(x, name)
            if isinstance(val, (_types.MethodType, _types.FunctionType)):
                if file:
                    print('Disassembly of %s:' % name, file=file)
                else:
                    print('Disassembly of %s:' % name)
                disassemble(val.__code__, file=file)
        return
    try:
        co = _get_code_object(x)
    except TypeError:
        return
    disassemble(co, file=file)


def disassemble(co, lasti=-1, *, file=None, show_caches=False, adaptive=False):
    """Disassemble a code object."""
    linestarts = dict(findlinestarts(co))
    labels = findlabels(co)
    for instr in _get_instructions_bytes(co):
        new_source_line = instr.offset in linestarts
        if new_source_line:
            line_no = linestarts[instr.offset]
            print('%3d' % line_no, end=' ', file=file)
        else:
            print('   ', end=' ', file=file)
        if instr.is_jump_target:
            print('>>', end=' ', file=file)
        else:
            print('  ', end=' ', file=file)
        if instr.offset == lasti:
            print('-->', end=' ', file=file)
        else:
            print('   ', end=' ', file=file)
        print(repr(instr.offset).rjust(4), end=' ', file=file)
        print(instr.opname.ljust(20), end=' ', file=file)
        if instr.arg is not None:
            print(repr(instr.arg).rjust(5), end=' ', file=file)
            if instr.argrepr:
                print('(' + instr.argrepr + ')', end=' ', file=file)
        print(file=file)


def code_info(x):
    """Return a formatted multi-line string for a code object."""
    co = _get_code_object(x)
    lines = []
    lines.append('Name:              %s' % co.co_name)
    lines.append('Filename:          %s' % co.co_filename)
    lines.append('Argument count:    %d' % co.co_argcount)
    lines.append('Kw-only arguments: %d' % co.co_kwonlyargcount)
    lines.append('Number of locals:  %d' % co.co_nlocals)
    return '\n'.join(lines)


def stack_effect(opcode, oparg=None, *, jump=None):
    """Return the stack effect of the given opcode."""
    return _c_opcode.stack_effect(opcode, oparg, jump=jump)


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def dis2_get_instructions():
    """get_instructions() yields Instruction objects for a function; returns True."""
    def sample():
        return 1 + 2
    instrs = list(get_instructions(sample))
    return len(instrs) > 0 and isinstance(instrs[0], Instruction)


def dis2_findlinestarts():
    """findlinestarts() yields (offset, lineno) pairs; returns True."""
    def sample():
        x = 1
        return x
    pairs = list(findlinestarts(sample.__code__))
    return len(pairs) > 0 and all(isinstance(o, int) and isinstance(l, int) for o, l in pairs)


def dis2_opname():
    """opname mapping exists and LOAD_CONST is in it; returns True."""
    return 'LOAD_CONST' in opmap and opname[opmap['LOAD_CONST']] == 'LOAD_CONST'


__all__ = [
    'dis', 'disassemble', 'code_info', 'get_instructions',
    'findlinestarts', 'findlabels', 'stack_effect',
    'Instruction', 'opmap', 'opname', 'cmp_op',
    'HAVE_ARGUMENT', 'EXTENDED_ARG',
    'dis2_get_instructions', 'dis2_findlinestarts', 'dis2_opname',
]
