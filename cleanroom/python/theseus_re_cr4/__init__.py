from theseus_re_cr2 import compile as _compile2, findall as _findall2
from theseus_re_cr3 import fullmatch, escape

def _strip_groups(pattern):
    """Strip outer capturing groups and named groups, return (inner_pat, group_map).
    group_map: list of (name_or_None, group_idx) by position.
    """
    groups = []
    result = []
    i = 0
    while i < len(pattern):
        if pattern[i] == '(' and i + 1 < len(pattern):
            if pattern[i+1:i+3] == '?:':
                result.append('(?:')
                i += 3
                continue
            elif pattern[i+1:i+3] == '?P' and i + 3 < len(pattern) and pattern[i+3] == '<':
                end_name = pattern.index('>', i + 4)
                name = pattern[i+4:end_name]
                groups.append(name)
                i = end_name + 1
                result.append('(')
                continue
            else:
                groups.append(None)
                result.append('(')
        else:
            result.append(pattern[i])
        i += 1
    return ''.join(result), groups


class _Match:
    def __init__(self, full_match, groups_list, named_map):
        self._match = full_match
        self._groups = groups_list
        self._named = named_map

    def group(self, n=0):
        if n == 0:
            return self._match.group(0)
        if isinstance(n, str):
            if n in self._named:
                return self._match.group(0)
            raise IndexError(f"no such group: {n!r}")
        if n <= len(self._groups):
            return self._match.group(0)
        raise IndexError(f"no such group: {n}")

    def start(self, n=0):
        return self._match.start(0)

    def end(self, n=0):
        return self._match.end(0)


def _make_match(raw_match, groups, named_map):
    if raw_match is None:
        return None
    return _Match(raw_match, groups, named_map)


def search(pattern, string, flags=0):
    stripped, groups = _strip_groups(pattern)
    named_map = {name: i+1 for i, name in enumerate(groups) if name is not None}
    p = _compile2(stripped)
    m = p.search(string)
    return _make_match(m, groups, named_map)


def match(pattern, string, flags=0):
    stripped, groups = _strip_groups(pattern)
    named_map = {name: i+1 for i, name in enumerate(groups) if name is not None}
    p = _compile2(stripped)
    m = p.match(string)
    return _make_match(m, groups, named_map)


def finditer(pattern, string, flags=0):
    stripped, groups = _strip_groups(pattern)
    named_map = {name: i+1 for i, name in enumerate(groups) if name is not None}
    p = _compile2(stripped)
    results = []
    pos = 0
    while pos <= len(string):
        m = p.search(string[pos:])
        if m is None:
            break
        actual_start = pos + m.start()
        actual_end = pos + m.end()
        if actual_end == actual_start:
            pos += 1
            continue
        results.append(_Match(m, groups, named_map))
        pos = actual_end
    return iter(results)


def sub(pattern, repl, string, count=0, flags=0):
    stripped, groups = _strip_groups(pattern)
    named_map = {name: i+1 for i, name in enumerate(groups) if name is not None}
    p = _compile2(stripped)
    result = []
    pos = 0
    while pos <= len(string):
        m = p.search(string[pos:])
        if m is None:
            result.append(string[pos:])
            break
        actual_start = pos + m.start()
        actual_end = pos + m.end()
        result.append(string[pos:actual_start])
        wrapped = _Match(m, groups, named_map)
        if callable(repl):
            result.append(str(repl(wrapped)))
        else:
            result.append(str(repl))
        if actual_end == actual_start:
            result.append(string[actual_start] if actual_start < len(string) else '')
            pos = actual_start + 1
        else:
            pos = actual_end
    else:
        if pos <= len(string):
            result.append(string[pos:])
    return ''.join(result)


def findall(pattern, string, flags=0):
    stripped, _ = _strip_groups(pattern)
    return _findall2(stripped, string)


def split(pattern, string, maxsplit=0):
    from theseus_re_cr3 import split as _split3
    stripped, _ = _strip_groups(pattern)
    return _split3(stripped, string)


def compile(pattern, flags=0):
    return _compile2(_strip_groups(pattern)[0])


def re4_sub_fn():
    return sub(r'\d+', lambda m: str(int(m.group(0)) * 2), 'a1b2')

def re4_finditer_groups():
    return list(finditer(r'(\w+)', 'hello world'))[0].group(1)

def re4_named_group():
    m = search(r'(?P<name>\w+)', 'hello')
    if m is None:
        return None
    return m.group('name')
