"""Clean-room implementation of annotationlib-style annotation utilities.

Provides:
  - Format: enum-like class with VALUE, FORWARDREF, STRING formats.
  - ForwardRef: representation of an unevaluated annotation expression.
  - get_annotations(obj, *, globals=None, locals=None, eval_str=False, format=Format.VALUE)
  - Invariant self-check functions: annotlib2_get_annotations, annotlib2_forward_ref,
    annotlib2_format.
"""

import sys as _sys
import types as _types


class Format:
    """Format constants for annotation retrieval."""
    VALUE = 1
    VALUE_WITH_FAKE_GLOBALS = 2
    FORWARDREF = 3
    STRING = 4


# Public format aliases
VALUE = Format.VALUE
VALUE_WITH_FAKE_GLOBALS = Format.VALUE_WITH_FAKE_GLOBALS
FORWARDREF = Format.FORWARDREF
STRING = Format.STRING


_SENTINEL = object()


class ForwardRef:
    """Represents an annotation captured as a string for later evaluation."""

    __slots__ = (
        "__forward_arg__",
        "__forward_module__",
        "__forward_value__",
        "__forward_evaluated__",
        "__forward_is_argument__",
        "__forward_is_class__",
        "__owner__",
        "__weakref__",
    )

    def __init__(self, arg, *, module=None, owner=None,
                 is_argument=True, is_class=False):
        if not isinstance(arg, str):
            raise TypeError(
                "ForwardRef must be a string -- got %r" % (arg,)
            )
        self.__forward_arg__ = arg
        self.__forward_module__ = module
        self.__forward_value__ = _SENTINEL
        self.__forward_evaluated__ = False
        self.__forward_is_argument__ = is_argument
        self.__forward_is_class__ = is_class
        self.__owner__ = owner

    def evaluate(self, *, globals=None, locals=None, type_params=None,
                 owner=None, format=Format.VALUE):
        if self.__forward_evaluated__ and self.__forward_value__ is not _SENTINEL:
            return self.__forward_value__

        # Resolve globals from module if not supplied.
        if globals is None and self.__forward_module__ is not None:
            mod = _sys.modules.get(self.__forward_module__)
            if mod is not None:
                globals = getattr(mod, "__dict__", None)

        if globals is None:
            globals = {}
        if locals is None:
            locals = {}

        # Add type_params to locals if provided.
        if type_params:
            merged = dict(locals)
            for tp in type_params:
                name = getattr(tp, "__name__", None)
                if name is not None:
                    merged.setdefault(name, tp)
            locals = merged

        try:
            value = eval(self.__forward_arg__, globals, locals)
        except NameError:
            if format == Format.STRING:
                return self.__forward_arg__
            if format == Format.FORWARDREF:
                return self
            raise

        self.__forward_value__ = value
        self.__forward_evaluated__ = True
        return value

    def __eq__(self, other):
        if not isinstance(other, ForwardRef):
            return NotImplemented
        return (
            self.__forward_arg__ == other.__forward_arg__
            and self.__forward_module__ == other.__forward_module__
        )

    def __hash__(self):
        return hash((self.__forward_arg__, self.__forward_module__))

    def __repr__(self):
        if self.__forward_module__ is None:
            return "ForwardRef(%r)" % (self.__forward_arg__,)
        return "ForwardRef(%r, module=%r)" % (
            self.__forward_arg__, self.__forward_module__,
        )


def _raw_annotations(obj):
    """Extract the raw __annotations__ mapping from supported objects."""
    if isinstance(obj, type):
        # For classes, look only in the class's own dict (not inherited).
        ann = obj.__dict__.get("__annotations__", None)
    elif isinstance(obj, _types.ModuleType):
        ann = getattr(obj, "__annotations__", None)
    elif isinstance(obj, (_types.FunctionType, _types.MethodType,
                          _types.BuiltinFunctionType)):
        ann = getattr(obj, "__annotations__", None)
    elif callable(obj):
        ann = getattr(obj, "__annotations__", None)
    else:
        # Generic fallback for anything with __annotations__.
        ann = getattr(obj, "__annotations__", None)
    if ann is None:
        return {}
    if not isinstance(ann, dict):
        raise TypeError("__annotations__ must be a dict")
    return dict(ann)


def _module_globals(obj):
    mod_name = None
    if isinstance(obj, _types.ModuleType):
        return getattr(obj, "__dict__", {})
    mod_name = getattr(obj, "__module__", None)
    if mod_name is None:
        return {}
    mod = _sys.modules.get(mod_name)
    if mod is None:
        return {}
    return getattr(mod, "__dict__", {})


def _to_string(value):
    if isinstance(value, str):
        return value
    if isinstance(value, ForwardRef):
        return value.__forward_arg__
    if isinstance(value, type):
        return value.__name__
    name = getattr(value, "__name__", None)
    if name is not None:
        return name
    return repr(value)


def get_annotations(obj, *, globals=None, locals=None,
                    eval_str=False, format=Format.VALUE):
    """Return a fresh dict of annotations for *obj*.

    Mirrors the behavior of inspect.get_annotations / annotationlib
    in clean-room form.
    """
    ann = _raw_annotations(obj)

    if not ann:
        return {}

    if format == Format.STRING:
        return {k: _to_string(v) for k, v in ann.items()}

    # Determine evaluation environment for string annotations.
    if globals is None:
        globals = _module_globals(obj)
    if locals is None:
        if isinstance(obj, type):
            locals = dict(obj.__dict__)
        else:
            locals = {}

    if format == Format.FORWARDREF:
        result = {}
        module_name = getattr(obj, "__module__", None)
        for k, v in ann.items():
            if isinstance(v, str):
                try:
                    result[k] = eval(v, globals, locals)
                except Exception:
                    result[k] = ForwardRef(v, module=module_name)
            else:
                result[k] = v
        return result

    if format == Format.VALUE or format == Format.VALUE_WITH_FAKE_GLOBALS:
        if eval_str:
            result = {}
            for k, v in ann.items():
                if isinstance(v, str):
                    result[k] = eval(v, globals, locals)
                else:
                    result[k] = v
            return result
        return ann

    raise ValueError("Unsupported format: %r" % (format,))


# ---------------------------------------------------------------------------
# Invariant self-checks
# ---------------------------------------------------------------------------

def annotlib2_get_annotations():
    """Verify get_annotations works on functions, classes, and modules."""
    def func(x: int, y: str) -> bool:
        return True
    ann = get_annotations(func)
    if ann != {"x": int, "y": str, "return": bool}:
        return False
    # Returned dict must be a fresh copy (mutating it must not affect source).
    ann["x"] = float
    if func.__annotations__["x"] is not int:
        return False

    class C:
        a: int
        b: "str"
    cann = get_annotations(C)
    if cann.get("a") is not int:
        return False
    if cann.get("b") != "str":
        return False

    # eval_str path.
    cann_eval = get_annotations(C, eval_str=True, locals={"str": str})
    if cann_eval.get("b") is not str:
        return False

    # STRING format path.
    sann = get_annotations(func, format=Format.STRING)
    if sann != {"x": "int", "y": "str", "return": "bool"}:
        return False

    # Object without annotations returns empty dict.
    class Empty:
        pass
    if get_annotations(Empty) != {}:
        return False

    return True


def annotlib2_forward_ref():
    """Verify ForwardRef construction, equality, and evaluation."""
    fr = ForwardRef("int")
    if fr.__forward_arg__ != "int":
        return False
    if fr != ForwardRef("int"):
        return False
    if hash(fr) != hash(ForwardRef("int")):
        return False
    # Evaluate against builtins.
    if fr.evaluate() is not int:
        return False
    # Cached evaluation returns the same object.
    if fr.evaluate() is not int:
        return False

    # Unknown name with FORWARDREF format returns the ref.
    fr2 = ForwardRef("DefinitelyNotAName")
    out = fr2.evaluate(globals={}, locals={}, format=Format.FORWARDREF)
    if out is not fr2:
        return False
    # Same with STRING format returns the original string.
    out2 = fr2.evaluate(globals={}, locals={}, format=Format.STRING)
    if out2 != "DefinitelyNotAName":
        return False

    # Non-string argument raises TypeError.
    try:
        ForwardRef(123)
    except TypeError:
        pass
    else:
        return False

    # repr should mention the forward arg.
    if "int" not in repr(fr):
        return False

    return True


def annotlib2_format():
    """Verify Format constants are distinct and have expected ordering."""
    values = {Format.VALUE, Format.VALUE_WITH_FAKE_GLOBALS,
              Format.FORWARDREF, Format.STRING}
    if len(values) != 4:
        return False
    if Format.VALUE != 1:
        return False
    if Format.FORWARDREF != 3:
        return False
    if Format.STRING != 4:
        return False
    # Module-level aliases must match.
    if VALUE != Format.VALUE or FORWARDREF != Format.FORWARDREF \
            or STRING != Format.STRING:
        return False
    return True


__all__ = [
    "Format",
    "VALUE",
    "VALUE_WITH_FAKE_GLOBALS",
    "FORWARDREF",
    "STRING",
    "ForwardRef",
    "get_annotations",
    "annotlib2_get_annotations",
    "annotlib2_forward_ref",
    "annotlib2_format",
]