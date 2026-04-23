"""
theseus_xml_cr2 — Clean-room XML/ElementTree utilities.
Do NOT import xml or xml.etree or any third-party library.
"""

import re
import io


# ---------------------------------------------------------------------------
# Element
# ---------------------------------------------------------------------------

class Element:
    """Minimal XML Element implementation."""

    def __init__(self, tag, attrib=None, **extra):
        if not isinstance(tag, str):
            raise TypeError(f"tag must be a string, not {type(tag)!r}")
        self.tag = tag
        self.attrib = {}
        if attrib:
            self.attrib.update(attrib)
        self.attrib.update(extra)
        self.text = None
        self.tail = None
        self._children = []

    # ------------------------------------------------------------------
    # Sequence / container interface
    # ------------------------------------------------------------------

    def __len__(self):
        return len(self._children)

    def __iter__(self):
        return iter(self._children)

    def __getitem__(self, index):
        return self._children[index]

    def __setitem__(self, index, element):
        self._children[index] = element

    def __delitem__(self, index):
        del self._children[index]

    def append(self, subelement):
        if not isinstance(subelement, Element):
            raise TypeError(f"expected an Element, not {type(subelement)!r}")
        self._children.append(subelement)

    def extend(self, elements):
        for element in elements:
            self.append(element)

    def insert(self, index, subelement):
        if not isinstance(subelement, Element):
            raise TypeError(f"expected an Element, not {type(subelement)!r}")
        self._children.insert(index, subelement)

    def remove(self, subelement):
        self._children.remove(subelement)

    def clear(self):
        self.attrib = {}
        self.text = None
        self.tail = None
        self._children = []

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def findall(self, match):
        """Return list of direct children whose tag matches *match*."""
        if match == '*':
            return list(self._children)
        return [child for child in self._children if child.tag == match]

    def find(self, match):
        """Return first direct child whose tag matches *match*, or None."""
        results = self.findall(match)
        return results[0] if results else None

    def findtext(self, match, default=None):
        """Return text of first matching child, or *default*."""
        child = self.find(match)
        if child is None:
            return default
        return child.text or default

    def get(self, key, default=None):
        return self.attrib.get(key, default)

    def set(self, key, value):
        self.attrib[key] = value

    def keys(self):
        return list(self.attrib.keys())

    def items(self):
        return list(self.attrib.items())

    # ------------------------------------------------------------------
    # Traversal
    # ------------------------------------------------------------------

    def iter(self, tag=None):
        """Depth-first iteration over this element and all sub-elements."""
        if tag is None or self.tag == tag:
            yield self
        for child in self._children:
            yield from child.iter(tag)

    def __repr__(self):
        return f"<Element {self.tag!r} at 0x{id(self):016x}>"


# ---------------------------------------------------------------------------
# SubElement
# ---------------------------------------------------------------------------

def SubElement(parent, tag, attrib=None, **extra):
    """Create a sub-element and attach it to *parent*."""
    if attrib is None:
        attrib = {}
    element = Element(tag, attrib, **extra)
    parent.append(element)
    return element


# ---------------------------------------------------------------------------
# ElementTree
# ---------------------------------------------------------------------------

class ElementTree:
    """Wrapper around an Element, representing an XML document."""

    def __init__(self, element=None, file=None):
        self._root = element
        if file is not None:
            self.parse(file)

    def getroot(self):
        return self._root

    def parse(self, source):
        if isinstance(source, str):
            with open(source, 'rb') as f:
                data = f.read()
        elif hasattr(source, 'read'):
            data = source.read()
        else:
            raise TypeError(f"cannot parse from {type(source)!r}")
        if isinstance(data, (bytes, bytearray)):
            data = _decode_xml_bytes(data)
        self._root = fromstring(data)
        return self._root

    def write(self, file_or_path, encoding='unicode', xml_declaration=False,
              short_empty_elements=True):
        data = tostring(self._root, encoding=encoding,
                        xml_declaration=xml_declaration,
                        short_empty_elements=short_empty_elements)
        if isinstance(file_or_path, str):
            mode = 'wb' if isinstance(data, bytes) else 'w'
            with open(file_or_path, mode) as f:
                f.write(data)
        else:
            file_or_path.write(data)

    def find(self, match):
        return self._root.find(match)

    def findall(self, match):
        return self._root.findall(match)

    def iter(self, tag=None):
        return self._root.iter(tag)


# ---------------------------------------------------------------------------
# XML Parser (hand-written, no xml imports)
# ---------------------------------------------------------------------------

# Tokeniser patterns
_ENCODING_RE = re.compile(
    r'''<\?xml[^?]*encoding\s*=\s*['"]([^'"]+)['"]''', re.IGNORECASE)

_TOKEN_RE = re.compile(
    r'''(?x)
    (?P<comment><!--.*?-->)                          # XML comment
    |(?P<pi><\?.*?\?>)                               # processing instruction
    |(?P<cdata><!\[CDATA\[.*?\]\]>)                  # CDATA section
    |(?P<doctype><!DOCTYPE[^>]*>)                    # DOCTYPE
    |(?P<end_tag></\s*(?P<end_name>[^\s>]+)\s*>)     # end tag
    |(?P<start_tag>                                  # start tag (possibly self-closing)
        <\s*(?P<start_name>[^\s>/]+)
        (?P<attrs>[^>]*)
        (?P<self_close>/)?>
      )
    |(?P<text>[^<]+)                                 # text content
    ''',
    re.DOTALL
)

_ATTR_RE = re.compile(
    r'''(?x)
    \s*(?P<name>[^\s=>/]+)
    \s*=\s*
    (?:
        "(?P<dq>[^"]*)"
      | '(?P<sq>[^']*)'
      | (?P<uq>[^\s>]+)
    )
    ''',
    re.DOTALL
)

_ENTITY_MAP = {
    'amp': '&',
    'lt': '<',
    'gt': '>',
    'apos': "'",
    'quot': '"',
}


def _unescape(text):
    """Replace XML entities and character references."""
    if '&' not in text:
        return text

    def replace(m):
        ref = m.group(1)
        if ref.startswith('#'):
            try:
                if ref.startswith('#x') or ref.startswith('#X'):
                    return chr(int(ref[2:], 16))
                else:
                    return chr(int(ref[1:]))
            except (ValueError, OverflowError):
                return m.group(0)
        return _ENTITY_MAP.get(ref, m.group(0))

    return re.sub(r'&([^;]+);', replace, text)


def _decode_xml_bytes(data):
    """Detect encoding from BOM or XML declaration and decode."""
    if data.startswith(b'\xef\xbb\xbf'):
        return data[3:].decode('utf-8')
    if data.startswith(b'\xff\xfe'):
        return data[2:].decode('utf-16-le')
    if data.startswith(b'\xfe\xff'):
        return data[2:].decode('utf-16-be')
    # Try to find encoding declaration in first 200 bytes
    head = data[:200].decode('ascii', errors='replace')
    m = _ENCODING_RE.search(head)
    if m:
        enc = m.group(1).lower()
        return data.decode(enc)
    return data.decode('utf-8')


def _parse_attrs(attrs_str):
    """Parse attribute string into dict."""
    result = {}
    for m in _ATTR_RE.finditer(attrs_str):
        name = m.group('name')
        value = m.group('dq') or m.group('sq') or m.group('uq') or ''
        result[name] = _unescape(value)
    return result


def _tokenize(text):
    """Yield (type, value, extra) tuples from XML text."""
    for m in _TOKEN_RE.finditer(text):
        kind = m.lastgroup
        if kind == 'comment':
            yield ('comment', m.group(), {})
        elif kind == 'pi':
            yield ('pi', m.group(), {})
        elif kind == 'cdata':
            content = m.group()[9:-3]  # strip <![CDATA[ and ]]>
            yield ('text', content, {})
        elif kind == 'doctype':
            yield ('doctype', m.group(), {})
        elif kind == 'end_tag':
            yield ('end', m.group('end_name'), {})
        elif kind == 'start_tag':
            name = m.group('start_name')
            attrs = _parse_attrs(m.group('attrs') or '')
            self_close = bool(m.group('self_close'))
            yield ('start', name, {'attrs': attrs, 'self_close': self_close})
        elif kind == 'text':
            yield ('text', m.group(), {})


def _build_tree(tokens):
    """Build Element tree from token stream; return root Element."""
    stack = []
    root = None

    for kind, value, extra in tokens:
        if kind == 'start':
            elem = Element(value, extra['attrs'])
            if stack:
                stack[-1].append(elem)
            else:
                if root is None:
                    root = elem
            if not extra['self_close']:
                stack.append(elem)
        elif kind == 'end':
            if stack:
                stack.pop()
        elif kind == 'text':
            text = _unescape(value)
            if stack:
                current = stack[-1]
                if len(current) == 0:
                    # text before any children → .text
                    current.text = (current.text or '') + text
                else:
                    # text after a child → last child's .tail
                    last = current[-1]
                    last.tail = (last.tail or '') + text
            # text outside root is ignored (whitespace between prolog etc.)
        # comments, pi, doctype are ignored

    return root


def fromstring(text):
    """Parse XML from a string and return the root Element."""
    if isinstance(text, (bytes, bytearray)):
        text = _decode_xml_bytes(text)
    tokens = _tokenize(text)
    root = _build_tree(tokens)
    if root is None:
        raise ParseError("no element found")
    return root


def parse(source):
    """Parse XML from a file path or file-like object; return ElementTree."""
    tree = ElementTree()
    tree.parse(source)
    return tree


# ---------------------------------------------------------------------------
# tostring
# ---------------------------------------------------------------------------

def _escape_text(text):
    text = text.replace('&', '&amp;')
    text = text.replace('<', '&lt;')
    text = text.replace('>', '&gt;')
    return text


def _escape_attrib(text):
    text = text.replace('&', '&amp;')
    text = text.replace('<', '&lt;')
    text = text.replace('>', '&gt;')
    text = text.replace('"', '&quot;')
    return text


def _serialize(elem, short_empty_elements=True):
    """Recursively serialize an Element to a list of string parts."""
    parts = []
    # Opening tag
    tag = elem.tag
    attribs = ''.join(
        f' {k}="{_escape_attrib(v)}"' for k, v in elem.attrib.items()
    )
    has_children = len(elem._children) > 0
    has_text = elem.text and elem.text.strip() != '' or (elem.text is not None and elem.text != '')

    if short_empty_elements and not has_children and not has_text:
        parts.append(f'<{tag}{attribs} />')
    else:
        parts.append(f'<{tag}{attribs}>')
        if elem.text:
            parts.append(_escape_text(elem.text))
        for child in elem._children:
            parts.extend(_serialize(child, short_empty_elements))
            if child.tail:
                parts.append(_escape_text(child.tail))
        parts.append(f'</{tag}>')
    return parts


def tostring(element, encoding='unicode', xml_declaration=False,
             short_empty_elements=True):
    """Serialize *element* to an XML string."""
    parts = _serialize(element, short_empty_elements)
    result = ''.join(parts)
    if xml_declaration:
        result = '<?xml version=\'1.0\' encoding=\'us-ascii\'?>\n' + result
    if encoding == 'unicode':
        return result
    return result.encode(encoding)


# ---------------------------------------------------------------------------
# iterparse
# ---------------------------------------------------------------------------

class iterparse:
    """Incremental XML parser that yields (event, element) pairs."""

    def __init__(self, source, events=None):
        if events is None:
            events = ('end',)
        self._events_filter = set(events)
        if isinstance(source, str):
            with open(source, 'rb') as f:
                data = f.read()
            text = _decode_xml_bytes(data)
        elif hasattr(source, 'read'):
            data = source.read()
            if isinstance(data, (bytes, bytearray)):
                text = _decode_xml_bytes(data)
            else:
                text = data
        else:
            raise TypeError(f"cannot parse from {type(source)!r}")
        self._text = text
        self._events = []
        self._root = None
        self._parse()

    def _parse(self):
        stack = []
        root = None
        events = self._events
        ef = self._events_filter

        for kind, value, extra in _tokenize(self._text):
            if kind == 'start':
                elem = Element(value, extra['attrs'])
                if stack:
                    stack[-1].append(elem)
                else:
                    if root is None:
                        root = elem
                if 'start' in ef:
                    events.append(('start', elem))
                if not extra['self_close']:
                    stack.append(elem)
                else:
                    if 'end' in ef:
                        events.append(('end', elem))
            elif kind == 'end':
                if stack:
                    elem = stack.pop()
                    if 'end' in ef:
                        events.append(('end', elem))
            elif kind == 'text':
                text = _unescape(value)
                if stack:
                    current = stack[-1]
                    if len(current) == 0:
                        current.text = (current.text or '') + text
                    else:
                        last = current[-1]
                        last.tail = (last.tail or '') + text

        self._root = root

    @property
    def root(self):
        return self._root

    def __iter__(self):
        return iter(self._events)


# ---------------------------------------------------------------------------
# ParseError
# ---------------------------------------------------------------------------

class ParseError(SyntaxError):
    pass


# ---------------------------------------------------------------------------
# Invariant test functions (zero-arg, return hardcoded results)
# ---------------------------------------------------------------------------

def xml2_findall():
    """root with 2 'child' elements; root.findall('child') has length 2."""
    root = Element('root')
    SubElement(root, 'child')
    SubElement(root, 'child')
    return len(root.findall('child'))


def xml2_iter():
    """list(root.iter()) includes root and all children — length > 1."""
    root = Element('root')
    SubElement(root, 'child1')
    SubElement(root, 'child2')
    return len(list(root.iter())) > 1


def xml2_subelement():
    """SubElement(root, 'new') appends child; root[-1].tag == 'new'."""
    root = Element('root')
    SubElement(root, 'existing')
    SubElement(root, 'new')
    return root[-1].tag


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = [
    'Element',
    'SubElement',
    'ElementTree',
    'parse',
    'fromstring',
    'tostring',
    'iterparse',
    'ParseError',
    'xml2_findall',
    'xml2_iter',
    'xml2_subelement',
]