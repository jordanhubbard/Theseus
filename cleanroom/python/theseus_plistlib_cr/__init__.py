"""
Clean-room implementation of plistlib for the Theseus project.
Supports XML plist format (FMT_XML). FMT_BINARY raises NotImplementedError.
"""

import re
import base64
from datetime import datetime

# Format constants
FMT_XML = 'xml'
FMT_BINARY = 'binary'


def dumps(value, fmt=FMT_XML):
    """Serialize a Python object to plist bytes."""
    if fmt == FMT_BINARY:
        raise NotImplementedError("Binary plist format is not supported.")
    
    lines = []
    lines.append("<?xml version=\"1.0\" encoding=\"UTF-8\"?>")
    lines.append("<!DOCTYPE plist PUBLIC \"-//Apple//DTD PLIST 1.0//EN\" "
                 "\"http://www.apple.com/DTDs/PropertyList-1.0.dtd\">")
    lines.append("<plist version=\"1.0\">")
    _serialize_value(value, lines, indent=0)
    lines.append("</plist>")
    return ("\n".join(lines) + "\n").encode("utf-8")


def _escape_xml(s):
    """Escape special XML characters in a string."""
    s = s.replace("&", "&amp;")
    s = s.replace("<", "&lt;")
    s = s.replace(">", "&gt;")
    s = s.replace("\"", "&quot;")
    return s


def _serialize_value(value, lines, indent):
    """Recursively serialize a Python value to XML plist lines."""
    pad = "\t" * indent
    
    if isinstance(value, bool):
        # bool must be checked before int since bool is subclass of int
        if value:
            lines.append(pad + "<true/>")
        else:
            lines.append(pad + "<false/>")
    elif isinstance(value, int):
        lines.append(pad + "<integer>{}</integer>".format(value))
    elif isinstance(value, float):
        lines.append(pad + "<real>{}</real>".format(repr(value)))
    elif isinstance(value, str):
        lines.append(pad + "<string>{}</string>".format(_escape_xml(value)))
    elif isinstance(value, bytes):
        encoded = base64.b64encode(value).decode("ascii")
        lines.append(pad + "<data>{}</data>".format(encoded))
    elif isinstance(value, dict):
        lines.append(pad + "<dict>")
        for k, v in value.items():
            if not isinstance(k, str):
                raise TypeError("Dict keys must be strings in plist format.")
            lines.append(pad + "\t<key>{}</key>".format(_escape_xml(k)))
            _serialize_value(v, lines, indent + 1)
        lines.append(pad + "</dict>")
    elif isinstance(value, (list, tuple)):
        lines.append(pad + "<array>")
        for item in value:
            _serialize_value(item, lines, indent + 1)
        lines.append(pad + "</array>")
    elif isinstance(value, datetime):
        # ISO 8601 format
        lines.append(pad + "<date>{}</date>".format(value.strftime("%Y-%m-%dT%H:%M:%SZ")))
    else:
        raise TypeError("Unsupported type: {}".format(type(value)))


def loads(data):
    """Parse plist bytes and return a Python object."""
    if isinstance(data, (bytes, bytearray)):
        text = data.decode("utf-8")
    else:
        text = data
    
    parser = _PlistParser(text)
    return parser.parse()


class _PlistParser:
    """Simple XML plist parser."""
    
    def __init__(self, text):
        self.text = text
        self.pos = 0
    
    def parse(self):
        # Skip XML declaration and DOCTYPE
        self._skip_prolog()
        # Parse <plist ...>
        self._expect_tag_open("plist")
        value = self._parse_value()
        self._skip_whitespace()
        self._expect_tag_close("plist")
        return value
    
    def _skip_prolog(self):
        """Skip XML declaration, DOCTYPE, and comments."""
        while self.pos < len(self.text):
            self._skip_whitespace()
            if self.pos >= len(self.text):
                break
            if self.text[self.pos:self.pos+4] == "<!--":
                end = self.text.find("-->", self.pos)
                if end == -1:
                    raise ValueError("Unclosed comment")
                self.pos = end + 3
            elif self.text[self.pos:self.pos+2] == "<?":
                end = self.text.find("?>", self.pos)
                if end == -1:
                    raise ValueError("Unclosed processing instruction")
                self.pos = end + 2
            elif self.text[self.pos:self.pos+9] == "<!DOCTYPE":
                end = self.text.find(">", self.pos)
                if end == -1:
                    raise ValueError("Unclosed DOCTYPE")
                self.pos = end + 1
            else:
                break
    
    def _skip_whitespace(self):
        while self.pos < len(self.text) and self.text[self.pos] in " \t\n\r":
            self.pos += 1
    
    def _expect_tag_open(self, name):
        """Consume an opening tag like <plist version="1.0"> and return attributes."""
        self._skip_whitespace()
        if self.pos >= len(self.text) or self.text[self.pos] != '<':
            raise ValueError("Expected '<' at position {}".format(self.pos))
        end = self.text.find('>', self.pos)
        if end == -1:
            raise ValueError("Unclosed tag")
        tag_content = self.text[self.pos+1:end]
        self.pos = end + 1
        # tag_content should start with name
        tag_content = tag_content.strip()
        if not tag_content.startswith(name):
            raise ValueError("Expected tag <{}>, got <{}>".format(name, tag_content))
        return tag_content
    
    def _expect_tag_close(self, name):
        """Consume a closing tag like </plist>."""
        self._skip_whitespace()
        expected = "</{}>".format(name)
        if self.text[self.pos:self.pos+len(expected)] != expected:
            # Try to find it anyway
            raise ValueError("Expected closing tag </{}> at position {}, got: {}".format(
                name, self.pos, self.text[self.pos:self.pos+20]))
        self.pos += len(expected)
    
    def _peek_tag(self):
        """Peek at the next tag name without consuming it."""
        self._skip_whitespace()
        if self.pos >= len(self.text) or self.text[self.pos] != '<':
            return None
        end = self.text.find('>', self.pos)
        if end == -1:
            return None
        tag_content = self.text[self.pos+1:end].strip()
        # Extract tag name
        m = re.match(r'(/?\w+)', tag_content)
        if m:
            return m.group(1)
        return None
    
    def _parse_value(self):
        """Parse the next plist value."""
        self._skip_whitespace()
        if self.pos >= len(self.text):
            raise ValueError("Unexpected end of data")
        
        # Peek at the tag
        tag = self._peek_tag()
        if tag is None:
            raise ValueError("Expected a value tag at position {}".format(self.pos))
        
        if tag == 'string':
            return self._parse_simple_tag('string', str)
        elif tag == 'integer':
            return self._parse_simple_tag('integer', int)
        elif tag == 'real':
            return self._parse_simple_tag('real', float)
        elif tag == 'true':
            self._consume_self_closing('true')
            return True
        elif tag == 'false':
            self._consume_self_closing('false')
            return False
        elif tag == 'data':
            return self._parse_data()
        elif tag == 'date':
            return self._parse_date()
        elif tag == 'dict':
            return self._parse_dict()
        elif tag == 'array':
            return self._parse_array()
        else:
            raise ValueError("Unknown plist tag: <{}>".format(tag))
    
    def _consume_self_closing(self, name):
        """Consume a self-closing tag like <true/> or <false/>."""
        self._skip_whitespace()
        # Could be <true/> or <true></true>
        tag1 = "<{}/>" .format(name)
        tag2_open = "<{}>".format(name)
        tag2_close = "</{}>".format(name)
        
        if self.text[self.pos:self.pos+len(tag1)] == tag1:
            self.pos += len(tag1)
        elif self.text[self.pos:self.pos+len(tag2_open)] == tag2_open:
            self.pos += len(tag2_open)
            self._skip_whitespace()
            if self.text[self.pos:self.pos+len(tag2_close)] == tag2_close:
                self.pos += len(tag2_close)
            else:
                raise ValueError("Expected </{}> after <{}>".format(name, name))
        else:
            raise ValueError("Expected <{}/>".format(name))
    
    def _parse_simple_tag(self, name, converter):
        """Parse a simple tag like <string>content</string>."""
        self._skip_whitespace()
        open_tag = "<{}>".format(name)
        close_tag = "</{}>".format(name)
        
        if self.text[self.pos:self.pos+len(open_tag)] != open_tag:
            raise ValueError("Expected {} at position {}".format(open_tag, self.pos))
        self.pos += len(open_tag)
        
        end = self.text.find(close_tag, self.pos)
        if end == -1:
            raise ValueError("Unclosed tag <{}>".format(name))
        
        content = self.text[self.pos:end]
        self.pos = end + len(close_tag)
        
        # Unescape XML entities
        content = self._unescape_xml(content)
        return converter(content)
    
    def _unescape_xml(self, s):
        """Unescape XML entities."""
        s = s.replace("&amp;", "&")
        s = s.replace("&lt;", "<")
        s = s.replace("&gt;", ">")
        s = s.replace("&quot;", "\"")
        s = s.replace("&apos;", "'")
        return s
    
    def _parse_data(self):
        """Parse a <data> tag containing base64-encoded bytes."""
        self._skip_whitespace()
        open_tag = "<data>"
        close_tag = "</data>"
        
        if self.text[self.pos:self.pos+len(open_tag)] != open_tag:
            raise ValueError("Expected <data>")
        self.pos += len(open_tag)
        
        end = self.text.find(close_tag, self.pos)
        if end == -1:
            raise ValueError("Unclosed <data> tag")
        
        content = self.text[self.pos:end].strip()
        self.pos = end + len(close_tag)
        
        # Remove whitespace from base64 content
        content = re.sub(r'\s+', '', content)
        return base64.b64decode(content)
    
    def _parse_date(self):
        """Parse a <date> tag."""
        self._skip_whitespace()
        open_tag = "<date>"
        close_tag = "</date>"
        
        if self.text[self.pos:self.pos+len(open_tag)] != open_tag:
            raise ValueError("Expected <date>")
        self.pos += len(open_tag)
        
        end = self.text.find(close_tag, self.pos)
        if end == -1:
            raise ValueError("Unclosed <date> tag")
        
        content = self.text[self.pos:end].strip()
        self.pos = end + len(close_tag)
        
        # Parse ISO 8601 date
        try:
            return datetime.strptime(content, "%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            raise ValueError("Invalid date format: {}".format(content))
    
    def _parse_dict(self):
        """Parse a <dict> element."""
        self._skip_whitespace()
        open_tag = "<dict>"
        close_tag = "</dict>"
        
        if self.text[self.pos:self.pos+len(open_tag)] != open_tag:
            raise ValueError("Expected <dict>")
        self.pos += len(open_tag)
        
        result = {}
        while True:
            self._skip_whitespace()
            if self.text[self.pos:self.pos+len(close_tag)] == close_tag:
                self.pos += len(close_tag)
                break
            
            # Parse <key>...</key>
            key_open = "<key>"
            key_close = "</key>"
            if self.text[self.pos:self.pos+len(key_open)] != key_open:
                raise ValueError("Expected <key> in dict at position {}".format(self.pos))
            self.pos += len(key_open)
            
            end = self.text.find(key_close, self.pos)
            if end == -1:
                raise ValueError("Unclosed <key> tag")
            key = self._unescape_xml(self.text[self.pos:end])
            self.pos = end + len(key_close)
            
            # Parse value
            value = self._parse_value()
            result[key] = value
        
        return result
    
    def _parse_array(self):
        """Parse an <array> element."""
        self._skip_whitespace()
        open_tag = "<array>"
        close_tag = "</array>"
        
        if self.text[self.pos:self.pos+len(open_tag)] != open_tag:
            raise ValueError("Expected <array>")
        self.pos += len(open_tag)
        
        result = []
        while True:
            self._skip_whitespace()
            if self.text[self.pos:self.pos+len(close_tag)] == close_tag:
                self.pos += len(close_tag)
                break
            value = self._parse_value()
            result.append(value)
        
        return result


# Invariant functions
def plistlib_dumps_type():
    """dumps({'k': 'v'}) returns bytes — returns True."""
    return isinstance(dumps({'k': 'v'}), bytes)


def plistlib_roundtrip():
    """loads(dumps({'key': 'value'}))['key'] == 'value'"""
    return loads(dumps({'key': 'value'}))['key']


def plistlib_loads_int():
    """loads(dumps({'n': 42}))['n'] == 42"""
    return loads(dumps({'n': 42}))['n']