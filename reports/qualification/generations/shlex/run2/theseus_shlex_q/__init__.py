# generation B readers

_SAFE_CHARS = frozenset(
    "abcdefghijklmnopqrstuvwxyz"
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "0123456789"
    "@%+=:,./-"
)


def _read_single(s, index):
    start = index
    while index < len(s) and s[index] != "'":
        index += 1
    if index == len(s):
        raise ValueError("No closing quotation")
    return s[start:index], index + 1


def _read_double(s, index):
    pieces = []
    while index < len(s):
        char = s[index]
        if char == '"':
            return "".join(pieces), index + 1
        if char == "\\":
            if index + 1 == len(s):
                raise ValueError("No escaped character")
            escaped = s[index + 1]
            if escaped in '\\"$`\n':
                pieces.append(escaped)
            else:
                pieces.append("\\")
                pieces.append(escaped)
            index += 2
            continue
        pieces.append(char)
        index += 1
    raise ValueError("No closing quotation")


def _read_word(s, index, comments, posix):
    pieces = []
    while index < len(s):
        char = s[index]
        if char.isspace() or (comments and char == "#"):
            break
        if char == "'":
            piece, index = _read_single(s, index + 1)
            if posix:
                pieces.append(piece)
            else:
                pieces.append("'" + piece + "'")
            continue
        if char == '"':
            piece, index = _read_double(s, index + 1)
            if posix:
                pieces.append(piece)
            else:
                pieces.append('"' + piece + '"')
            continue
        if char == "\\":
            if index + 1 == len(s):
                raise ValueError("No escaped character")
            if posix:
                pieces.append(s[index + 1])
            else:
                pieces.append("\\")
                pieces.append(s[index + 1])
            index += 2
            continue
        pieces.append(char)
        index += 1
    return "".join(pieces), index


def split(s, comments=False, posix=True):
    words = []
    index = 0
    while index < len(s):
        while index < len(s) and s[index].isspace():
            index += 1
        if index == len(s):
            break
        if comments and s[index] == "#":
            while index < len(s) and s[index] != "\n":
                index += 1
            continue
        word, new_index = _read_word(s, index, comments, posix)
        words.append(word)
        index = new_index
        if comments and index < len(s) and s[index] == "#":
            while index < len(s) and s[index] != "\n":
                index += 1
    return words


def quote(s):
    if s and all(char in _SAFE_CHARS for char in s):
        return s
    if not s:
        return "''"
    return "'" + s.replace("'", "'\"'\"'") + "'"


def join(split_command):
    return " ".join(quote(token) for token in split_command)
