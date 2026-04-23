"""
theseus_html_parser_cr: Clean-room HTML tag parser.
Do NOT import html or html.parser.
"""

import re


class HTMLParseError(Exception):
    """Exception raised for HTML parse errors."""
    def __init__(self, msg, position=(None, None)):
        self.msg = msg
        self.lineno = position[0]
        self.offset = position[1]
        if self.lineno is not None:
            msg += f', at line {self.lineno}'
        if self.offset is not None:
            msg += f', column {self.offset}'
        super().__init__(msg)


_ENTITY_RE = re.compile(r'&(?:#(\d+)|#[xX]([0-9a-fA-F]+)|([A-Za-z][A-Za-z0-9]*));')

_HTML_ENTITIES = {
    'amp': '&', 'lt': '<', 'gt': '>', 'quot': '"', 'apos': "'",
    'nbsp': '\xa0', 'copy': '©', 'reg': '®', 'deg': '°', 'plusmn': '±',
    'micro': 'µ', 'para': '¶', 'middot': '·', 'frac12': '½', 'frac14': '¼',
    'frac34': '¾', 'times': '×', 'divide': '÷', 'szlig': 'ß',
    'agrave': 'à', 'aacute': 'á', 'eacute': 'é', 'egrave': 'è',
    'iacute': 'í', 'oacute': 'ó', 'uacute': 'ú', 'ntilde': 'ñ',
    'Agrave': 'À', 'Aacute': 'Á', 'Eacute': 'É', 'Oacute': 'Ó',
}


def unescape(s):
    """Unescape HTML entities in string s."""
    def _replace(m):
        dec = m.group(1)
        if dec:
            return chr(int(dec))
        hex_ = m.group(2)
        if hex_:
            return chr(int(hex_, 16))
        name = m.group(3)
        return _HTML_ENTITIES.get(name, m.group(0))
    return _ENTITY_RE.sub(_replace, s)


class HTMLParser:
    """
    A clean-room HTML parser that tokenizes HTML and fires callbacks
    for start tags, end tags, and text data.
    """

    def feed(self, data):
        """
        Parse the given HTML string, firing callbacks as tokens are found.
        """
        pos = 0
        length = len(data)

        while pos < length:
            # Look for the next '<'
            lt_pos = data.find('<', pos)

            if lt_pos == -1:
                # No more tags; rest is text data
                text = data[pos:]
                if text:
                    self.handle_data(text)
                break

            # Text before the tag
            if lt_pos > pos:
                text = data[pos:lt_pos]
                if text:
                    self.handle_data(text)

            # Find the closing '>'
            gt_pos = data.find('>', lt_pos)
            if gt_pos == -1:
                # Malformed tag, treat rest as data
                text = data[lt_pos:]
                if text:
                    self.handle_data(text)
                break

            tag_content = data[lt_pos + 1:gt_pos]
            pos = gt_pos + 1

            # Check for comment <!-- ... -->
            if tag_content.startswith('!--'):
                # It's a comment, skip it (find --> properly)
                comment_end = data.find('-->', lt_pos)
                if comment_end != -1:
                    pos = comment_end + 3
                # else skip to after '>'
                continue

            # Check for DOCTYPE
            if tag_content.lower().startswith('!doctype'):
                continue

            # Check for end tag
            if tag_content.startswith('/'):
                # End tag
                end_tag_name = tag_content[1:].strip().split()[0] if tag_content[1:].strip() else ''
                end_tag_name = end_tag_name.rstrip('/').lower()
                if end_tag_name:
                    self.handle_endtag(end_tag_name)
                continue

            # Self-closing or start tag
            # Remove trailing slash for self-closing tags like <br/>
            is_self_closing = tag_content.endswith('/')
            if is_self_closing:
                tag_content_clean = tag_content[:-1].strip()
            else:
                tag_content_clean = tag_content.strip()

            if not tag_content_clean:
                continue

            # Parse tag name and attributes
            tag_name, attrs = _parse_tag(tag_content_clean)

            if tag_name:
                self.handle_starttag(tag_name.lower(), attrs)
                if is_self_closing:
                    self.handle_endtag(tag_name.lower())

    def handle_starttag(self, tag, attrs):
        """Called when a start tag is encountered. Override in subclasses."""
        pass

    def handle_endtag(self, tag):
        """Called when an end tag is encountered. Override in subclasses."""
        pass

    def handle_data(self, data):
        """Called when text data is encountered. Override in subclasses."""
        pass


def _parse_tag(tag_content):
    """
    Parse a tag's content (without < and >) into (tag_name, attrs).
    attrs is a list of (name, value) tuples.
    """
    tag_content = tag_content.strip()
    if not tag_content:
        return '', []

    # Split tag name from attributes
    # Tag name ends at first whitespace
    parts = tag_content.split(None, 1)
    tag_name = parts[0]
    attr_string = parts[1] if len(parts) > 1 else ''

    attrs = _parse_attrs(attr_string)
    return tag_name, attrs


def _parse_attrs(attr_string):
    """
    Parse an attribute string into a list of (name, value) tuples.
    Handles: name="value", name='value', name=value, name (boolean)
    """
    attrs = []
    attr_string = attr_string.strip()

    # Use a regex to find attributes
    # Pattern matches:
    #   name="value"  name='value'  name=value  name
    pattern = re.compile(
        r'([\w\-:.]+)'           # attribute name
        r'(?:\s*=\s*'            # optional = with surrounding whitespace
        r'(?:'
        r'"([^"]*)"'             # double-quoted value
        r"|'([^']*)'"            # single-quoted value
        r'|([^\s"\'>/]*)'        # unquoted value
        r'))?',
        re.IGNORECASE
    )

    for m in pattern.finditer(attr_string):
        name = m.group(1)
        if m.group(2) is not None:
            value = m.group(2)
        elif m.group(3) is not None:
            value = m.group(3)
        elif m.group(4) is not None:
            value = m.group(4)
        else:
            value = None
        attrs.append((name.lower(), value))

    return attrs


def find_tags(html_str):
    """
    Return a list of tag names found in html_str.
    Includes both start tags and end tags (in order).
    Self-closing tags appear once.
    """
    tags = []

    class _TagFinder(HTMLParser):
        def handle_starttag(self, tag, attrs):
            tags.append(tag)

        def handle_endtag(self, tag):
            tags.append(tag)

    parser = _TagFinder()
    parser.feed(html_str)
    return tags


def find_text(html_str):
    """
    Return concatenated text content from html_str (text between tags).
    """
    texts = []

    class _TextFinder(HTMLParser):
        def handle_data(self, data):
            texts.append(data)

    parser = _TextFinder()
    parser.feed(html_str)
    return ''.join(texts)


# ---------------------------------------------------------------------------
# Invariant demo functions (used by the test harness)
# ---------------------------------------------------------------------------

def html_parser_tags():
    """
    Invariant: parsing '<p>hi</p><br/>' returns a list containing
    tag names ['p', 'p', 'br'] (order: start tags and end tags).
    Returns True if the result is a non-empty list of strings.
    """
    result = find_tags('<p>hi</p><br/>')
    # Expected something like ['p', 'p', 'br'] — a non-empty list of tag names
    return (
        isinstance(result, list)
        and len(result) > 0
        and all(isinstance(t, str) for t in result)
        and 'p' in result
        and 'br' in result
    )


def html_parser_starttag():
    """
    Invariant: handle_starttag fires for '<div class="x">'.
    Returns the value of the 'class' attribute, which should be "x".
    """
    found = {}

    class _AttrCapture(HTMLParser):
        def handle_starttag(self, tag, attrs):
            for name, value in attrs:
                found[name] = value

    parser = _AttrCapture()
    parser.feed('<div class="x">')
    return found.get('class', '')


def html_parser_data():
    """
    Invariant: handle_data fires for text between tags.
    Returns the text content of '<p>hello</p>', which should be "hello".
    """
    return find_text('<p>hello</p>')


# ---------------------------------------------------------------------------
# New invariant functions (htmlparser2_ prefix for the cleanroom spec)
# ---------------------------------------------------------------------------

def htmlparser2_parse():
    """HTMLParser can parse simple tags; returns True."""
    result = find_tags('<html><body><p>hello</p></body></html>')
    return 'html' in result and 'body' in result


def htmlparser2_attrs():
    """HTMLParser handles attributes correctly; returns True."""
    found = {}

    class _AC(HTMLParser):
        def handle_starttag(self, tag, attrs):
            for name, val in attrs:
                found[name] = val

    _AC().feed('<a href="https://example.com" class="link">text</a>')
    return found.get('href') == 'https://example.com' and found.get('class') == 'link'


def htmlparser2_data():
    """HTMLParser handles text data; returns True."""
    texts = []

    class _DC(HTMLParser):
        def handle_data(self, data):
            texts.append(data)

    _DC().feed('<p>Hello World</p>')
    return 'Hello World' in texts


def htmlparser2_entities():
    """unescape() handles HTML entities; returns True."""
    return (unescape('&lt;b&gt;') == '<b>' and
            unescape('&amp;') == '&' and
            unescape('&#65;') == 'A' and
            unescape('&#x41;') == 'A')


def htmlparser2_error():
    """HTMLParseError exception class exists; returns True."""
    e = HTMLParseError('test error', (1, 5))
    return (issubclass(HTMLParseError, Exception) and
            e.lineno == 1 and
            e.offset == 5)