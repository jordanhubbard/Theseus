"""
theseus_symtable_cr — Clean-room re-implementation of the symtable module.

This module does NOT import the original `symtable` package or its private
C-extension `_symtable`. Instead, it parses the source via the standard
`ast` module and the built-in `compile()` to derive symbol information.

It exposes the small surface area required by the Theseus invariants:
    - symtable(code, filename, compile_type) -> SymbolTable
    - SymbolTable.get_symbols() -> list[Symbol]
    - SymbolTable.lookup(name) -> Symbol
"""

import ast as _ast


# ---------------------------------------------------------------------------
# Public scope-flag constants (mirroring the canonical symtable module)
# ---------------------------------------------------------------------------

SCOPE_OFF = 11
SCOPE_MASK = 7

FREE = 4
LOCAL = 1
GLOBAL_IMPLICIT = 2
GLOBAL_EXPLICIT = 3
CELL = 5

DEF_GLOBAL = 1
DEF_LOCAL = 2
DEF_PARAM = 4
DEF_NONLOCAL = 8
DEF_USE = 16
DEF_FREE = 32
DEF_FREE_CLASS = 64
DEF_IMPORT = 128
DEF_BOUND = DEF_LOCAL | DEF_PARAM | DEF_IMPORT

OPT_IMPORT_STAR = 1
OPT_EXEC = 2
OPT_BARE_EXEC = 4

USE = DEF_USE


class SymbolTableError(Exception):
    """Raised on lookup of a name that is not present."""
    pass


# ---------------------------------------------------------------------------
# AST-driven symbol extraction
# ---------------------------------------------------------------------------

def _scope_kind_for(node):
    if isinstance(node, _ast.Module):
        return "module"
    if isinstance(node, (_ast.FunctionDef, _ast.AsyncFunctionDef, _ast.Lambda)):
        return "function"
    if isinstance(node, _ast.ClassDef):
        return "class"
    return "module"


def _scope_name_for(node):
    if isinstance(node, _ast.Module):
        return "top"
    if isinstance(node, (_ast.FunctionDef, _ast.AsyncFunctionDef, _ast.ClassDef)):
        return node.name
    if isinstance(node, _ast.Lambda):
        return "lambda"
    return "top"


def _scope_lineno_for(node):
    return getattr(node, "lineno", 0) or 0


def _is_scope(node):
    return isinstance(
        node,
        (_ast.Module, _ast.FunctionDef, _ast.AsyncFunctionDef,
         _ast.Lambda, _ast.ClassDef),
    )


def _extract_target_names(target, sink):
    if isinstance(target, _ast.Name):
        sink.append((target.id, DEF_LOCAL))
    elif isinstance(target, (_ast.Tuple, _ast.List)):
        for elt in target.elts:
            _extract_target_names(elt, sink)
    elif isinstance(target, _ast.Starred):
        _extract_target_names(target.value, sink)


def _walk_local_only(node, visit):
    for child in _ast.iter_child_nodes(node):
        visit(child)
        if not _is_scope(child):
            _walk_local_only(child, visit)


def _collect_symbols(scope_node):
    symbols = {}
    children = []

    def add(name, flag):
        if not isinstance(name, str) or not name:
            return
        symbols[name] = symbols.get(name, 0) | flag

    if isinstance(scope_node, (_ast.FunctionDef, _ast.AsyncFunctionDef, _ast.Lambda)):
        args = scope_node.args
        for a in list(args.args) + list(args.posonlyargs) + list(args.kwonlyargs):
            add(a.arg, DEF_PARAM)
        if args.vararg is not None:
            add(args.vararg.arg, DEF_PARAM)
        if args.kwarg is not None:
            add(args.kwarg.arg, DEF_PARAM)

    if isinstance(scope_node, _ast.Module):
        body_iter = scope_node.body
    elif isinstance(scope_node, _ast.Lambda):
        body_iter = [scope_node.body]
    else:
        body_iter = scope_node.body

    def visit(child):
        if isinstance(child, (_ast.FunctionDef, _ast.AsyncFunctionDef)):
            add(child.name, DEF_LOCAL)
            children.append(child)
            return
        if isinstance(child, _ast.ClassDef):
            add(child.name, DEF_LOCAL)
            children.append(child)
            return
        if isinstance(child, _ast.Lambda):
            children.append(child)
            return

        if isinstance(child, _ast.Assign):
            for tgt in child.targets:
                bound = []
                _extract_target_names(tgt, bound)
                for n, f in bound:
                    add(n, f)
        elif isinstance(child, _ast.AugAssign):
            bound = []
            _extract_target_names(child.target, bound)
            for n, f in bound:
                add(n, f | DEF_USE)
        elif isinstance(child, _ast.AnnAssign):
            bound = []
            _extract_target_names(child.target, bound)
            for n, f in bound:
                add(n, f)
        elif isinstance(child, _ast.For):
            bound = []
            _extract_target_names(child.target, bound)
            for n, f in bound:
                add(n, f)
        elif isinstance(child, _ast.AsyncFor):
            bound = []
            _extract_target_names(child.target, bound)
            for n, f in bound:
                add(n, f)
        elif isinstance(child, _ast.With):
            for item in child.items:
                if item.optional_vars is not None:
                    bound = []
                    _extract_target_names(item.optional_vars, bound)
                    for n, f in bound:
                        add(n, f)
        elif isinstance(child, _ast.AsyncWith):
            for item in child.items:
                if item.optional_vars is not None:
                    bound = []
                    _extract_target_names(item.optional_vars, bound)
                    for n, f in bound:
                        add(n, f)
        elif isinstance(child, _ast.Import):
            for alias in child.names:
                local = alias.asname if alias.asname else alias.name.split(".")[0]
                add(local, DEF_IMPORT)
        elif isinstance(child, _ast.ImportFrom):
            for alias in child.names:
                if alias.name == "*":
                    continue
                local = alias.asname if alias.asname else alias.name
                add(local, DEF_IMPORT)
        elif isinstance(child, _ast.Global):
            for n in child.names:
                add(n, DEF_GLOBAL)
        elif isinstance(child, _ast.Nonlocal):
            for n in child.names:
                add(n, DEF_NONLOCAL)
        elif isinstance(child, _ast.ExceptHandler):
            if child.name:
                add(child.name, DEF_LOCAL)
        elif isinstance(child, _ast.Name):
            if isinstance(child.ctx, _ast.Store):
                add(child.id, DEF_LOCAL)
            elif isinstance(child.ctx, (_ast.Load, _ast.Del)):
                add(child.id, DEF_USE)

    for stmt in body_iter:
        visit(stmt)
        if not _is_scope(stmt):
            _walk_local_only(stmt, visit)

    return symbols, children


# ---------------------------------------------------------------------------
# SymbolTable / Symbol classes
# ---------------------------------------------------------------------------

class Symbol:
    __slots__ = ("_name", "_flags", "_namespaces")

    def __init__(self, name, flags, namespaces=None):
        self._name = name
        self._flags = int(flags)
        self._namespaces = list(namespaces) if namespaces else []

    def get_name(self):
        return self._name

    def is_referenced(self):
        return bool(self._flags & DEF_USE)

    def is_parameter(self):
        return bool(self._flags & DEF_PARAM)

    def is_global(self):
        return bool(self._flags & (DEF_GLOBAL | DEF_FREE)) or False

    def is_nonlocal(self):
        return bool(self._flags & DEF_NONLOCAL)

    def is_declared_global(self):
        return bool(self._flags & DEF_GLOBAL)

    def is_local(self):
        return bool(self._flags & DEF_BOUND)

    def is_annotated(self):
        return False

    def is_free(self):
        return bool(self._flags & DEF_FREE)

    def is_imported(self):
        return bool(self._flags & DEF_IMPORT)

    def is_assigned(self):
        return bool(self._flags & DEF_LOCAL)

    def is_namespace(self):
        return bool(self._namespaces)

    def get_namespaces(self):
        return list(self._namespaces)

    def get_namespace(self):
        if len(self._namespaces) == 0:
            raise ValueError("name is not bound to any namespace")
        if len(self._namespaces) > 1:
            raise ValueError("name is bound to multiple namespaces")
        return self._namespaces[0]

    def __repr__(self):
        return "<symbol %r>" % (self._name,)


class SymbolTable:
    def __init__(self, scope_node, filename, parent=None):
        self._node = scope_node
        self._filename = filename
        self._parent = parent
        self._symbols, child_nodes = _collect_symbols(scope_node)
        self._children = [
            _build_subtable(c, filename, self) for c in child_nodes
        ]
        self._namespaces_by_name = {}
        for child in self._children:
            cname = child.get_name()
            self._namespaces_by_name.setdefault(cname, []).append(child)

    def get_type(self):
        return _scope_kind_for(self._node)

    def get_id(self):
        return id(self._node)

    def get_name(self):
        return _scope_name_for(self._node)

    def get_lineno(self):
        return _scope_lineno_for(self._node)

    def is_optimized(self):
        return isinstance(
            self._node, (_ast.FunctionDef, _ast.AsyncFunctionDef, _ast.Lambda)
        )

    def is_nested(self):
        return self._parent is not None and not isinstance(self._node, _ast.Module)

    def has_children(self):
        return bool(self._children)

    def get_identifiers(self):
        return list(self._symbols.keys())

    def get_symbols(self):
        out = []
        for name, flags in self._symbols.items():
            ns = self._namespaces_by_name.get(name, [])
            out.append(Symbol(name, flags, ns))
        return out

    def lookup(self, name):
        if name not in self._symbols:
            raise KeyError(name)
        ns = self._namespaces_by_name.get(name, [])
        return Symbol(name, self._symbols[name], ns)

    def get_children(self):
        return list(self._children)

    def __contains__(self, name):
        return name in self._symbols

    def __repr__(self):
        return "<%s SymbolTable for %s in %r>" % (
            self.get_type(), self.get_name(), self._filename,
        )


class FunctionSymbolTable(SymbolTable):
    def get_parameters(self):
        params = []
        if isinstance(self._node, (_ast.FunctionDef, _ast.AsyncFunctionDef, _ast.Lambda)):
            args = self._node.args
            for a in list(args.posonlyargs) + list(args.args) + list(args.kwonlyargs):
                params.append(a.arg)
            if args.vararg is not None:
                params.append(args.vararg.arg)
            if args.kwarg is not None:
                params.append(args.kwarg.arg)
        return tuple(params)

    def get_locals(self):
        return tuple(
            n for n, f in self._symbols.items() if f & DEF_BOUND
        )

    def get_globals(self):
        return tuple(
            n for n, f in self._symbols.items() if f & DEF_GLOBAL
        )

    def get_nonlocals(self):
        return tuple(
            n for n, f in self._symbols.items() if f & DEF_NONLOCAL
        )

    def get_frees(self):
        return tuple(
            n for n, f in self._symbols.items() if f & DEF_FREE
        )


class ClassSymbolTable(SymbolTable):
    def get_methods(self):
        methods = []
        for child in self._children:
            if child.get_type() == "function":
                methods.append(child.get_name())
        return tuple(methods)


def _build_subtable(scope_node, filename, parent):
    if isinstance(scope_node, (_ast.FunctionDef, _ast.AsyncFunctionDef, _ast.Lambda)):
        return FunctionSymbolTable(scope_node, filename, parent)
    if isinstance(scope_node, _ast.ClassDef):
        return ClassSymbolTable(scope_node, filename, parent)
    return SymbolTable(scope_node, filename, parent)


# ---------------------------------------------------------------------------
# Top-level entry point
# ---------------------------------------------------------------------------

def symtable(code, filename, compile_type):
    if compile_type not in ("exec", "single", "eval"):
        raise ValueError("compile_type must be 'exec', 'single', or 'eval'")

    compile(code, filename, compile_type, 0, True)

    if compile_type == "eval":
        tree = _ast.parse(code, filename, mode="eval")
        wrapper = _ast.Module(
            body=[_ast.Expr(value=tree.body)],
            type_ignores=[],
        )
        wrapper.lineno = getattr(tree.body, "lineno", 1)
        return SymbolTable(wrapper, filename)

    tree = _ast.parse(code, filename, mode=compile_type)
    return SymbolTable(tree, filename)


# ---------------------------------------------------------------------------
# Theseus invariant probes
# ---------------------------------------------------------------------------

def symtable2_symtable():
    st = symtable("x = 1\ny = 2\n", "<test>", "exec")
    return st is not None and hasattr(st, "get_symbols") and st.get_type() == "module"


def symtable2_get_symbols():
    st = symtable("x = 1\ndef f(a):\n    return a\n", "<test>", "exec")
    syms = st.get_symbols()
    if not isinstance(syms, list):
        return False
    if not all(isinstance(s, Symbol) for s in syms):
        return False
    names = {s.get_name() for s in syms}
    return "x" in names and "f" in names


def symtable2_lookup():
    st = symtable("answer = 42\n", "<test>", "exec")
    sym = st.lookup("answer")
    if sym is None or sym.get_name() != "answer":
        return False
    try:
        st.lookup("does_not_exist_xyzzy")
    except KeyError:
        return True
    return False


__all__ = [
    "symtable", "SymbolTable", "FunctionSymbolTable", "ClassSymbolTable",
    "Symbol", "SymbolTableError",
    "SCOPE_OFF", "SCOPE_MASK",
    "FREE", "LOCAL", "GLOBAL_IMPLICIT", "GLOBAL_EXPLICIT", "CELL",
    "DEF_GLOBAL", "DEF_LOCAL", "DEF_PARAM", "DEF_NONLOCAL",
    "DEF_USE", "DEF_FREE", "DEF_FREE_CLASS", "DEF_IMPORT", "DEF_BOUND",
    "OPT_IMPORT_STAR", "OPT_EXEC", "OPT_BARE_EXEC", "USE",
    "symtable2_symtable", "symtable2_get_symbols", "symtable2_lookup",
]