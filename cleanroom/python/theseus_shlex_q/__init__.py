"""
theseus_shlex_q — Clean-room shell-like lexical analysis.
Do NOT import shlex.
"""

import re

_UNSAFE = re.compile(r"[^\w@%+=:,./-]", re.ASCII)


def quote(s):
    if not s:
        return "''"
    if _UNSAFE.search(s) is None:
        return s
    return "'" + s.replace("'", "'\"'\"'") + "'"


def split(s, comments=False, posix=True):
    if s is None:
        raise ValueError("NoneType")
    tokens = []
    i = 0
    n = len(s)
    token = []
    in_single = False
    in_double = False
    escaped = False
    while i < n:
        ch = s[i]
        i += 1
        if escaped:
            token.append(ch)
            escaped = False
            continue
        if posix and ch == "\\" and not in_single:
            if in_double:
                nxt = s[i] if i < n else ""
                if nxt in ('"', "\\", "$", "`"):
                    escaped = True
                    continue
                token.append(ch)
                continue
            escaped = True
            continue
        if in_single:
            if ch == "'":
                in_single = False
            else:
                token.append(ch)
            continue
        if in_double:
            if ch == '"':
                in_double = False
            else:
                token.append(ch)
            continue
        if ch in " \t\r\n":
            if token:
                tokens.append("".join(token))
                token = []
            continue
        if comments and ch == "#" and not token:
            break
        if ch == "'":
            in_single = True
            continue
        if ch == '"':
            in_double = True
            continue
        token.append(ch)
    if in_single or in_double or escaped:
        raise ValueError("No closing quotation")
    if token:
        tokens.append("".join(token))
    return tokens


def join(split_command):
    return " ".join(quote(part) for part in split_command)


__all__ = ["split", "quote", "join"]
