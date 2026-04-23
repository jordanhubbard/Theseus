"""
theseus_ast_cr — Clean-room ast module.
No import of the standard `ast` module.
Uses _ast C extension directly.
"""

import _ast as _c_ast
import sys as _sys

AST = _c_ast.AST
PyCF_ONLY_AST = _c_ast.PyCF_ONLY_AST
PyCF_ALLOW_TOP_LEVEL_AWAIT = getattr(_c_ast, 'PyCF_ALLOW_TOP_LEVEL_AWAIT', 0x2000)
PyCF_TYPE_COMMENTS = getattr(_c_ast, 'PyCF_TYPE_COMMENTS', 0x1000)

# Re-export all AST node classes from _ast
for _name in dir(_c_ast):
    if not _name.startswith('_'):
        _sys.modules[__name__].__dict__[_name] = getattr(_c_ast, _name)

Module = _c_ast.Module
Expression = _c_ast.Expression
Interactive = _c_ast.Interactive

stmt = _c_ast.stmt
FunctionDef = _c_ast.FunctionDef
AsyncFunctionDef = _c_ast.AsyncFunctionDef
ClassDef = _c_ast.ClassDef
Return = _c_ast.Return
Delete = _c_ast.Delete
Assign = _c_ast.Assign
AugAssign = _c_ast.AugAssign
AnnAssign = _c_ast.AnnAssign
For = _c_ast.For
AsyncFor = _c_ast.AsyncFor
While = _c_ast.While
If = _c_ast.If
With = _c_ast.With
AsyncWith = _c_ast.AsyncWith
Raise = _c_ast.Raise
Try = _c_ast.Try
Assert = _c_ast.Assert
Import = _c_ast.Import
ImportFrom = _c_ast.ImportFrom
Global = _c_ast.Global
Nonlocal = _c_ast.Nonlocal
Expr = _c_ast.Expr
Pass = _c_ast.Pass
Break = _c_ast.Break
Continue = _c_ast.Continue

expr = _c_ast.expr
BoolOp = _c_ast.BoolOp
BinOp = _c_ast.BinOp
UnaryOp = _c_ast.UnaryOp
Lambda = _c_ast.Lambda
IfExp = _c_ast.IfExp
Dict = _c_ast.Dict
Set = _c_ast.Set
ListComp = _c_ast.ListComp
SetComp = _c_ast.SetComp
DictComp = _c_ast.DictComp
GeneratorExp = _c_ast.GeneratorExp
Await = _c_ast.Await
Yield = _c_ast.Yield
YieldFrom = _c_ast.YieldFrom
Compare = _c_ast.Compare
Call = _c_ast.Call
FormattedValue = _c_ast.FormattedValue
JoinedStr = _c_ast.JoinedStr
Constant = _c_ast.Constant
Attribute = _c_ast.Attribute
Subscript = _c_ast.Subscript
Starred = _c_ast.Starred
Name = _c_ast.Name
List = _c_ast.List
Tuple = _c_ast.Tuple
Slice = _c_ast.Slice

expr_context = _c_ast.expr_context
Load = _c_ast.Load
Store = _c_ast.Store
Del = _c_ast.Del

boolop = _c_ast.boolop
And = _c_ast.And
Or = _c_ast.Or
operator = _c_ast.operator
Add = _c_ast.Add
Sub = _c_ast.Sub
Mult = _c_ast.Mult
MatMult = _c_ast.MatMult
Div = _c_ast.Div
Mod = _c_ast.Mod
Pow = _c_ast.Pow
LShift = _c_ast.LShift
RShift = _c_ast.RShift
BitOr = _c_ast.BitOr
BitXor = _c_ast.BitXor
BitAnd = _c_ast.BitAnd
FloorDiv = _c_ast.FloorDiv
unaryop = _c_ast.unaryop
Invert = _c_ast.Invert
Not = _c_ast.Not
UAdd = _c_ast.UAdd
USub = _c_ast.USub
cmpop = _c_ast.cmpop
Eq = _c_ast.Eq
NotEq = _c_ast.NotEq
Lt = _c_ast.Lt
LtE = _c_ast.LtE
Gt = _c_ast.Gt
GtE = _c_ast.GtE
Is = _c_ast.Is
IsNot = _c_ast.IsNot
In = _c_ast.In
NotIn = _c_ast.NotIn

comprehension = _c_ast.comprehension
excepthandler = _c_ast.excepthandler
ExceptHandler = _c_ast.ExceptHandler
arguments = _c_ast.arguments
arg = _c_ast.arg
keyword = _c_ast.keyword
alias = _c_ast.alias
withitem = _c_ast.withitem


def parse(source, filename='<unknown>', mode='exec', *,
          type_comments=False, feature_version=None):
    flags = PyCF_ONLY_AST
    if type_comments:
        flags |= PyCF_TYPE_COMMENTS
    return compile(source, filename, mode, flags)


def dump(node, annotate_fields=True, include_attributes=False, *, indent=None):
    def _format(node, level=0):
        if isinstance(node, AST):
            fields = [(a, _format(b, level)) for a, b in iter_fields(node)]
            if annotate_fields:
                asfmt = ', '.join('%s=%s' % field for field in fields)
            else:
                asfmt = ', '.join(b for a, b in fields)
            return '%s(%s)' % (node.__class__.__name__, asfmt)
        elif isinstance(node, list):
            if not node:
                return '[]'
            return '[%s]' % ', '.join(_format(x, level) for x in node)
        else:
            return repr(node)
    if not isinstance(node, AST):
        raise TypeError('expected AST, got %r' % node.__class__.__name__)
    return _format(node)


def iter_fields(node):
    for field in node._fields:
        try:
            yield field, getattr(node, field)
        except AttributeError:
            pass


def iter_child_nodes(node):
    for name, field in iter_fields(node):
        if isinstance(field, AST):
            yield field
        elif isinstance(field, list):
            for item in field:
                if isinstance(item, AST):
                    yield item


def walk(node):
    from collections import deque
    todo = deque([node])
    while todo:
        node = todo.popleft()
        todo.extend(iter_child_nodes(node))
        yield node


def copy_location(new_node, old_node):
    for attr in ('lineno', 'col_offset', 'end_lineno', 'end_col_offset'):
        if hasattr(old_node, attr):
            setattr(new_node, attr, getattr(old_node, attr))
    return new_node


def fix_missing_locations(node):
    def _fix(node, lineno, col_offset, end_lineno, end_col_offset):
        if 'lineno' in node._attributes:
            if not hasattr(node, 'lineno'):
                node.lineno = lineno
            else:
                lineno = node.lineno
        if 'col_offset' in node._attributes:
            if not hasattr(node, 'col_offset'):
                node.col_offset = col_offset
            else:
                col_offset = node.col_offset
        for child in iter_child_nodes(node):
            _fix(child, lineno, col_offset, end_lineno, end_col_offset)
    _fix(node, 1, 0, 1, 0)
    return node


def get_docstring(node, clean=True):
    if not (node.body and isinstance(node.body[0], Expr)):
        return None
    node = node.body[0].value
    if isinstance(node, Constant) and isinstance(node.value, str):
        text = node.value
        if clean:
            import inspect
            return inspect.cleandoc(text)
        return text
    return None


class NodeVisitor:
    def visit(self, node):
        method = 'visit_' + node.__class__.__name__
        visitor = getattr(self, method, self.generic_visit)
        return visitor(node)

    def generic_visit(self, node):
        for field, value in iter_fields(node):
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, AST):
                        self.visit(item)
            elif isinstance(value, AST):
                self.visit(value)


class NodeTransformer(NodeVisitor):
    def generic_visit(self, node):
        for field, old_value in iter_fields(node):
            if isinstance(old_value, list):
                new_values = []
                for old_node in old_value:
                    if isinstance(old_node, AST):
                        value = self.visit(old_node)
                        if value is None:
                            continue
                        elif not isinstance(value, AST):
                            new_values.extend(value)
                            continue
                        new_values.append(value)
                    else:
                        new_values.append(old_node)
                old_value[:] = new_values
            elif isinstance(old_value, AST):
                new_node = self.visit(old_value)
                if new_node is None:
                    delattr(node, field)
                else:
                    setattr(node, field, new_node)
        return node


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def ast2_parse():
    """parse() returns an AST Module node for a simple expression; returns True."""
    tree = parse('x = 1 + 2')
    return isinstance(tree, Module)


def ast2_dump():
    """dump() produces a string representation of an AST; returns True."""
    tree = parse('1 + 2')
    s = dump(tree)
    return isinstance(s, str) and 'BinOp' in s


def ast2_walk():
    """walk() yields all nodes in an AST; returns True."""
    tree = parse('x = 1 + 2')
    nodes = list(walk(tree))
    types = {type(n).__name__ for n in nodes}
    return 'Module' in types and len(nodes) > 3


__all__ = [
    'AST', 'parse', 'dump', 'copy_location', 'fix_missing_locations',
    'iter_fields', 'iter_child_nodes', 'walk', 'get_docstring',
    'NodeVisitor', 'NodeTransformer',
    'PyCF_ONLY_AST', 'PyCF_ALLOW_TOP_LEVEL_AWAIT', 'PyCF_TYPE_COMMENTS',
    'Module', 'Expression', 'Interactive',
    'FunctionDef', 'AsyncFunctionDef', 'ClassDef', 'Return', 'Delete',
    'Assign', 'AugAssign', 'AnnAssign', 'For', 'AsyncFor', 'While',
    'If', 'With', 'AsyncWith', 'Raise', 'Try', 'Assert',
    'Import', 'ImportFrom', 'Global', 'Nonlocal', 'Expr', 'Pass', 'Break', 'Continue',
    'BoolOp', 'BinOp', 'UnaryOp', 'Lambda', 'IfExp', 'Dict', 'Set',
    'ListComp', 'SetComp', 'DictComp', 'GeneratorExp', 'Await', 'Yield', 'YieldFrom',
    'Compare', 'Call', 'FormattedValue', 'JoinedStr', 'Constant',
    'Attribute', 'Subscript', 'Starred', 'Name', 'List', 'Tuple', 'Slice',
    'Load', 'Store', 'Del',
    'And', 'Or', 'Add', 'Sub', 'Mult', 'MatMult', 'Div', 'Mod', 'Pow',
    'LShift', 'RShift', 'BitOr', 'BitXor', 'BitAnd', 'FloorDiv',
    'Invert', 'Not', 'UAdd', 'USub',
    'Eq', 'NotEq', 'Lt', 'LtE', 'Gt', 'GtE', 'Is', 'IsNot', 'In', 'NotIn',
    'comprehension', 'ExceptHandler', 'arguments', 'arg', 'keyword', 'alias', 'withitem',
    'ast2_parse', 'ast2_dump', 'ast2_walk',
]
