"""
Clean-room minimal XML ElementTree parser implementation.
No imports of xml, xml.etree, or any xml submodule.
"""

import re


class Element:
    """XML element with tag, attrib dict, text, tail, children."""
    
    def __init__(self, tag, attrib=None):
        self.tag = tag
        self.attrib = attrib if attrib is not None else {}
        self.text = None
        self.tail = None
        self._children = []
    
    def append(self, child):
        self._children.append(child)
    
    def __len__(self):
        return len(self._children)
    
    def __iter__(self):
        return iter(self._children)
    
    def __getitem__(self, index):
        return self._children[index]
    
    def find(self, tag):
        for child in self._children:
            if child.tag == tag:
                return child
        return None
    
    def findall(self, tag):
        return [child for child in self._children if child.tag == tag]
    
    def get(self, key, default=None):
        return self.attrib.get(key, default)
    
    def set(self, key, value):
        self.attrib[key] = value
    
    def keys(self):
        return self.attrib.keys()
    
    def items(self):
        return self.attrib.items()
    
    def iter(self, tag=None):
        if tag is None or self.tag == tag:
            yield self
        for child in self._children:
            yield from child.iter(tag)


def SubElement(parent, tag, attrib=None):
    """Create a child element appended to parent."""
    if attrib is None:
        attrib = {}
    child = Element(tag, attrib)
    parent.append(child)
    return child


# XML escape sequences
_ESCAPE_MAP = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&apos;',
}

_UNESCAPE_MAP = {v: k for k, v in _ESCAPE_MAP.items()}

def _escape_text(text):
    """Escape special XML characters in text content."""
    if text is None:
        return ''
    result = []
    for ch in text:
        result.append(_ESCAPE_MAP.get(ch, ch))
    return ''.join(result)

def _escape_attrib(text):
    """Escape special XML characters in attribute values."""
    return _escape_text(text)

def _unescape(text):
    """Unescape XML entities."""
    if '&' not in text:
        return text
    
    # Handle numeric character references
    def replace_entity(m):
        entity = m.group(0)
        if entity in _UNESCAPE_MAP:
            return _UNESCAPE_MAP[entity]
        if entity.startswith('&#x') or entity.startswith('&#X'):
            try:
                return chr(int(entity[3:-1], 16))
            except (ValueError, OverflowError):
                return entity
        if entity.startswith('&#'):
            try:
                return chr(int(entity[2:-1]))
            except (ValueError, OverflowError):
                return entity
        return entity
    
    return re.sub(r'&[^;]+;', replace_entity, text)


class _XMLParser:
    """Simple XML parser that builds an Element tree."""
    
    def __init__(self, xml_str):
        if isinstance(xml_str, bytes):
            # Try to detect encoding from XML declaration
            xml_str = self._decode(xml_str)
        self.xml = xml_str
        self.pos = 0
        self.length = len(xml_str)
    
    def _decode(self, data):
        """Decode bytes to string, handling XML encoding declaration."""
        # Try UTF-8 first (most common)
        try:
            text = data.decode('utf-8')
        except UnicodeDecodeError:
            text = data.decode('latin-1')
        return text
    
    def parse(self):
        """Parse the XML and return the root Element."""
        self._skip_whitespace()
        
        # Skip XML declaration if present
        if self._peek_str('<?xml'):
            self._skip_processing_instruction()
            self._skip_whitespace()
        
        # Skip DOCTYPE if present
        while self._peek_str('<!DOCTYPE') or self._peek_str('<!--'):
            if self._peek_str('<!--'):
                self._skip_comment()
            else:
                self._skip_doctype()
            self._skip_whitespace()
        
        # Parse root element
        root = self._parse_element()
        return root
    
    def _peek_str(self, s):
        return self.xml[self.pos:self.pos + len(s)] == s
    
    def _skip_whitespace(self):
        while self.pos < self.length and self.xml[self.pos] in ' \t\n\r':
            self.pos += 1
    
    def _skip_processing_instruction(self):
        """Skip <?...?> processing instruction."""
        self.pos += 2  # skip <?
        while self.pos < self.length - 1:
            if self.xml[self.pos] == '?' and self.xml[self.pos + 1] == '>':
                self.pos += 2
                return
            self.pos += 1
    
    def _skip_comment(self):
        """Skip <!-- ... --> comment."""
        self.pos += 4  # skip <!--
        while self.pos < self.length - 2:
            if self.xml[self.pos:self.pos + 3] == '-->':
                self.pos += 3
                return
            self.pos += 1
    
    def _skip_doctype(self):
        """Skip <!DOCTYPE ...> declaration."""
        self.pos += 2  # skip <!
        depth = 1
        while self.pos < self.length:
            ch = self.xml[self.pos]
            if ch == '<':
                depth += 1
            elif ch == '>':
                depth -= 1
                if depth == 0:
                    self.pos += 1
                    return
            self.pos += 1
    
    def _parse_element(self):
        """Parse an XML element starting at current position."""
        self._skip_whitespace()
        
        if self.pos >= self.length:
            raise ValueError("Unexpected end of XML")
        
        if self.xml[self.pos] != '<':
            raise ValueError(f"Expected '<' at position {self.pos}, got {self.xml[self.pos]!r}")
        
        self.pos += 1  # skip '<'
        
        # Handle comments
        if self._peek_str('!--'):
            self._skip_comment_from_bang()
            return None
        
        # Handle CDATA
        if self._peek_str('![CDATA['):
            # This shouldn't be at element level, but handle gracefully
            raise ValueError("CDATA not expected at element level")
        
        # Read tag name
        tag = self._read_name()
        
        # Read attributes
        attrib = {}
        self._skip_whitespace()
        
        while self.pos < self.length and self.xml[self.pos] not in ('>', '/'):
            attr_name = self._read_name()
            self._skip_whitespace()
            
            if self.pos < self.length and self.xml[self.pos] == '=':
                self.pos += 1  # skip '='
                self._skip_whitespace()
                attr_value = self._read_attr_value()
                attrib[attr_name] = _unescape(attr_value)
            else:
                # Boolean attribute (no value)
                attrib[attr_name] = attr_name
            
            self._skip_whitespace()
        
        element = Element(tag, attrib)
        
        # Check for self-closing tag
        if self.pos < self.length and self.xml[self.pos] == '/':
            self.pos += 1  # skip '/'
            if self.pos < self.length and self.xml[self.pos] == '>':
                self.pos += 1  # skip '>'
            return element
        
        if self.pos < self.length and self.xml[self.pos] == '>':
            self.pos += 1  # skip '>'
        else:
            raise ValueError(f"Expected '>' at position {self.pos}")
        
        # Parse children and text content
        text_parts = []
        
        while self.pos < self.length:
            # Check for closing tag
            if self._peek_str('</'):
                # Read closing tag
                self.pos += 2  # skip '</'
                close_tag = self._read_name()
                self._skip_whitespace()
                if self.pos < self.length and self.xml[self.pos] == '>':
                    self.pos += 1
                if close_tag != tag:
                    raise ValueError(f"Mismatched tags: <{tag}> closed by </{close_tag}>")
                break
            elif self.xml[self.pos] == '<':
                # Check what kind of tag
                if self.xml[self.pos + 1:self.pos + 4] == '!--':
                    # Comment
                    self.pos += 1
                    self._skip_comment_from_bang()
                    continue
                elif self.xml[self.pos + 1:self.pos + 9] == '![CDATA[':
                    # CDATA section
                    self.pos += 9  # skip <![CDATA[
                    cdata_text = self._read_cdata()
                    if not element._children:
                        text_parts.append(cdata_text)
                    else:
                        # Append to last child's tail
                        last_child = element._children[-1]
                        if last_child.tail is None:
                            last_child.tail = cdata_text
                        else:
                            last_child.tail += cdata_text
                    continue
                elif self.xml[self.pos + 1:self.pos + 2] == '?':
                    # Processing instruction
                    self.pos += 1
                    self._skip_processing_instruction_from_q()
                    continue
                else:
                    # Child element
                    if text_parts:
                        if not element._children:
                            element.text = _unescape(''.join(text_parts))
                        else:
                            last_child = element._children[-1]
                            if last_child.tail is None:
                                last_child.tail = _unescape(''.join(text_parts))
                            else:
                                last_child.tail += _unescape(''.join(text_parts))
                        text_parts = []
                    
                    child = self._parse_element()
                    if child is not None:
                        element.append(child)
            else:
                # Text content
                text_parts.append(self._read_text())
        
        # Handle remaining text
        if text_parts:
            text = _unescape(''.join(text_parts))
            if not element._children:
                element.text = text
            else:
                last_child = element._children[-1]
                if last_child.tail is None:
                    last_child.tail = text
                else:
                    last_child.tail += text
        
        return element
    
    def _skip_comment_from_bang(self):
        """Skip comment starting after '<', positioned at '!--'."""
        self.pos += 3  # skip !--
        while self.pos < self.length - 2:
            if self.xml[self.pos:self.pos + 3] == '-->':
                self.pos += 3
                return
            self.pos += 1
    
    def _skip_processing_instruction_from_q(self):
        """Skip PI starting after '<', positioned at '?'."""
        self.pos += 1  # skip ?
        while self.pos < self.length - 1:
            if self.xml[self.pos] == '?' and self.xml[self.pos + 1] == '>':
                self.pos += 2
                return
            self.pos += 1
    
    def _read_cdata(self):
        """Read CDATA content until ]]>."""
        start = self.pos
        while self.pos < self.length - 2:
            if self.xml[self.pos:self.pos + 3] == ']]>':
                result = self.xml[start:self.pos]
                self.pos += 3
                return result
            self.pos += 1
        raise ValueError("Unterminated CDATA section")
    
    def _read_name(self):
        """Read an XML name (tag or attribute name)."""
        start = self.pos
        # First character: letter, underscore, or colon
        if self.pos < self.length and (self.xml[self.pos].isalpha() or 
                                        self.xml[self.pos] in ('_', ':', '-')):
            self.pos += 1
        else:
            raise ValueError(f"Invalid name start at position {self.pos}: {self.xml[self.pos:self.pos+10]!r}")
        
        # Subsequent characters
        while self.pos < self.length:
            ch = self.xml[self.pos]
            if ch.isalnum() or ch in ('_', ':', '-', '.'):
                self.pos += 1
            else:
                break
        
        return self.xml[start:self.pos]
    
    def _read_attr_value(self):
        """Read an attribute value (quoted string)."""
        if self.pos >= self.length:
            raise ValueError("Unexpected end of XML in attribute value")
        
        quote = self.xml[self.pos]
        if quote not in ('"', "'"):
            raise ValueError(f"Expected quote character, got {quote!r}")
        
        self.pos += 1  # skip opening quote
        start = self.pos
        
        while self.pos < self.length and self.xml[self.pos] != quote:
            self.pos += 1
        
        value = self.xml[start:self.pos]
        
        if self.pos < self.length:
            self.pos += 1  # skip closing quote
        
        return value
    
    def _read_text(self):
        """Read text content until '<'."""
        start = self.pos
        while self.pos < self.length and self.xml[self.pos] != '<':
            self.pos += 1
        return self.xml[start:self.pos]


def fromstring(xml_str):
    """Parse XML string into Element tree."""
    parser = _XMLParser(xml_str)
    return parser.parse()


def tostring(element, encoding=None, xml_declaration=False):
    """Serialize Element back to bytes/string."""
    parts = []
    _serialize_element(element, parts)
    result = ''.join(parts)
    if encoding == 'unicode':
        return result
    if encoding is not None:
        return result.encode(encoding)
    return result


def _serialize_element(element, parts):
    """Recursively serialize an element to string parts."""
    # Opening tag
    parts.append('<')
    parts.append(element.tag)
    
    # Attributes
    for key, value in element.attrib.items():
        parts.append(' ')
        parts.append(key)
        parts.append('="')
        parts.append(_escape_attrib(str(value)))
        parts.append('"')
    
    if not element._children and not element.text:
        parts.append(' />')
    else:
        parts.append('>')
        
        # Text content
        if element.text:
            parts.append(_escape_text(element.text))
        
        # Children
        for child in element._children:
            _serialize_element(child, parts)
            if child.tail:
                parts.append(_escape_text(child.tail))
        
        # Closing tag
        parts.append('</')
        parts.append(element.tag)
        parts.append('>')


# Test functions as specified in the invariants

def xml_et_tag():
    """fromstring('<root/>').tag == 'root'"""
    return fromstring('<root/>').tag


def xml_et_attrib():
    """fromstring('<a x="1"/>').attrib['x'] == '1'"""
    return fromstring('<a x="1"/>').attrib['x']


def xml_et_child_count():
    """fromstring('<r><a/><b/></r>') has 2 children"""
    return len(fromstring('<r><a/><b/></r>'))


__all__ = ['Element', 'SubElement', 'fromstring', 'tostring',
           'xml_et_tag', 'xml_et_attrib', 'xml_et_child_count']