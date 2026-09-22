# generation A recursive copy


def copy(x):
    if isinstance(x, list):
        return list(x)
    if isinstance(x, dict):
        return dict(x)
    if isinstance(x, tuple):
        return x
    return x


def deepcopy(x, memo=None):
    if memo is None:
        memo = {}
    obj_id = id(x)
    if obj_id in memo:
        return memo[obj_id]
    if isinstance(x, (int, str, type(None), float, bool)):
        return x
    if isinstance(x, tuple):
        y = tuple(deepcopy(item, memo) for item in x)
        memo[obj_id] = y
        return y
    if isinstance(x, list):
        y = []
        memo[obj_id] = y
        for item in x:
            y.append(deepcopy(item, memo))
        return y
    if isinstance(x, dict):
        y = {}
        memo[obj_id] = y
        for key, value in x.items():
            y[deepcopy(key, memo)] = deepcopy(value, memo)
        return y
    return x
