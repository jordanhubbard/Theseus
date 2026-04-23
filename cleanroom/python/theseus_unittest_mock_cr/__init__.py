"""
theseus_unittest_mock_cr — Clean-room unittest.mock module.
No import of the standard `unittest.mock` module.
"""

import sys as _sys
import inspect as _inspect
import functools as _functools
import contextlib as _contextlib


_MOCK_METHODS = frozenset([
    '__hash__', '__sizeof__', '__repr__', '__str__',
])

_ALL_MAGICS = frozenset(m for m in dir(int) if m.startswith('__'))


class _CallList(list):
    def __contains__(self, value):
        if not isinstance(value, list):
            return list.__contains__(self, value)
        len_value = len(value)
        len_self = len(self)
        if len_value > len_self:
            return False
        for i in range(0, len_self - len_value + 1):
            if self[i:i+len_value] == value:
                return True
        return False


class _MockIter:
    def __init__(self, obj):
        self.obj = obj

    def __iter__(self):
        return iter(self.obj)


class call(tuple):
    """A tuple for holding the results of a call to a mock."""

    def __new__(cls, /, *args, **kwargs):
        return tuple.__new__(cls, (args, kwargs))

    def __call__(self, /, *args, **kwargs):
        return call(*args, **kwargs)

    def __repr__(self):
        if self[1]:
            return 'call(%s, %s)' % (
                ', '.join(repr(a) for a in self[0]),
                ', '.join('%s=%r' % i for i in self[1].items())
            )
        return 'call(%s)' % ', '.join(repr(a) for a in self[0])


class _MockMethodList:
    def __init__(self):
        self._mock_methods = []

    def __iter__(self):
        return iter(self._mock_methods)


class NonCallableMock:
    """A non-callable version of Mock."""

    def __init__(self, spec=None, wraps=None, name=None, spec_set=None,
                 **kwargs):
        self._mock_name = name
        self._mock_spec = spec
        self._mock_wraps = wraps
        self._mock_children = {}
        self._mock_return_value = DEFAULT
        self._mock_called = False
        self._mock_call_count = 0
        self._mock_call_args = None
        self._mock_call_args_list = _CallList()
        self._mock_mock_calls = _CallList()
        self.method_calls = _CallList()
        self._mock_parent = None
        self._mock_new_parent = None
        self._mock_sealed = False
        for kw, val in kwargs.items():
            setattr(self, kw, val)

    @property
    def called(self):
        return self._mock_called

    @property
    def call_count(self):
        return self._mock_call_count

    @property
    def call_args(self):
        return self._mock_call_args

    @property
    def call_args_list(self):
        return self._mock_call_args_list

    @property
    def mock_calls(self):
        return self._mock_mock_calls

    @property
    def return_value(self):
        if self._mock_return_value is DEFAULT:
            self._mock_return_value = Mock(name='%s()' % self._mock_name if self._mock_name else None)
        return self._mock_return_value

    @return_value.setter
    def return_value(self, value):
        self._mock_return_value = value

    def __get_attr__(self, name):
        if name in self._mock_children:
            return self._mock_children[name]
        child = Mock(name='%s.%s' % (self._mock_name or '', name))
        child._mock_parent = self
        self._mock_children[name] = child
        return child

    def __getattr__(self, name):
        if name.startswith('_mock_') or name in ('method_calls',):
            raise AttributeError(name)
        if name in self._mock_children:
            return self._mock_children[name]
        child = Mock(name='%s.%s' % (self._mock_name or '', name))
        child._mock_parent = self
        self._mock_children[name] = child
        return child

    def __setattr__(self, name, value):
        if name.startswith('_mock_') or name in ('method_calls', 'return_value',
                                                    'side_effect', 'called',
                                                    'call_count', 'call_args',
                                                    'call_args_list', 'mock_calls'):
            object.__setattr__(self, name, value)
        else:
            self._mock_children[name] = value

    def __repr__(self):
        name = self._mock_name or 'mock'
        return "<%s name='%s' id='%d'>" % (type(self).__name__, name, id(self))

    def reset_mock(self, visited=None, *, return_value=False, side_effect=False):
        self._mock_called = False
        self._mock_call_count = 0
        self._mock_call_args = None
        self._mock_call_args_list = _CallList()
        self._mock_mock_calls = _CallList()
        self.method_calls = _CallList()
        for child in self._mock_children.values():
            if isinstance(child, (Mock, MagicMock)):
                child.reset_mock(return_value=return_value, side_effect=side_effect)

    def configure_mock(self, **kwargs):
        for attr, val in sorted(kwargs.items(), key=lambda e: e[0].count('.')):
            final, rest = attr, None
            if '.' in attr:
                parts = attr.split('.')
                final = parts[-1]
                obj = self
                for part in parts[:-1]:
                    obj = getattr(obj, part)
                setattr(obj, final, val)
            else:
                setattr(self, attr, val)

    def assert_called(self):
        if not self.called:
            raise AssertionError("Expected '%s' to have been called." % (self._mock_name or 'mock',))

    def assert_called_once(self):
        if self.call_count != 1:
            raise AssertionError("Expected '%s' to have been called once. Called %d times." % (
                self._mock_name or 'mock', self.call_count))

    def assert_called_with(self, /, *args, **kwargs):
        expected = call(*args, **kwargs)
        actual = self.call_args
        if expected != actual:
            raise AssertionError('expected call not found.\nExpected: %s\nActual: %s' % (expected, actual))

    def assert_called_once_with(self, /, *args, **kwargs):
        self.assert_called_once()
        self.assert_called_with(*args, **kwargs)

    def assert_any_call(self, /, *args, **kwargs):
        expected = call(*args, **kwargs)
        if expected not in self.call_args_list:
            raise AssertionError('expected call not found in call_args_list')

    def assert_has_calls(self, calls, any_order=False):
        if not any_order:
            if calls not in self.mock_calls:
                raise AssertionError('Calls not found.\nExpected: %s\nActual: %s' % (calls, self.mock_calls))
        else:
            all_calls = list(self.mock_calls)
            not_found = []
            for kall in calls:
                try:
                    all_calls.remove(kall)
                except ValueError:
                    not_found.append(kall)
            if not_found:
                raise AssertionError('Calls not found: %s' % not_found)

    def assert_not_called(self):
        if self.called:
            raise AssertionError("Expected '%s' not to have been called. Called %d times." % (
                self._mock_name or 'mock', self.call_count))


class _DEFAULT:
    def __repr__(self):
        return 'DEFAULT'
DEFAULT = _DEFAULT()


class Mock(NonCallableMock):
    """A mock object with call tracking."""

    def __init__(self, spec=None, wraps=None, name=None, spec_set=None,
                 side_effect=None, return_value=DEFAULT, **kwargs):
        super().__init__(spec=spec, wraps=wraps, name=name, spec_set=spec_set, **kwargs)
        self._mock_side_effect = side_effect
        if return_value is not DEFAULT:
            self._mock_return_value = return_value

    @property
    def side_effect(self):
        return self._mock_side_effect

    @side_effect.setter
    def side_effect(self, value):
        self._mock_side_effect = value

    def __call__(self, /, *args, **kwargs):
        self._mock_called = True
        self._mock_call_count += 1
        self._mock_call_args = call(*args, **kwargs)
        self._mock_call_args_list.append(call(*args, **kwargs))
        self._mock_mock_calls.append(call(*args, **kwargs))

        if self._mock_side_effect is not None:
            se = self._mock_side_effect
            if callable(se):
                result = se(*args, **kwargs)
                if result is not DEFAULT:
                    return result
            elif isinstance(se, BaseException) or (isinstance(se, type) and issubclass(se, BaseException)):
                raise se
            else:
                # Iterator
                try:
                    effect = next(se)
                except StopIteration:
                    raise
                if isinstance(effect, BaseException):
                    raise effect
                return effect

        if self._mock_wraps is not None:
            return self._mock_wraps(*args, **kwargs)

        return self.return_value


class MagicMixin:
    """Mixin for magic method support."""

    def __init__(self, /, *args, **kw):
        self._mock_set_magics()

    def _mock_set_magics(self):
        these_magics = _ALL_MAGICS

        for name in these_magics:
            klass = type(self)
            if not hasattr(klass, name):
                setattr(klass, name, MagicProxy(name))

    def __len__(self):
        return 0

    def __contains__(self, item):
        return False

    def __iter__(self):
        return iter([])

    def __int__(self):
        return 1

    def __float__(self):
        return 1.0

    def __bool__(self):
        return True

    def __index__(self):
        return 1


class MagicMock(MagicMixin, Mock):
    """A Mock subclass that supports magic method configuration."""

    def __init__(self, /, *args, **kw):
        Mock.__init__(self, *args, **kw)
        MagicMixin.__init__(self, *args, **kw)

    def mock_add_spec(self, spec, spec_set=False):
        self._mock_spec = spec

    def __iter__(self):
        return iter(self.return_value if hasattr(self, '_mock_return_value') and
                    self._mock_return_value is not DEFAULT else [])


class MagicProxy:
    def __init__(self, name):
        self.name = name

    def __get__(self, obj, obj_type=None):
        if obj is None:
            return self
        return obj._mock_children.get(self.name, Mock(name=self.name))


class NonCallableMagicMock(MagicMixin, NonCallableMock):
    """A version of MagicMock that isn't callable."""

    def __init__(self, /, *args, **kw):
        NonCallableMock.__init__(self, *args, **kw)
        MagicMixin.__init__(self, *args, **kw)


class AsyncMock(Mock):
    """A mock object for async functions."""

    async def __call__(self, /, *args, **kwargs):
        return Mock.__call__(self, *args, **kwargs)


class _patch:
    """A context manager/decorator for patching."""

    def __init__(self, getter, attribute, new, spec, create, spec_set,
                 autospec, new_callable, kwargs):
        self.getter = getter
        self.attribute = attribute
        self.new = new
        self.spec = spec
        self.create = create
        self.spec_set = spec_set
        self.autospec = autospec
        self.new_callable = new_callable
        self.kwargs = kwargs
        self.additional_patchers = []
        self.temp_original = DEFAULT
        self.is_local = False

    def get_original(self):
        target = self.getter()
        name = self.attribute
        original = DEFAULT
        local = False
        try:
            original = target.__dict__[name]
            local = True
        except (AttributeError, KeyError):
            original = getattr(target, name, DEFAULT)
        return original, local

    def __enter__(self):
        name = self.attribute
        target = self.getter()

        original, local = self.get_original()

        if self.new is DEFAULT:
            if self.new_callable is not None:
                klass = self.new_callable
            else:
                klass = MagicMock
            new = klass(**self.kwargs)
        else:
            new = self.new

        self.temp_original = original
        self.is_local = local
        setattr(target, name, new)
        return new

    def __exit__(self, *exc_info):
        target = self.getter()
        name = self.attribute
        if self.temp_original is not DEFAULT:
            setattr(target, name, self.temp_original)
        elif self.is_local is False:
            try:
                delattr(target, name)
            except AttributeError:
                pass

    def __call__(self, func):
        if isinstance(func, type):
            return self._decorate_class(func)
        @_functools.wraps(func)
        def wrapper(*args, **keywargs):
            with self as mock_obj:
                keywargs['mock'] = mock_obj
                return func(*args, **keywargs)
        return wrapper

    def _decorate_class(self, klass):
        return klass

    def start(self):
        result = self.__enter__()
        return result

    def stop(self):
        self.__exit__(None, None, None)


_builtins = object()


def patch(target, new=DEFAULT, spec=None, create=False, spec_set=None,
          autospec=None, new_callable=None, **kwargs):
    """Patch an object for the duration of a test."""
    # Parse the target string
    getter, attribute = _get_target(target)
    return _patch(getter, attribute, new, spec, create, spec_set,
                  autospec, new_callable, kwargs)


def _get_target(target):
    """Parse 'a.b.c' into (getter_for_a.b, 'c')."""
    try:
        target, attribute = target.rsplit('.', 1)
    except (TypeError, ValueError) as e:
        raise TypeError("Need a valid target to patch. You supplied: %r" % (target,)) from e

    def getter():
        import importlib as _imp
        return _imp.import_module(target)

    return getter, attribute


class patch:
    """namespace for patch functions."""

    def __new__(cls, target, new=DEFAULT, spec=None, create=False,
                spec_set=None, autospec=None, new_callable=None, **kwargs):
        getter, attribute = _get_target(target)
        return _patch(getter, attribute, new, spec, create, spec_set,
                      autospec, new_callable, kwargs)

    @staticmethod
    def object(target, attribute, new=DEFAULT, spec=None, create=False,
               spec_set=None, autospec=None, new_callable=None, **kwargs):
        getter = lambda: target
        return _patch(getter, attribute, new, spec, create, spec_set,
                      autospec, new_callable, kwargs)

    @staticmethod
    def dict(in_dict, values=(), clear=False, **kwargs):
        return _patch_dict(in_dict, values, clear, **kwargs)

    @staticmethod
    def multiple(target, spec=None, create=False, spec_set=None,
                 autospec=None, new_callable=None, **kwargs):
        getter, attribute = _get_target(target)
        return _patch(getter, attribute, DEFAULT, spec, create, spec_set,
                      autospec, new_callable, kwargs)

    @staticmethod
    def stopall():
        pass


class _patch_dict:
    """A context manager for patching dicts."""

    def __init__(self, in_dict, values=(), clear=False, **kwargs):
        self.in_dict = in_dict
        self.values = values
        self.clear = clear
        self.kwargs = kwargs
        self._original = None

    def __enter__(self):
        self._original = dict(self.in_dict)
        if self.clear:
            self.in_dict.clear()
        if self.values:
            self.in_dict.update(self.values)
        self.in_dict.update(self.kwargs)
        return self.in_dict

    def __exit__(self, *args):
        self.in_dict.clear()
        self.in_dict.update(self._original)

    def __call__(self, func):
        @_functools.wraps(func)
        def wrapper(*args, **kwargs):
            with self:
                return func(*args, **kwargs)
        return wrapper


class sentinel:
    """Provide unique, named objects to use as sentinel values."""

    def __init__(self):
        self._sentinels = {}

    def __getattr__(self, name):
        if name.startswith('_'):
            raise AttributeError(name)
        if name not in self._sentinels:
            self._sentinels[name] = _SentinelObject(name)
        return self._sentinels[name]


class _SentinelObject:
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return 'sentinel.%s' % self.name

    def __reduce__(self):
        return (_get_sentinel, (self.name,))


def _get_sentinel(name):
    return getattr(sentinel, name)


sentinel = sentinel()


class _ANY:
    def __eq__(self, other):
        return True

    def __ne__(self, other):
        return False

    def __repr__(self):
        return '<ANY>'


ANY = _ANY()


def create_autospec(spec, spec_set=False, instance=False, _parent=None,
                    _name=None, **kwargs):
    """Create a mock object with a spec automatically set up."""
    if isinstance(spec, type):
        return MagicMock(spec=spec, **kwargs)
    return MagicMock(spec=spec, **kwargs)


def mock_open(mock=None, read_data=''):
    """A helper function to create a mock to replace the use of open()."""
    if mock is None:
        mock = MagicMock(name='open', spec=open)

    handle = MagicMock(spec=type(open(
        __file__, 'r',
    )))
    handle.__enter__.return_value = handle
    handle.read.return_value = read_data
    handle.readline.return_value = ''
    handle.readlines.return_value = []
    handle.__exit__.return_value = False
    handle.__iter__.return_value = iter([])

    mock.return_value = handle
    return mock


class PropertyMock(Mock):
    """A mock intended to be used as a property."""

    def _get_child_mock(self, /, *args, **kwargs):
        return MagicMock(*args, **kwargs)

    def __get__(self, obj, obj_type=None):
        return self()

    def __set__(self, obj, val):
        self(val)


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def mock2_mock():
    """Mock class can be instantiated and called; returns True."""
    m = Mock()
    m(1, 2, key='value')
    return (m.called and
            m.call_count == 1 and
            isinstance(m.call_args, tuple))


def mock2_patch():
    """patch() decorator works as context manager; returns True."""
    import os as _os
    original = _os.getcwd

    # Use patch as context manager via object form
    with patch.object(_os, 'getcwd', return_value='/fake') as mock_getcwd:
        result = _os.getcwd()

    return result == '/fake' and _os.getcwd is original


def mock2_magic_mock():
    """MagicMock supports magic methods; returns True."""
    m = MagicMock()
    m.some_attr = 42
    return (isinstance(m, MagicMock) and
            bool(m) is True)


__all__ = [
    'Mock', 'MagicMock', 'NonCallableMock', 'NonCallableMagicMock',
    'AsyncMock', 'PropertyMock',
    'patch', 'sentinel', 'DEFAULT', 'ANY', 'call',
    'create_autospec', 'mock_open',
    'mock2_mock', 'mock2_patch', 'mock2_magic_mock',
]
