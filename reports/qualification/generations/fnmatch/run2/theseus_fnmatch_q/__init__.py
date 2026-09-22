# generation B regex translate

import os
import re
import sys


def _normcase(value):
    if os.name == "nt" or sys.platform == "darwin":
        return value.lower()
    return value


def _class_atom(char):
    if char in "\\[]^-&~|":
        return "\\" + char
    return char


def _translate_class(content):
    parts = []
    index = 0
    length = len(content)

    while index < length:
        if index + 2 < length and content[index + 1] == "-":
            start = content[index]
            end = content[index + 2]
            if ord(start) <= ord(end):
                parts.append(_class_atom(start) + "-" + _class_atom(end))
            index += 3
            continue

        parts.append(_class_atom(content[index]))
        index += 1

    if not parts:
        return None
    return "".join(parts)


def translate(pat):
    pieces = []
    index = 0
    length = len(pat)

    while index < length:
        char = pat[index]
        index += 1

        if char == "*":
            pieces.append(".*")
        elif char == "?":
            pieces.append(".")
        elif char != "[":
            pieces.append(re.escape(char))
        else:
            end = index
            if end < length and pat[end] == "!":
                end += 1
            if end < length and pat[end] == "]":
                end += 1
            while end < length and pat[end] != "]":
                end += 1

            if end >= length:
                pieces.append(r"\[")
                continue

            content = pat[index:end]
            index = end + 1
            negated = content.startswith("!")
            if negated:
                content = content[1:]

            translated = _translate_class(content)
            if translated is None:
                pieces.append("(?!)")
            elif negated:
                pieces.append("[^" + translated + "]")
            else:
                pieces.append("[" + translated + "]")

    return "(?s:" + "".join(pieces) + r")\Z"


def fnmatchcase(name, pat):
    return re.match(translate(pat), name) is not None


def fnmatch(name, pat):
    return fnmatchcase(_normcase(name), _normcase(pat))


def filter(names, pat):
    return [name for name in names if fnmatch(name, pat)]
