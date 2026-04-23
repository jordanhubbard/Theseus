"""
theseus_copy: Clean-room shallow and deep copy utilities.
"""


def copy(obj=None):
    """
    Shallow copy of obj.
    Returns a new container with the same element references.
    Supports: list, dict, set, tuple, and falls back to obj for primitives.
    """
    if isinstance(obj, list):
        return list(obj)
    elif isinstance(obj, dict):
        return dict(obj)
    elif isinstance(obj, set):
        return set(obj)
    elif isinstance(obj, tuple):
        return tuple(obj)
    else:
        return obj


def deepcopy(obj=None, _memo=None):
    """
    Deep copy of obj.
    Returns a new container with recursively copied elements.
    Supports: list, dict, set, tuple, and falls back to obj for primitives.
    """
    if _memo is None:
        _memo = {}

    if obj is None:
        return None

    obj_id = id(obj)
    if obj_id in _memo:
        return _memo[obj_id]

    if isinstance(obj, list):
        result = []
        _memo[obj_id] = result
        for item in obj:
            result.append(deepcopy(item, _memo))
        return result
    elif isinstance(obj, dict):
        result = {}
        _memo[obj_id] = result
        for key, value in obj.items():
            result[deepcopy(key, _memo)] = deepcopy(value, _memo)
        return result
    elif isinstance(obj, set):
        result = set()
        _memo[obj_id] = result
        for item in obj:
            result.add(deepcopy(item, _memo))
        return result
    elif isinstance(obj, tuple):
        items = tuple(deepcopy(item, _memo) for item in obj)
        _memo[obj_id] = items
        return items
    else:
        return obj


def copy_shallow_equal():
    orig = [1, 2, 3]
    return copy(orig) == orig


def copy_is_not_same():
    orig = [1, 2]
    return copy(orig) is not orig


def copy_deep_independent():
    orig = [[1, 2], [3, 4]]
    dc = deepcopy(orig)
    dc[0].append(99)
    return orig[0] == [1, 2]


def shallow_equal(obj=None):
    """
    Returns a shallow copy of obj. The copy equals the original (==).
    """
    return copy(obj)


def shallow_not_same(obj=None):
    """
    Returns a shallow copy of obj that is not the same object as the original.
    """
    return copy(obj)


def deep_independent(obj=None):
    """
    Returns a deep copy of obj that is fully independent from the original.
    """
    return deepcopy(obj)