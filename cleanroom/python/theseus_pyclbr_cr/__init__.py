"""
theseus_pyclbr_cr — Clean-room pyclbr module.
No import of the standard `pyclbr` module.
Reads Python module source and extracts class/function definitions via ast.
"""

import ast as _ast
import sys as _sys
import importlib.util as _importlib_util
import os as _os


class _Object:
    """Base class for Class and Function objects."""

    def __init__(self, module, name, file, lineno, parent=None):
        self.module = module
        self.name = name
        self.file = file
        self.lineno = lineno
        self.parent = parent
        self.children = {}

    def _indent(self, indent):
        return ' ' * indent

    def __repr__(self):
        return f'<{self.__class__.__name__} {self.name} at line {self.lineno}>'


class Class(_Object):
    """Information about a class defined in a Python module."""

    def __init__(self, module, name, super_classes, file, lineno, parent=None):
        super().__init__(module, name, file, lineno, parent)
        self.super = super_classes or []
        self.methods = {}

    def _addmethod(self, name, lineno):
        self.methods[name] = lineno


class Function(_Object):
    """Information about a function defined in a Python module."""

    def __init__(self, module, name, file, lineno, parent=None, is_async=False):
        super().__init__(module, name, file, lineno, parent)
        self.is_async = is_async


def _find_module_source(module, path=None):
    """Locate the source file for a module."""
    if path is None:
        path = _sys.path

    spec = _importlib_util.find_spec(module)
    if spec is None:
        raise ImportError(f'No module named {module!r}')

    origin = spec.origin
    if origin is None or not origin.endswith('.py'):
        return None, None
    return origin, spec


def _extract_names(node, module, filename, parent=None):
    """Recursively extract class and function definitions from an AST node."""
    result = {}

    for child in _ast.iter_child_nodes(node):
        if isinstance(child, (_ast.FunctionDef, _ast.AsyncFunctionDef)):
            is_async = isinstance(child, _ast.AsyncFunctionDef)
            func = Function(module, child.name, filename, child.lineno,
                            parent=parent, is_async=is_async)
            result[child.name] = func
            # Also look for nested classes/functions
            nested = _extract_names(child, module, filename, parent=func)
            func.children.update(nested)

        elif isinstance(child, _ast.ClassDef):
            supers = []
            for base in child.bases:
                if isinstance(base, _ast.Name):
                    supers.append(base.id)
                elif isinstance(base, _ast.Attribute):
                    supers.append(f'{base.attr}')

            cls = Class(module, child.name, supers, filename, child.lineno,
                        parent=parent)
            result[child.name] = cls

            # Extract methods
            for item in _ast.iter_child_nodes(child):
                if isinstance(item, (_ast.FunctionDef, _ast.AsyncFunctionDef)):
                    cls._addmethod(item.name, item.lineno)

            # Nested classes/functions
            nested = _extract_names(child, module, filename, parent=cls)
            cls.children.update(nested)

    return result


def readmodule(module, path=None):
    """Return a dictionary mapping class names to Class objects."""
    result = readmodule_ex(module, path)
    return {k: v for k, v in result.items() if isinstance(v, Class)}


def readmodule_ex(module, path=None):
    """Return a dictionary mapping names to Class/Function objects."""
    try:
        source_file, spec = _find_module_source(module, path)
    except ImportError:
        return {}

    if source_file is None:
        return {}

    try:
        with open(source_file, 'rb') as f:
            source = f.read()
    except OSError:
        return {}

    try:
        tree = _ast.parse(source, filename=source_file)
    except SyntaxError:
        return {}

    return _extract_names(tree, module, source_file)


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def pyclbr2_class():
    """Class object has name and module attributes; returns True."""
    cls = Class('mymodule', 'MyClass', ['object'], 'myfile.py', 10)
    return (cls.name == 'MyClass' and
            cls.module == 'mymodule' and
            cls.lineno == 10 and
            cls.super == ['object'])


def pyclbr2_function():
    """Function object has name and module attributes; returns True."""
    fn = Function('mymodule', 'my_func', 'myfile.py', 5)
    return (fn.name == 'my_func' and
            fn.module == 'mymodule' and
            fn.lineno == 5)


def pyclbr2_readmodule():
    """readmodule() returns a dict of class/function names; returns True."""
    result = readmodule_ex('ast')
    return isinstance(result, dict) and len(result) > 0


__all__ = [
    'Class', 'Function', '_Object',
    'readmodule', 'readmodule_ex',
    'pyclbr2_class', 'pyclbr2_function', 'pyclbr2_readmodule',
]
