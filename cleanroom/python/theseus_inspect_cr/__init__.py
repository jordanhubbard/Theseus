"""
theseus_inspect_cr - Clean-room code introspection utilities.
Do NOT import inspect. Implemented from scratch.
"""

import types
import sys
import linecache


def isfunction(obj):
    """Return True if obj is a Python function (including lambdas)."""
    return isinstance(obj, types.FunctionType)


def isclass(obj):
    """Return True if obj is a class."""
    return isinstance(obj, type)


def ismethod(obj):
    """Return True if obj is a bound method."""
    return isinstance(obj, types.MethodType)


def ismodule(obj):
    """Return True if obj is a module."""
    return isinstance(obj, types.ModuleType)


def isfunction_str(obj):
    """
    Return True if obj is a Python function, checking via type name string.
    This checks whether the type name is 'function'.
    """
    return type(obj).__name__ == 'function'


def inspect_isfunction():
    return isfunction(lambda: None)


def inspect_isclass():
    return isclass(int)


def inspect_isfunction_str():
    return isfunction('hello')


def getmembers(obj):
    """
    Return a list of (name, value) pairs for all members of obj.
    Results are sorted alphabetically by name.
    """
    results = []
    names = set()

    try:
        if hasattr(obj, '__dict__'):
            names.update(obj.__dict__.keys())
        for cls in type(obj).__mro__:
            if hasattr(cls, '__dict__'):
                names.update(cls.__dict__.keys())
        if isinstance(obj, type):
            for cls in obj.__mro__:
                if hasattr(cls, '__dict__'):
                    names.update(cls.__dict__.keys())
    except Exception:
        pass

    for name in sorted(names):
        try:
            value = getattr(obj, name)
            results.append((name, value))
        except AttributeError:
            pass
        except Exception:
            pass

    return results


def getsource(obj):
    """
    Attempt to return the source code for a function or class.
    This is a best-effort implementation without using inspect.
    """
    try:
        if isinstance(obj, types.FunctionType):
            filename = obj.__code__.co_filename
            firstlineno = obj.__code__.co_firstlineno
        elif isinstance(obj, type):
            mod = sys.modules.get(obj.__module__, None)
            if mod is not None and hasattr(mod, '__file__'):
                filename = mod.__file__
                if filename and filename.endswith('.pyc'):
                    filename = filename[:-1]
            else:
                raise OSError("Cannot find source for class")
            firstlineno = None
            lines = linecache.getlines(filename)
            for i, line in enumerate(lines, 1):
                if line.strip().startswith('class ' + obj.__name__):
                    firstlineno = i
                    break
            if firstlineno is None:
                raise OSError("Cannot find class definition in source")
        else:
            raise TypeError("Object is not a function or class")

        if not filename or filename == '<string>' or filename.startswith('<'):
            raise OSError("Cannot get source for dynamically created objects")

        lines = linecache.getlines(filename)
        if not lines:
            raise OSError(f"Cannot read source file: {filename}")

        start = firstlineno - 1
        def_line = lines[start]
        indent = len(def_line) - len(def_line.lstrip())

        source_lines = [def_line]
        i = start + 1
        while i < len(lines):
            line = lines[i]
            stripped = line.rstrip()
            if stripped == '':
                source_lines.append(line)
                i += 1
                continue
            line_indent = len(line) - len(line.lstrip())
            if line_indent > indent:
                source_lines.append(line)
                i += 1
            else:
                break

        while source_lines and not source_lines[-1].strip():
            source_lines.pop()

        return ''.join(source_lines)

    except (OSError, TypeError, AttributeError) as e:
        raise OSError(f"Could not get source: {e}") from e


def signature(fn):
    """
    Return a string representation of the function signature with parameter names.
    """
    if not isinstance(fn, types.FunctionType) and not isinstance(fn, types.MethodType):
        raise TypeError(f"Object {fn!r} is not a function or method")

    if isinstance(fn, types.MethodType):
        code = fn.__func__.__code__
        defaults = fn.__func__.__defaults__ or ()
        kwdefaults = fn.__func__.__kwdefaults__ or {}
        annotations = fn.__func__.__annotations__
    else:
        code = fn.__code__
        defaults = fn.__defaults__ if fn.__defaults__ else ()
        kwdefaults = fn.__kwdefaults__ if fn.__kwdefaults__ else {}
        annotations = fn.__annotations__

    varnames = code.co_varnames
    argcount = code.co_argcount
    kwonlyargcount = code.co_kwonlyargcount
    flags = code.co_flags

    CO_VARARGS = 0x04
    CO_VARKEYWORDS = 0x08

    has_varargs = bool(flags & CO_VARARGS)
    has_varkw = bool(flags & CO_VARKEYWORDS)

    pos_args = list(varnames[:argcount])

    idx = argcount
    varargs_name = None
    if has_varargs:
        varargs_name = varnames[idx]
        idx += 1

    kwonly_args = list(varnames[idx:idx + kwonlyargcount])
    idx += kwonlyargcount

    varkw_name = None
    if has_varkw:
        varkw_name = varnames[idx]

    params = []

    n_defaults = len(defaults)
    n_pos = len(pos_args)

    for i, name in enumerate(pos_args):
        default_idx = i - (n_pos - n_defaults)
        if default_idx >= 0:
            default_val = defaults[default_idx]
            params.append(f"{name}={default_val!r}")
        else:
            params.append(name)

    if varargs_name:
        params.append(f"*{varargs_name}")
    elif kwonly_args:
        params.append("*")

    for name in kwonly_args:
        if name in kwdefaults:
            params.append(f"{name}={kwdefaults[name]!r}")
        else:
            params.append(name)

    if varkw_name:
        params.append(f"**{varkw_name}")

    return_annotation = annotations.get('return', None)
    sig = f"({', '.join(params)})"
    if return_annotation is not None:
        sig += f" -> {return_annotation!r}"

    return sig


__all__ = [
    'isfunction',
    'isclass',
    'ismethod',
    'ismodule',
    'isfunction_str',
    'inspect_isfunction',
    'inspect_isclass',
    'inspect_isfunction_str',
    'getmembers',
    'getsource',
    'signature',
]