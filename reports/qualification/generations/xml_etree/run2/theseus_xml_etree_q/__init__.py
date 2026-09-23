# generation B xml class


class _Element:
    def __init__(self, text):
        self.text = text


def _unescape(value):
    entities = {
        "amp": "&",
        "lt": "<",
        "gt": ">",
        "apos": "'",
        "quot": '"',
    }
    result = []
    position = 0
    while position < len(value):
        if value[position] != "&":
            result.append(value[position])
            position += 1
            continue
        end = value.find(";", position + 1)
        if end < 0:
            raise ValueError("unterminated entity reference")
        reference = value[position + 1:end]
        if reference.startswith("#x"):
            character = chr(int(reference[2:], 16))
        elif reference.startswith("#"):
            character = chr(int(reference[1:], 10))
        elif reference in entities:
            character = entities[reference]
        else:
            raise ValueError("unknown entity reference")
        result.append(character)
        position = end + 1
    return "".join(result)


def fromstring(text):
    if isinstance(text, bytes):
        text = text.decode("utf-8")
    if not isinstance(text, str):
        raise TypeError("fromstring() argument must be str or bytes")

    position = 0
    length = len(text)
    while position < length and text[position].isspace():
        position += 1
    if text.startswith("<?xml", position):
        declaration_end = text.find("?>", position + 5)
        if declaration_end < 0:
            raise ValueError("unterminated XML declaration")
        position = declaration_end + 2
        while position < length and text[position].isspace():
            position += 1
    if position >= length or text[position] != "<":
        raise ValueError("expected root element")

    opening_end = text.find(">", position + 1)
    if opening_end < 0:
        raise ValueError("unterminated start tag")
    opening = text[position + 1:opening_end].strip()
    if not opening or opening[0] in "!?/":
        raise ValueError("invalid root element")
    if opening.endswith("/"):
        return _Element(None)

    name = opening.split(None, 1)[0]
    content_start = opening_end + 1
    cursor = content_start
    pieces = []
    while cursor < length:
        next_tag = text.find("<", cursor)
        if next_tag < 0:
            raise ValueError("missing end tag")
        pieces.append(text[cursor:next_tag])
        if text.startswith("<![CDATA[", next_tag):
            cdata_end = text.find("]]>", next_tag + 9)
            if cdata_end < 0:
                raise ValueError("unterminated CDATA section")
            pieces.append(text[next_tag + 9:cdata_end])
            cursor = cdata_end + 3
            continue
        if text.startswith("<!--", next_tag):
            comment_end = text.find("-->", next_tag + 4)
            if comment_end < 0:
                raise ValueError("unterminated comment")
            cursor = comment_end + 3
            continue
        if text.startswith("</", next_tag):
            close_end = text.find(">", next_tag + 2)
            if close_end < 0 or text[next_tag + 2:close_end].strip() != name:
                raise ValueError("mismatched end tag")
            return _Element(_unescape("".join(pieces)))
        return _Element(_unescape("".join(pieces)) or None)
    raise ValueError("missing end tag")
