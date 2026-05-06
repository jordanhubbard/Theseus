"""Clean-room implementation of Python's contextvars module.

Provides ContextVar, Context, Token, and copy_context() — implemented from
scratch using only thread-local storage and dict-based state. Does not
import or wrap the original contextvars module.
"""

import threading


# Sentinel used to distinguish "no value" from a legitimate None value.
_MISSING = object()

# Thread-local storage holding the currently-active Context for each thread.
_local = threading.local()


def _current_context():
    """Return the active Context for the current thread, creating one lazily."""
    ctx = getattr(_local, "context", None)
    if ctx is None:
        ctx = Context()
        _local.context = ctx
    return ctx


class Token:
    """Returned by ContextVar.set(); carries enough state for reset()."""

    MISSING = _MISSING

    __slots__ = ("_var", "_old_value", "_used")

    def __init__(self, var, old_value):
        self._var = var
        self._old_value = old_value
        self._used = False

    @property
    def var(self):
        return self._var

    @property
    def old_value(self):
        return self._old_value

    def __repr__(self):
        used = " used" if self._used else ""
        return f"<Token{used} var={self._var!r} at 0x{id(self):x}>"


class ContextVar:
    """Holds a context-local value identified by name."""

    __slots__ = ("_name", "_default", "__weakref__")

    def __init__(self, name, *, default=_MISSING):
        if not isinstance(name, str):
            raise TypeError("context variable name must be a str")
        self._name = name
        self._default = default

    @property
    def name(self):
        return self._name

    def get(self, *args):
        if len(args) > 1:
            raise TypeError(
                f"ContextVar.get() takes at most 2 arguments ({len(args) + 1} given)"
            )
        ctx = _current_context()
        if self in ctx._data:
            return ctx._data[self]
        # Per standard contextvars semantics, the argument default takes
        # precedence over the ContextVar's own default.
        if args:
            return args[0]
        if self._default is not _MISSING:
            return self._default
        raise LookupError(self)

    def set(self, value):
        ctx = _current_context()
        old = ctx._data.get(self, _MISSING)
        token = Token(self, old)
        ctx._data[self] = value
        return token

    def reset(self, token):
        if not isinstance(token, Token):
            raise TypeError(f"expected an instance of Token, got {type(token).__name__}")
        if token._used:
            raise ValueError("Token has already been used once")
        if token._var is not self:
            raise ValueError("Token was created by a different ContextVar")
        ctx = _current_context()
        if token._old_value is _MISSING:
            ctx._data.pop(self, None)
        else:
            ctx._data[self] = token._old_value
        token._used = True

    def __repr__(self):
        default_repr = ""
        if self._default is not _MISSING:
            default_repr = f" default={self._default!r}"
        return f"<ContextVar name={self._name!r}{default_repr} at 0x{id(self):x}>"


class Context:
    """A mapping from ContextVar to value, plus a run() entry point."""

    __slots__ = ("_data", "_prev", "_entered")

    def __init__(self):
        self._data = {}
        self._prev = None
        self._entered = False

    def run(self, func, *args, **kwargs):
        if self._entered:
            raise RuntimeError(
                "cannot enter context: %s is already entered" % (self,)
            )
        self._prev = getattr(_local, "context", None)
        _local.context = self
        self._entered = True
        try:
            return func(*args, **kwargs)
        finally:
            _local.context = self._prev
            self._prev = None
            self._entered = False

    def copy(self):
        new_ctx = Context()
        new_ctx._data = dict(self._data)
        return new_ctx

    def __getitem__(self, var):
        if not isinstance(var, ContextVar):
            raise TypeError(
                f"a ContextVar key was expected, got {type(var).__name__}"
            )
        return self._data[var]

    def get(self, var, default=None):
        if not isinstance(var, ContextVar):
            raise TypeError(
                f"a ContextVar key was expected, got {type(var).__name__}"
            )
        return self._data.get(var, default)

    def __contains__(self, var):
        return var in self._data

    def __iter__(self):
        return iter(self._data)

    def __len__(self):
        return len(self._data)

    def keys(self):
        return self._data.keys()

    def values(self):
        return self._data.values()

    def items(self):
        return self._data.items()

    def __repr__(self):
        return f"<Context at 0x{id(self):x} ({len(self._data)} vars)>"


def copy_context():
    """Return a shallow copy of the current thread's active Context."""
    return _current_context().copy()


# ---------------------------------------------------------------------------
# Invariant probes — exercise the public surface end-to-end and report
# True only when every observable behavior matches expectation.
# ---------------------------------------------------------------------------

def ctxvars2_contextvar():
    """Verify ContextVar create/get/set/reset/default semantics."""
    try:
        # Default-value path.
        var = ContextVar("cv_probe", default=42)
        if var.name != "cv_probe":
            return False
        if var.get() != 42:
            return False
        # Per standard semantics, the argument default takes precedence
        # over the ContextVar's own default when no value is set in
        # the context.
        if var.get("fallback") != "fallback":
            return False

        # set/get/reset round-trip.
        tok = var.set(100)
        if var.get() != 100:
            return False
        # Once a value is set, both get() and get(default) return it.
        if var.get("ignored") != 100:
            return False
        var.reset(tok)
        if var.get() != 42:
            return False

        # No-default ContextVar raises LookupError.
        var2 = ContextVar("cv_probe_nodefault")
        try:
            var2.get()
            return False
        except LookupError:
            pass
        if var2.get("explicit") != "explicit":
            return False

        # Setting and resetting in a non-default ContextVar.
        t2 = var2.set("hello")
        if var2.get() != "hello":
            return False
        var2.reset(t2)
        try:
            var2.get()
            return False
        except LookupError:
            pass

        # Type validation on the name.
        try:
            ContextVar(123)  # type: ignore[arg-type]
            return False
        except TypeError:
            pass

        return True
    except Exception:
        return False


def ctxvars2_copy_context():
    """Verify copy_context() snapshots state and Context.run() isolates writes."""
    try:
        var = ContextVar("cc_probe", default=0)
        tok = var.set(7)
        try:
            ctx = copy_context()
            if not isinstance(ctx, Context):
                return False
            if var not in ctx:
                return False
            if ctx[var] != 7:
                return False
            if ctx.get(var) != 7:
                return False
            if len(ctx) < 1:
                return False
            if var not in list(ctx.keys()):
                return False

            # Mutations inside Context.run() must not leak out.
            def _inside():
                var.set(999)
                return var.get()

            inner = ctx.run(_inside)
            if inner != 999:
                return False
            if var.get() != 7:
                return False

            # Re-entering the same context while it's already active is forbidden.
            def _reenter():
                try:
                    ctx.run(lambda: None)
                except RuntimeError:
                    return "ok"
                return "bad"

            if ctx.run(_reenter) != "ok":
                return False
        finally:
            var.reset(tok)

        return True
    except Exception:
        return False


def ctxvars2_token():
    """Verify Token carries var/old_value and enforces single-use reset."""
    try:
        var = ContextVar("tok_probe")

        # First set on an unset variable: old_value is the MISSING sentinel.
        t1 = var.set("alpha")
        if not isinstance(t1, Token):
            return False
        if t1.var is not var:
            return False
        if t1.old_value is not Token.MISSING:
            return False

        # Second set: old_value is the previous value.
        t2 = var.set("beta")
        if t2.old_value != "alpha":
            return False
        if var.get() != "beta":
            return False

        # Reset to the prior value.
        var.reset(t2)
        if var.get() != "alpha":
            return False

        # Tokens are single-use.
        try:
            var.reset(t2)
            return False
        except ValueError:
            pass

        # A token from a different ContextVar must be rejected.
        other = ContextVar("tok_probe_other")
        t_other = other.set("x")
        try:
            var.reset(t_other)
            return False
        except ValueError:
            pass
        other.reset(t_other)

        # Reset all the way back to "unset".
        var.reset(t1)
        try:
            var.get()
            return False
        except LookupError:
            pass

        # Non-token argument is rejected.
        try:
            var.reset("not a token")  # type: ignore[arg-type]
            return False
        except TypeError:
            pass

        return True
    except Exception:
        return False


__all__ = [
    "ContextVar",
    "Context",
    "Token",
    "copy_context",
    "ctxvars2_contextvar",
    "ctxvars2_copy_context",
    "ctxvars2_token",
]