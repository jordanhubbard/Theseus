"""Clean-room collections.abc subset for Theseus invariants."""

import abc


class Iterable(metaclass=abc.ABCMeta):
    pass


class Iterator(Iterable):
    pass


class Generator(Iterator):
    pass


class Sequence(Iterable):
    pass


class MutableSequence(Sequence):
    pass


class Mapping(Iterable):
    pass


class MutableMapping(Mapping):
    pass


class Awaitable(metaclass=abc.ABCMeta):
    pass


class Coroutine(Awaitable):
    pass


class AsyncIterable(metaclass=abc.ABCMeta):
    pass


class AsyncIterator(AsyncIterable):
    pass


class AsyncGenerator(AsyncIterator):
    pass


MutableSequence.register(list)
Sequence.register(list)
MutableMapping.register(dict)
Mapping.register(dict)


def colabc2_sequence():
    return Sequence is not None and MutableSequence is not None and Mapping is not None and issubclass(list, MutableSequence) and issubclass(dict, MutableMapping)


def colabc2_register():
    class MySeq:
        def __getitem__(self, i):
            return i

        def __len__(self):
            return 0

    Sequence.register(MySeq)
    return isinstance(MySeq(), Sequence)


def colabc2_iterator():
    return Iterator is not None and Iterable is not None and Generator is not None and issubclass(Iterator, Iterable)


__all__ = [
    "Awaitable", "Coroutine", "AsyncIterable", "AsyncIterator", "AsyncGenerator",
    "Iterable", "Iterator", "Generator", "Sequence", "MutableSequence",
    "Mapping", "MutableMapping",
    "colabc2_sequence", "colabc2_register", "colabc2_iterator",
]
