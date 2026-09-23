# generation B fnmatch class
import os


class _Match:
    def __init__(self, name, pattern):
        self.name = name
        self.pattern = pattern
        self._memo = {}

    def matches(self):
        return self._match(0, 0)

    def _match(self, name_pos, pattern_pos):
        key = (name_pos, pattern_pos)
        if key in self._memo:
            return self._memo[key]

        if pattern_pos == len(self.pattern):
            result = name_pos == len(self.name)
        else:
            token = self.pattern[pattern_pos]
            if token == "*":
                while (
                    pattern_pos + 1 < len(self.pattern)
                    and self.pattern[pattern_pos + 1] == "*"
                ):
                    pattern_pos += 1
                result = self._match(name_pos, pattern_pos + 1)
                if not result and name_pos < len(self.name):
                    result = self._match(name_pos + 1, pattern_pos)
            elif name_pos == len(self.name):
                result = False
            elif token == "?":
                result = self._match(name_pos + 1, pattern_pos + 1)
            elif token == "[":
                end = self._set_end(pattern_pos)
                if end is None:
                    result = (
                        self.name[name_pos] == "["
                        and self._match(name_pos + 1, pattern_pos + 1)
                    )
                else:
                    result = self._in_set(
                        self.name[name_pos], pattern_pos + 1, end
                    ) and self._match(name_pos + 1, end + 1)
            else:
                result = (
                    self.name[name_pos] == token
                    and self._match(name_pos + 1, pattern_pos + 1)
                )

        self._memo[key] = result
        return result

    def _set_end(self, opening):
        pos = opening + 1
        if pos < len(self.pattern) and self.pattern[pos] in ("!", "^"):
            pos += 1
        if pos < len(self.pattern) and self.pattern[pos] == "]":
            pos += 1
        end = self.pattern.find("]", pos)
        if end < 0:
            return None
        return end

    def _in_set(self, character, start, end):
        negate = start < end and self.pattern[start] in ("!", "^")
        if negate:
            start += 1

        found = False
        pos = start
        if pos < end and self.pattern[pos] == "]":
            found = character == "]"
            pos += 1

        while pos < end:
            if (
                pos + 2 < end
                and self.pattern[pos + 1] == "-"
                and self.pattern[pos] <= self.pattern[pos + 2]
            ):
                if self.pattern[pos] <= character <= self.pattern[pos + 2]:
                    found = True
                pos += 3
            else:
                if character == self.pattern[pos]:
                    found = True
                pos += 1

        return not found if negate else found


def fnmatchcase(name, pat):
    return _Match(name, pat).matches()


def fnmatch(name, pat):
    return _Match(os.path.normcase(name), os.path.normcase(pat)).matches()
