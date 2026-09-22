# generation A state machine

import re

__all__ = ["split", "quote", "join"]

IN_WORD = "IN_WORD"
IN_SINGLE = "IN_SINGLE"
IN_DOUBLE = "IN_DOUBLE"

_WHITESPACE = " \t\n\r\f\v"
_SAFE_PATTERN = re.compile(r"^[\w@%+=:,./-]+$")


def split(s, comments=False, posix=True):
    if s == "":
        return []
    if posix:
        return _split_posix(s, comments)
    return _split_non_posix(s, comments)


def _split_posix(s, comments):
    tokens = []
    word = None
    state = None
    i = 0
    n = len(s)

    while i < n:
        c = s[i]

        if state is None:
            if c in _WHITESPACE:
                i += 1
                continue
            if comments and c == "#":
                while i < n and s[i] != "\n":
                    i += 1
                continue
            word = ""
            if c == "'":
                state = IN_SINGLE
                i += 1
                continue
            if c == '"':
                state = IN_DOUBLE
                i += 1
                continue
            if c == "\\":
                state = IN_WORD
                i += 1
                if i >= n:
                    raise ValueError("No escaped character")
                word += s[i]
                i += 1
                continue
            state = IN_WORD
            word = c
            i += 1
            continue

        if state == IN_WORD:
            if c in _WHITESPACE:
                tokens.append(word)
                word = None
                state = None
                continue
            if comments and c == "#":
                tokens.append(word)
                word = None
                state = None
                continue
            if c == "'":
                state = IN_SINGLE
                i += 1
                continue
            if c == '"':
                state = IN_DOUBLE
                i += 1
                continue
            if c == "\\":
                i += 1
                if i >= n:
                    raise ValueError("No escaped character")
                if s[i] == "\n":
                    i += 1
                    continue
                word += s[i]
                i += 1
                continue
            word += c
            i += 1
            continue

        if state == IN_SINGLE:
            if c == "'":
                state = IN_WORD
                i += 1
                continue
            word += c
            i += 1
            continue

        if state == IN_DOUBLE:
            if c == "\\":
                i += 1
                if i >= n:
                    raise ValueError("No escaped character")
                esc = s[i]
                if esc in ("\\", '"', "$", "`"):
                    word += esc
                elif esc == "\n":
                    word += "\n"
                else:
                    word += "\\"
                    word += esc
                i += 1
                continue
            if c == '"':
                state = IN_WORD
                i += 1
                continue
            word += c
            i += 1
            continue

    if state == IN_SINGLE or state == IN_DOUBLE:
        raise ValueError("No closing quotation")
    if state == IN_WORD:
        tokens.append(word)
    return tokens


def _split_non_posix(s, comments):
    tokens = []
    i = 0
    n = len(s)

    while i < n:
        c = s[i]
        if c in _WHITESPACE:
            i += 1
            continue
        if comments and c == "#":
            while i < n and s[i] != "\n":
                i += 1
            continue
        if c in "'\"":
            quote = c
            i += 1
            start = i
            while i < n and s[i] != quote:
                i += 1
            if i >= n:
                raise ValueError("No closing quotation")
            tokens.append(quote + s[start:i] + quote)
            i += 1
            continue
        start = i
        while i < n and s[i] not in _WHITESPACE:
            if comments and s[i] == "#":
                break
            i += 1
        tokens.append(s[start:i])
    return tokens


def quote(s):
    if s == "":
        return "''"
    if _SAFE_PATTERN.match(s):
        return s
    return "'" + s.replace("'", "'\"'\"'") + "'"


def join(split_command):
    return " ".join(quote(part) for part in split_command)
