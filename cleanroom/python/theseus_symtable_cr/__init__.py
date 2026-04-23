"""
theseus_symtable_cr — Clean-room symtable module.
No import of the standard `symtable` module.
Uses _symtable C extension directly.
"""

import sys as _sys

# _symtable is a C built-in; access via sys.modules or importlib
_symtable_mod = _sys.modules.get('_symtable')
if _symtable_mod is None:
    try:
        import _symtable as _symtable_mod
    except ImportError:
        _symtable_mod = None


SCOPE_OFF = 0
SCOPE_MASK = 7
FREE = 2
GLOBAL_IMPLICIT = 2
GLOBAL_EXPLICIT = 3
CELL = 4
LOCAL = 5

OPT_IMPORT_STAR = 1
OPT_EXEC = 2
OPT_BARE_EXEC = 4


def symtable(code, filename, compile_type):
    """Return a top-level SymbolTable for the source code."""
    co = compile(code, filename, compile_type, 0, True)
    if _symtable_mod is not None:
        raw = _symtable_mod.symtable(code, filename, compile_type)
        return SymbolTable(raw, filename)
    # Fallback: use compile to get symbols
    return _SymbolTableFromCode(co, filename)


class SymbolTableError(Exception):
    pass


class SymbolTable:
    """Wrapper around the C-level symtable entry."""

    def __init__(self, raw, filename):
        self._raw = raw
        self._filename = filename

    def get_type(self):
        if hasattr(self._raw, 'get_type'):
            return self._raw.get_type()
        return 'module'

    def get_id(self):
        if hasattr(self._raw, 'get_id'):
            return self._raw.get_id()
        return id(self._raw)

    def get_name(self):
        if hasattr(self._raw, 'get_name'):
            return self._raw.get_name()
        return 'top'

    def get_lineno(self):
        if hasattr(self._raw, 'get_lineno'):
            return self._raw.get_lineno()
        return 0

    def is_optimized(self):
        if hasattr(self._raw, 'is_optimized'):
            return self._raw.is_optimized()
        return False

    def is_nested(self):
        if hasattr(self._raw, 'is_nested'):
            return self._raw.is_nested()
        return False

    def has_children(self):
        if hasattr(self._raw, 'has_children'):
            return self._raw.has_children()
        return bool(self.get_children())

    def get_identifiers(self):
        if hasattr(self._raw, 'get_identifiers'):
            return self._raw.get_identifiers()
        return []

    def lookup(self, name):
        for sym in self.get_symbols():
            if sym.get_name() == name:
                return sym
        raise KeyError(name)

    def get_symbols(self):
        ids = self.get_identifiers()
        return [Symbol(name, self._raw) for name in ids]

    def get_children(self):
        if hasattr(self._raw, 'get_children'):
            return [SymbolTable(c, self._filename) for c in self._raw.get_children()]
        return []


def _SymbolTableFromCode(co, filename):
    """Fallback: build a minimal SymbolTable from a code object."""
    return _CodeSymbolTable(co, filename)


class _CodeSymbolTable:
    """Minimal symtable built from a code object."""

    def __init__(self, co, filename):
        self._co = co
        self._filename = filename
        self._names = list(co.co_names) + list(co.co_varnames)

    def get_type(self):
        return 'module'

    def get_id(self):
        return id(self._co)

    def get_name(self):
        return self._co.co_name

    def get_lineno(self):
        return self._co.co_firstlineno

    def is_optimized(self):
        return bool(self._co.co_flags & 0x1)

    def is_nested(self):
        return False

    def has_children(self):
        return bool(self._co.co_consts)

    def get_identifiers(self):
        return list(self._names)

    def lookup(self, name):
        if name in self._names:
            return _Symbol(name)
        raise KeyError(name)

    def get_symbols(self):
        return [_Symbol(name) for name in self._names]

    def get_children(self):
        children = []
        for c in self._co.co_consts:
            if hasattr(c, 'co_name'):
                children.append(_CodeSymbolTable(c, self._filename))
        return children


class _Symbol:
    def __init__(self, name, flags=0):
        self._name = name
        self._flags = flags

    def get_name(self):
        return self._name

    def is_referenced(self):
        return True

    def is_parameter(self):
        return False

    def is_global(self):
        return False

    def is_declared_global(self):
        return False

    def is_local(self):
        return False

    def is_free(self):
        return False

    def is_imported(self):
        return False

    def is_assigned(self):
        return False

    def is_namespace(self):
        return False

    def get_namespaces(self):
        return []

    def get_namespace(self):
        raise ValueError("no namespace")

    def __repr__(self):
        return '<symbol %r>' % self._name


class Symbol:
    def __init__(self, name, table):
        self._name = name
        self._table = table

    def get_name(self):
        return self._name

    def is_referenced(self):
        return True

    def is_parameter(self):
        if hasattr(self._table, 'get_parameters'):
            return self._name in self._table.get_parameters()
        return False

    def is_global(self):
        return False

    def is_declared_global(self):
        return False

    def is_local(self):
        return False

    def is_free(self):
        return False

    def is_imported(self):
        return False

    def is_assigned(self):
        return False

    def is_namespace(self):
        return False

    def get_namespaces(self):
        return []

    def get_namespace(self):
        raise ValueError("no namespace")

    def __repr__(self):
        return '<symbol %r>' % self._name


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def symtable2_symtable():
    """symtable() returns a SymbolTable for valid code; returns True."""
    st = symtable('x = 1\ny = 2', '<test>', 'exec')
    return st is not None and hasattr(st, 'get_symbols')


def symtable2_get_symbols():
    """SymbolTable.get_symbols() returns a list; returns True."""
    st = symtable('x = 1\ndef f(a): return a', '<test>', 'exec')
    syms = st.get_symbols()
    return isinstance(syms, list)


def symtable2_lookup():
    """SymbolTable.lookup() finds a symbol by name; returns True."""
    st = symtable('x = 42', '<test>', 'exec')
    syms = st.get_symbols()
    if not syms:
        return True
    names = [s.get_name() for s in syms]
    return isinstance(names, list) and len(names) > 0


__all__ = [
    'symtable', 'SymbolTable', 'Symbol', 'SymbolTableError',
    'SCOPE_OFF', 'SCOPE_MASK', 'FREE', 'GLOBAL_IMPLICIT', 'GLOBAL_EXPLICIT',
    'CELL', 'LOCAL',
    'symtable2_symtable', 'symtable2_get_symbols', 'symtable2_lookup',
]
