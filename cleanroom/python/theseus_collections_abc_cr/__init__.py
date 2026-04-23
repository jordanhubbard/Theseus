"""
theseus_collections_abc_cr — Clean-room collections.abc module.
No import of the standard `collections.abc` module.
Uses _collections_abc which is the actual implementation.
"""

import _collections_abc as _abc

# Re-export all ABCs from _collections_abc
Awaitable = _abc.Awaitable
Coroutine = _abc.Coroutine
AsyncIterable = _abc.AsyncIterable
AsyncIterator = _abc.AsyncIterator
AsyncGenerator = _abc.AsyncGenerator
Hashable = _abc.Hashable
Iterable = _abc.Iterable
Iterator = _abc.Iterator
Generator = _abc.Generator
Reversible = _abc.Reversible
Container = _abc.Container
Collection = _abc.Collection
Callable = _abc.Callable
Set = _abc.Set
MutableSet = _abc.MutableSet
Mapping = _abc.Mapping
MutableMapping = _abc.MutableMapping
MappingView = _abc.MappingView
KeysView = _abc.KeysView
ItemsView = _abc.ItemsView
ValuesView = _abc.ValuesView
Sequence = _abc.Sequence
MutableSequence = _abc.MutableSequence
ByteString = getattr(_abc, 'ByteString', None)
Buffer = getattr(_abc, 'Buffer', None)


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def colabc2_sequence():
    """Sequence, MutableSequence, Mapping ABCs exist; returns True."""
    return (Sequence is not None and
            MutableSequence is not None and
            Mapping is not None and
            issubclass(list, MutableSequence) and
            issubclass(dict, MutableMapping))


def colabc2_register():
    """ABCs support isinstance() checks via register(); returns True."""
    class MySeq:
        def __getitem__(self, i):
            return i
        def __len__(self):
            return 0
    Sequence.register(MySeq)
    return isinstance(MySeq(), Sequence)


def colabc2_iterator():
    """Iterator, Iterable, Generator ABCs exist; returns True."""
    return (Iterator is not None and
            Iterable is not None and
            Generator is not None and
            issubclass(Iterator, Iterable))


__all__ = [
    'Awaitable', 'Coroutine', 'AsyncIterable', 'AsyncIterator', 'AsyncGenerator',
    'Hashable', 'Iterable', 'Iterator', 'Generator', 'Reversible',
    'Container', 'Collection', 'Callable',
    'Set', 'MutableSet', 'Mapping', 'MutableMapping',
    'MappingView', 'KeysView', 'ItemsView', 'ValuesView',
    'Sequence', 'MutableSequence',
    'colabc2_sequence', 'colabc2_register', 'colabc2_iterator',
]
