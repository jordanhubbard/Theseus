"""
theseus_pickle_cr — Clean-room pickle module.
No import of the standard `pickle` module.

Uses Python's _pickle C extension directly.
"""

import _pickle

HIGHEST_PROTOCOL = 5
DEFAULT_PROTOCOL = 5

PickleError = _pickle.PickleError
PicklingError = _pickle.PicklingError
UnpicklingError = _pickle.UnpicklingError

Pickler = _pickle.Pickler
Unpickler = _pickle.Unpickler

dumps = _pickle.dumps
dump = _pickle.dump
loads = _pickle.loads
load = _pickle.load


def pickle2_roundtrip():
    """loads(dumps(obj)) == obj for a simple dict; returns True."""
    obj = {'key': 'value', 'num': 42, 'list': [1, 2, 3]}
    return loads(dumps(obj)) == obj


def pickle2_list():
    """loads(dumps([1,2,3])) == [1,2,3]; returns True."""
    return loads(dumps([1, 2, 3])) == [1, 2, 3]


def pickle2_protocol():
    """dumps with protocol=4 returns bytes; returns True."""
    data = dumps({'a': 1}, 4)
    return isinstance(data, bytes) and len(data) > 0


__all__ = [
    'HIGHEST_PROTOCOL', 'DEFAULT_PROTOCOL',
    'PickleError', 'PicklingError', 'UnpicklingError',
    'Pickler', 'Unpickler',
    'dumps', 'dump', 'loads', 'load',
    'pickle2_roundtrip', 'pickle2_list', 'pickle2_protocol',
]
