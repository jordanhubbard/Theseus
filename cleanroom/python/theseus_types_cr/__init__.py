# theseus_types_cr — clean-room implementation
# Do NOT import the `types` module or any third-party library.

# ---------------------------------------------------------------------------
# FunctionType: the type of Python functions
# We obtain it by inspecting a function we define right here.
# ---------------------------------------------------------------------------

def _get_function_type():
    def _sample():
        pass
    return type(_sample)

FunctionType = _get_function_type()

# LambdaType is just an alias for FunctionType
LambdaType = FunctionType


# ---------------------------------------------------------------------------
# SimpleNamespace: a simple object that holds attributes passed as kwargs.
# ---------------------------------------------------------------------------

class SimpleNamespace:
    """A simple attribute-based namespace."""

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def __repr__(self):
        items = ', '.join(
            f'{k}={v!r}' for k, v in sorted(self.__dict__.items())
        )
        return f'SimpleNamespace({items})'

    def __eq__(self, other):
        if isinstance(other, SimpleNamespace):
            return self.__dict__ == other.__dict__
        return NotImplemented

    def __ne__(self, other):
        result = self.__eq__(other)
        if result is NotImplemented:
            return result
        return not result

    def __hash__(self):
        # SimpleNamespace is mutable, so not hashable by default
        raise TypeError(
            f"unhashable type: '{type(self).__name__}'"
        )


# ---------------------------------------------------------------------------
# new_class: dynamic class creation
#
# Signature: new_class(name, bases=(), kwds=None, exec_body=None)
#
# This mirrors the behaviour of types.new_class:
#   1. Resolve the metaclass from bases and kwds.
#   2. Call metaclass.__prepare__ to get the namespace dict.
#   3. Call exec_body(namespace) if provided.
#   4. Create the class with metaclass(name, bases, namespace, **kwds).
# ---------------------------------------------------------------------------

def new_class(name, bases=(), kwds=None, exec_body=None):
    """Create a class object dynamically.

    Parameters
    ----------
    name      : str   — the class name
    bases     : tuple — base classes (default: ())
    kwds      : dict  — keyword arguments for the metaclass (default: {})
                        May contain 'metaclass' key.
    exec_body : callable(ns) — called with the class namespace so the caller
                               can populate it (default: None)

    Returns
    -------
    The newly created class object.
    """
    if kwds is None:
        kwds = {}
    else:
        kwds = dict(kwds)  # work on a copy

    # --- 1. Determine the metaclass ---
    # Extract explicit metaclass from kwds, if present.
    meta = kwds.pop('metaclass', None)

    if meta is None:
        # Derive from bases, just like Python does.
        if bases:
            # Use the type of the first base as a starting point.
            meta = type(bases[0])
            # Walk all bases to find the "most derived" metaclass.
            for base in bases[1:]:
                base_meta = type(base)
                if issubclass(base_meta, meta):
                    meta = base_meta
                elif not issubclass(meta, base_meta):
                    raise TypeError(
                        'metaclass conflict: the metaclass of a derived class '
                        'must be a (non-strict) subclass of the metaclasses '
                        'of all its bases'
                    )
        else:
            meta = type

    # --- 2. Prepare the namespace ---
    prepare = getattr(meta, '__prepare__', None)
    if prepare is not None:
        ns = prepare(name, bases, **kwds)
    else:
        ns = {}

    # --- 3. Populate the namespace ---
    if exec_body is not None:
        exec_body(ns)

    # --- 4. Create and return the class ---
    cls = meta(name, bases, ns, **kwds)
    return cls


# ---------------------------------------------------------------------------
# Test helpers referenced in the invariants
# ---------------------------------------------------------------------------

def types_function_type():
    """isinstance(lambda: None, FunctionType) == True"""
    return isinstance(lambda: None, FunctionType)


def types_simple_namespace():
    """SimpleNamespace(x=1).x == 1  →  returns 1"""
    return SimpleNamespace(x=1).x


def types_new_class():
    """new_class('Foo', (object,), {}) is a class  →  True"""
    Foo = new_class('Foo', (object,), {})
    return isinstance(Foo, type)