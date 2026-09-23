# generation A xml scan

__all__ = ["fromstring", "XmlElement"]


class XmlElement(object):
    def __init__(self, tag):
        self.tag = tag
        self.text = None
        self.tail = None
        self.attrib = {}
        self._children = []


def fromstring(text):
    if isinstance(text, bytes):
        text = text.decode("utf-8")
    if not isinstance(text, str):
        raise TypeError("fromstring() argument must be str or bytes")
    data = text.strip()
    if not data:
        raise ValueError("no element found")
    pos = 0
    pos = _skip_prologue(data, pos)
    root, pos = _parse_element(data, pos)
    pos = _skip_ws(data, pos)
    if pos != len(data):
        raise ValueError("junk after document element")
    return root


def _skip_ws(s, i):
    n = len(s)
    while i < n and s[i] in " \t\n\r":
        i += 1
    return i


def _skip_prologue(s, i):
    n = len(s)
    while i < n:
        i = _skip_ws(s, i)
        if i >= n:
            break
        if s.startswith("<?", i):
            end = s.find("?>", i + 2)
            if end < 0:
                raise ValueError("malformed processing instruction")
            i = end + 2
            continue
        if s.startswith("<!--", i):
            end = s.find("-->", i + 4)
            if end < 0:
                raise ValueError("malformed comment")
            i = end + 3
            continue
        if s.startswith("<!DOCTYPE", i):
            end = s.find(">", i + 9)
            if end < 0:
                raise ValueError("malformed doctype")
            i = end + 1
            continue
        break
    return i


def _parse_name(s, i):
    n = len(s)
    if i >= n:
        raise ValueError("unexpected end of data")
    start = i
    c = s[i]
    if not (c == "_" or c == ":" or ("A" <= c <= "Z") or ("a" <= c <= "z")):
        raise ValueError("invalid tag name")
    i += 1
    while i < n:
        c = s[i]
        if c == "_" or c == ":" or c == "-" or c == "." or ("0" <= c <= "9") or ("A" <= c <= "Z") or ("a" <= c <= "z"):
            i += 1
        else:
            break
    return s[start:i], i


def _parse_element(s, i):
    i = _skip_ws(s, i)
    n = len(s)
    if i >= n or s[i] != "<":
        raise ValueError("no element found")
    if s.startswith("</", i):
        raise ValueError("mismatched tag")
    if s.startswith("<!--", i) or s.startswith("<?", i):
        raise ValueError("invalid element")
    i += 1
    tag, i = _parse_name(s, i)
    elem = XmlElement(tag)
    i = _skip_ws(s, i)
    while i < n and s[i] != ">" and s[i] != "/":
        key, i = _parse_name(s, i)
        i = _skip_ws(s, i)
        if i >= n or s[i] != "=":
            raise ValueError("invalid attribute")
        i += 1
        i = _skip_ws(s, i)
        if i >= n or s[i] not in ("'", '"'):
            raise ValueError("invalid attribute value")
        quote = s[i]
        i += 1
        start = i
        while i < n and s[i] != quote:
            i += 1
        if i >= n:
            raise ValueError("unterminated attribute value")
        elem.attrib[key] = _unescape(s[start:i])
        i += 1
        i = _skip_ws(s, i)
    if i >= n:
        raise ValueError("unclosed tag")
    if s[i] == "/":
        if i + 1 >= n or s[i + 1] != ">":
            raise ValueError("invalid empty element tag")
        return elem, i + 2
    if s[i] != ">":
        raise ValueError("invalid tag")
    i += 1
    text_parts = []
    while i < n:
        if s.startswith("<![CDATA[", i):
            end = s.find("]]>", i + 9)
            if end < 0:
                raise ValueError("unclosed CDATA")
            text_parts.append(s[i + 9 : end])
            i = end + 3
            continue
        if s.startswith("<!--", i):
            end = s.find("-->", i + 4)
            if end < 0:
                raise ValueError("malformed comment")
            i = end + 3
            continue
        if s[i] == "<":
            if s.startswith("</", i):
                i += 2
                end_tag, i = _parse_name(s, i)
                i = _skip_ws(s, i)
                if i >= n or s[i] != ">":
                    raise ValueError("invalid closing tag")
                if end_tag != tag:
                    raise ValueError("mismatched tag")
                if text_parts:
                    elem.text = _unescape("".join(text_parts))
                return elem, i + 1
            child, i = _parse_element(s, i)
            elem._children.append(child)
            text_parts = []
            continue
        j = i
        while j < n and s[j] != "<":
            j += 1
        text_parts.append(s[i:j])
        i = j
    raise ValueError("unclosed tag")


def _unescape(s):
    out = []
    i = 0
    n = len(s)
    while i < n:
        if s[i] != "&":
            out.append(s[i])
            i += 1
            continue
        semi = s.find(";", i + 1)
        if semi < 0:
            out.append(s[i])
            i += 1
            continue
        ent = s[i + 1 : semi]
        if ent == "amp":
            out.append("&")
        elif ent == "lt":
            out.append("<")
        elif ent == "gt":
            out.append(">")
        elif ent == "quot":
            out.append('"')
        elif ent == "apos":
            out.append("'")
        elif ent.startswith("#x") and len(ent) > 2:
            try:
                out.append(chr(int(ent[2:], 16)))
            except ValueError:
                out.append("&" + ent + ";")
        elif ent.startswith("#") and len(ent) > 1:
            try:
                out.append(chr(int(ent[1:], 10)))
            except ValueError:
                out.append("&" + ent + ";")
        else:
            out.append("&" + ent + ";")
        i = semi + 1
    return "".join(out)
