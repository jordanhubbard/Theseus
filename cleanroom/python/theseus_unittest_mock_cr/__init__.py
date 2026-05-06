"""Clean-room implementation of a minimal unittest.mock-like module.

This module provides simple Mock, MagicMock, and patch primitives implemented
from scratch without importing unittest.mock.
"""


class _Call(tuple):
    """Represents a recorded call as (args, kwargs)."""

    def __new__(cls, args=(), kwargs=None):
        if kwargs is None:
            kwargs = {}
        return tuple.__new__(cls, (tuple(args), dict(kwargs)))

    @property
    def args(self):
        return self[0]

    @property
    def kwargs(self):
        return self[1]


class Mock(object):
    """A minimal mock object that records calls and auto-creates attributes."""

    def __init__(self, return_value=None, side_effect=None, name=None, spec=None):
        object.__setattr__(self, "_mock_name", name)
        object.__setattr__(self, "_mock_return_value", return_value)
        object.__setattr__(self, "_mock_side_effect", side_effect)
        object.__setattr__(self, "_mock_call_args", None)
        object.__setattr__(self, "_mock_call_args_list", [])
        object.__setattr__(self, "_mock_call_count", 0)
        object.__setattr__(self, "_mock_children", {})
        object.__setattr__(self, "_mock_spec", spec)

    def __call__(self, *args, **kwargs):
        object.__setattr__(self, "_mock_call_count", self._mock_call_count + 1)
        call = _Call(args, kwargs)
        object.__setattr__(self, "_mock_call_args", call)
        self._mock_call_args_list.append(call)

        side_effect = self._mock_side_effect
        if side_effect is not None:
            if isinstance(side_effect, BaseException) or (
                isinstance(side_effect, type) and issubclass(side_effect, BaseException)
            ):
                raise side_effect
            if callable(side_effect):
                result = side_effect(*args, **kwargs)
                if result is not _DEFAULT:
                    return result
            else:
                # Treat as iterable
                try:
                    iterator = iter(side_effect)
                    object.__setattr__(self, "_mock_side_effect", iterator)
                    return next(iterator)
                except TypeError:
                    pass
        return self._mock_return_value

    def __getattr__(self, name):
        if name.startswith("_mock_") or name.startswith("__"):
            raise AttributeError(name)
        children = self.__dict__.get("_mock_children")
        if children is None:
            raise AttributeError(name)
        if name not in children:
            child = type(self)(name=name)
            children[name] = child
            object.__setattr__(self, name, child)
        return children[name]

    @property
    def return_value(self):
        return self._mock_return_value

    @return_value.setter
    def return_value(self, value):
        object.__setattr__(self, "_mock_return_value", value)

    @property
    def side_effect(self):
        return self._mock_side_effect

    @side_effect.setter
    def side_effect(self, value):
        object.__setattr__(self, "_mock_side_effect", value)

    @property
    def call_count(self):
        return self._mock_call_count

    @property
    def call_args(self):
        return self._mock_call_args

    @property
    def call_args_list(self):
        return list(self._mock_call_args_list)

    @property
    def called(self):
        return self._mock_call_count > 0

    def assert_called(self):
        if self._mock_call_count == 0:
            raise AssertionError("Expected mock to have been called.")

    def assert_called_once(self):
        if self._mock_call_count != 1:
            raise AssertionError(
                "Expected mock to have been called once. Called %d times."
                % self._mock_call_count
            )

    def assert_called_with(self, *args, **kwargs):
        expected = _Call(args, kwargs)
        if self._mock_call_args != expected:
            raise AssertionError(
                "Expected call: %r\nActual call: %r" % (expected, self._mock_call_args)
            )

    def assert_called_once_with(self, *args, **kwargs):
        self.assert_called_once()
        self.assert_called_with(*args, **kwargs)

    def assert_not_called(self):
        if self._mock_call_count != 0:
            raise AssertionError(
                "Expected mock to not have been called. Called %d times."
                % self._mock_call_count
            )

    def reset_mock(self):
        object.__setattr__(self, "_mock_call_args", None)
        object.__setattr__(self, "_mock_call_args_list", [])
        object.__setattr__(self, "_mock_call_count", 0)


class _Default(object):
    def __repr__(self):
        return "DEFAULT"


_DEFAULT = _Default()
DEFAULT = _DEFAULT


def _make_magic_method(name, default):
    def method(self, *args, **kwargs):
        children = self.__dict__.get("_mock_children", {})
        child = children.get(name)
        if child is None:
            child = Mock(name=name)
            child._mock_return_value = default
            children[name] = child
        return child(*args, **kwargs)

    method.__name__ = name
    return method


_MAGIC_DEFAULTS = {
    "__lt__": NotImplemented,
    "__gt__": NotImplemented,
    "__le__": NotImplemented,
    "__ge__": NotImplemented,
    "__int__": 1,
    "__contains__": False,
    "__len__": 0,
    "__iter__": iter([]),
    "__exit__": False,
    "__complex__": 1j,
    "__float__": 1.0,
    "__bool__": True,
    "__next__": None,
    "__fspath__": "",
    "__index__": 1,
    "__hash__": None,
    "__str__": "",
    "__sizeof__": 0,
    "__enter__": None,
}


class MagicMock(Mock):
    """A Mock that supports magic methods with sensible defaults."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Pre-populate magic method children so attribute access returns mocks.
        for name, default in _MAGIC_DEFAULTS.items():
            child = Mock(name=name, return_value=default)
            self._mock_children[name] = child

    def __len__(self):
        return self._mock_children["__len__"]()

    def __iter__(self):
        return iter([])

    def __contains__(self, item):
        return self._mock_children["__contains__"](item)

    def __bool__(self):
        return True

    def __enter__(self):
        return self._mock_children["__enter__"]()

    def __exit__(self, exc_type, exc_val, exc_tb):
        return self._mock_children["__exit__"](exc_type, exc_val, exc_tb)

    def __int__(self):
        return self._mock_children["__int__"]()

    def __float__(self):
        return self._mock_children["__float__"]()

    def __str__(self):
        return ""


class _Patch(object):
    """Context manager / decorator for patching attributes on a target."""

    def __init__(self, target, attribute, new=_DEFAULT, new_callable=None):
        self.target = target
        self.attribute = attribute
        self.new = new
        self.new_callable = new_callable
        self._original = None
        self._had_attr = False
        self._active_value = None

    def _resolve_target(self):
        if isinstance(self.target, str):
            parts = self.target.split(".")
            module_name = parts[0]
            obj = __import__(module_name)
            for part in parts[1:]:
                obj = getattr(obj, part)
            return obj
        return self.target

    def __enter__(self):
        target_obj = self._resolve_target()
        self._target_obj = target_obj
        if hasattr(target_obj, self.attribute):
            self._had_attr = True
            self._original = getattr(target_obj, self.attribute)
        else:
            self._had_attr = False
            self._original = None

        if self.new is _DEFAULT:
            if self.new_callable is not None:
                value = self.new_callable()
            else:
                value = MagicMock()
        else:
            value = self.new

        self._active_value = value
        setattr(target_obj, self.attribute, value)
        return value

    def __exit__(self, exc_type, exc_val, exc_tb):
        target_obj = self._target_obj
        if self._had_attr:
            setattr(target_obj, self.attribute, self._original)
        else:
            try:
                delattr(target_obj, self.attribute)
            except AttributeError:
                pass
        return False

    def start(self):
        return self.__enter__()

    def stop(self):
        return self.__exit__(None, None, None)

    def __call__(self, func):
        def wrapper(*args, **kwargs):
            with self as patched:
                return func(*args + (patched,), **kwargs)

        return wrapper


def patch(target, new=_DEFAULT, new_callable=None):
    """Patch a target attribute. ``target`` can be ``"module.attr"`` or
    ``(obj, "attr")``."""
    if isinstance(target, str):
        if "." not in target:
            raise TypeError("patch target must be 'module.attr'")
        module_path, _, attribute = target.rpartition(".")
        return _Patch(module_path, attribute, new=new, new_callable=new_callable)
    if isinstance(target, tuple) and len(target) == 2:
        obj, attribute = target
        return _Patch(obj, attribute, new=new, new_callable=new_callable)
    raise TypeError("Unsupported patch target: %r" % (target,))


# ---------------------------------------------------------------------------
# Invariant entry points
# ---------------------------------------------------------------------------


def mock2_mock():
    """Verify that Mock records calls, return_value, and assertions."""
    m = Mock(return_value=42)
    if m.called:
        return False
    result = m(1, 2, key="value")
    if result != 42:
        return False
    if not m.called:
        return False
    if m.call_count != 1:
        return False
    if m.call_args != _Call((1, 2), {"key": "value"}):
        return False

    # Side effect raising an exception
    boom = Mock(side_effect=RuntimeError("nope"))
    try:
        boom()
    except RuntimeError:
        pass
    else:
        return False

    # reset_mock works
    m.reset_mock()
    if m.called or m.call_count != 0:
        return False

    # Auto-attribute creation
    parent = Mock()
    child = parent.child_attr
    if not isinstance(child, Mock):
        return False
    child(7)
    if child.call_count != 1:
        return False
    return True


def mock2_patch():
    """Verify that patch() temporarily replaces attributes on an object."""

    class Target(object):
        value = "original"

        def method(self):
            return "real"

    obj = Target()
    if obj.method() != "real":
        return False

    p = patch((obj, "method"), new=lambda: "patched")
    patched = p.start()
    if obj.method() != "patched":
        return False
    p.stop()
    if obj.method() != "real":
        return False

    # As a context manager with default MagicMock
    with patch((obj, "value")) as mocked:
        if not isinstance(mocked, MagicMock):
            return False
        if obj.value is not mocked:
            return False
    if obj.value != "original":
        return False

    return True


def mock2_magic_mock():
    """Verify that MagicMock supports magic methods."""
    mm = MagicMock()
    # len defaults to 0
    if len(mm) != 0:
        return False
    # iter is empty
    if list(iter(mm)) != []:
        return False
    # contains defaults to False
    if ("x" in mm):
        return False
    # bool is True
    if not bool(mm):
        return False
    # int default
    if int(mm) != 1:
        return False
    # context manager
    with mm as inner:
        _ = inner
    # str default
    if str(mm) != "":
        return False
    # Still recordable as a callable
    mm(1, 2, 3)
    if mm.call_count != 1:
        return False
    if mm.call_args != _Call((1, 2, 3), {}):
        return False
    return True