"""
theseus_pyexpat_cr — Clean-room pyexpat module.
No import of the standard `pyexpat` module.
Pure-Python XML tokenizer implementing the expat callback API.
"""

import re as _re


EXPAT_VERSION = 'expat_cleanroom'
XML_PARAM_ENTITY_PARSING_ALWAYS = 1
XML_PARAM_ENTITY_PARSING_NEVER = 0
XML_PARAM_ENTITY_PARSING_UNLESS_STANDALONE = 2

_TAG_RE = _re.compile(
    r'<(?:'
    r'!--.*?-->|'                              # comment
    r'!\[CDATA\[.*?\]\]>|'                     # CDATA
    r'\?[^?]*\?>|'                             # PI
    r'(?P<end>/)?(?P<tag>[A-Za-z_:][\w:.-]*)' # start/end tag
    r'(?P<attrs>[^>]*?)(?P<self>/)?'           # attrs + self-close
    r'>)',
    _re.DOTALL
)
_ATTR_RE = _re.compile(
    r'\s+([A-Za-z_:][\w:.-]*)(?:\s*=\s*(?:"([^"]*)"|\'([^\']*)\'|([^\s>]*)))?'
)
_ENTITY_RE = _re.compile(r'&(?:#(\d+)|#[xX]([0-9a-fA-F]+)|([A-Za-z]+));')
_ENTITIES = {'amp': '&', 'lt': '<', 'gt': '>', 'quot': '"', 'apos': "'"}


def _unescape(s):
    def _r(m):
        if m.group(1): return chr(int(m.group(1)))
        if m.group(2): return chr(int(m.group(2), 16))
        return _ENTITIES.get(m.group(3), m.group(0))
    return _ENTITY_RE.sub(_r, s)


class ExpatError(Exception):
    """Exception raised for XML parse errors."""
    def __init__(self, msg='', code=0, lineno=0, offset=0):
        self.code = code
        self.lineno = lineno
        self.offset = offset
        super().__init__(msg)

error = ExpatError


class XMLParserType:
    pass


class _Parser:
    """Minimal expat-compatible XML parser."""

    def __init__(self, encoding=None, namespace_separator=None):
        self._enc = encoding or 'utf-8'
        self._ns_sep = namespace_separator
        self._buf = b''
        # Public handler attributes
        self.StartElementHandler = None
        self.EndElementHandler = None
        self.CharacterDataHandler = None
        self.ProcessingInstructionHandler = None
        self.CommentHandler = None
        self.StartNamespaceDeclHandler = None
        self.EndNamespaceDeclHandler = None
        self.DefaultHandler = None
        self.DefaultHandlerExpand = None
        self.XmlDeclHandler = None
        self.StartDoctypeDeclHandler = None
        self.EndDoctypeDeclHandler = None
        self._done = False

    @property
    def CurrentLineNumber(self):
        return 1

    @property
    def CurrentColumnNumber(self):
        return 0

    @property
    def CurrentByteIndex(self):
        return 0

    def Parse(self, data, isfinal=False):
        if isinstance(data, str):
            data = data.encode(self._enc)
        self._buf += data
        if isfinal:
            self._parse_all()
            self._done = True
        return len(data)

    def ParseFile(self, f):
        return self.Parse(f.read(), isfinal=True)

    def SetBase(self, base):
        pass

    def GetBase(self):
        return None

    def GetInputContext(self):
        return None

    def SetParamEntityParsing(self, flag):
        return True

    def UseForeignDTD(self, flag=True):
        pass

    def _parse_all(self):
        try:
            text = self._buf.decode(self._enc)
        except UnicodeDecodeError as e:
            raise ExpatError(str(e))
        pos = 0
        n = len(text)
        while pos < n:
            lt = text.find('<', pos)
            if lt == -1:
                chunk = text[pos:]
                if chunk and self.CharacterDataHandler:
                    self.CharacterDataHandler(_unescape(chunk))
                break
            if lt > pos:
                chunk = text[pos:lt]
                if chunk and self.CharacterDataHandler:
                    self.CharacterDataHandler(_unescape(chunk))
            m = _TAG_RE.match(text, lt)
            if not m:
                pos = lt + 1
                continue
            pos = m.end()
            if m.group('end'):
                tag = m.group('tag')
                if self.EndElementHandler:
                    self.EndElementHandler(tag)
            elif m.group('tag'):
                tag = m.group('tag')
                attrs_str = m.group('attrs') or ''
                attrs = {}
                for am in _ATTR_RE.finditer(attrs_str):
                    aname = am.group(1)
                    aval = am.group(2) if am.group(2) is not None else \
                           am.group(3) if am.group(3) is not None else \
                           am.group(4) if am.group(4) is not None else None
                    attrs[aname] = _unescape(aval) if aval is not None else aval
                if self.StartElementHandler:
                    self.StartElementHandler(tag, attrs)
                if m.group('self') == '/':
                    if self.EndElementHandler:
                        self.EndElementHandler(tag)


def ParserCreate(encoding=None, namespace_separator=None):
    """Create an XML parser object."""
    return _Parser(encoding, namespace_separator)


def ErrorString(code):
    """Return a string description for an error code."""
    return f'XML error code {code}'


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def pyexp2_parser():
    """ParserCreate() creates an XML parser; returns True."""
    p = ParserCreate()
    found = []

    def start(tag, attrs):
        found.append(tag)

    p.StartElementHandler = start
    p.Parse('<root><child/></root>', True)
    return 'root' in found and 'child' in found


def pyexp2_version():
    """EXPAT_VERSION string is accessible; returns True."""
    return (isinstance(EXPAT_VERSION, str) and
            'expat' in EXPAT_VERSION.lower())


def pyexp2_error():
    """ExpatError exception class exists; returns True."""
    e = ExpatError('test error')
    return (issubclass(ExpatError, Exception) and
            ExpatError.__name__ == 'ExpatError' and
            str(e) == 'test error')


__all__ = [
    'ParserCreate', 'ExpatError', 'ErrorString', 'EXPAT_VERSION',
    'XMLParserType',
    'XML_PARAM_ENTITY_PARSING_ALWAYS', 'XML_PARAM_ENTITY_PARSING_NEVER',
    'XML_PARAM_ENTITY_PARSING_UNLESS_STANDALONE',
    'pyexp2_parser', 'pyexp2_version', 'pyexp2_error',
]
