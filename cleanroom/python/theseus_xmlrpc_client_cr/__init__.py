"""Clean-room implementation of xmlrpc.client for Theseus."""

import re as _re
import datetime as _datetime
import time as _time
import base64 as _base64
from io import BytesIO as _BytesIO


# ---------------------------------------------------------------------------
# Constants / Fault codes
# ---------------------------------------------------------------------------

PARSE_ERROR = -32700
SERVER_ERROR = -32600
APPLICATION_ERROR = -32500
SYSTEM_ERROR = -32400
TRANSPORT_ERROR = -32300

NOT_WELLFORMED_ERROR = -32700
UNSUPPORTED_ENCODING = -32701
INVALID_ENCODING_CHAR = -32702
INVALID_XMLRPC = -32600
METHOD_NOT_FOUND = -32601
INVALID_METHOD_PARAMS = -32602
INTERNAL_ERROR = -32603

MAXINT = 2 ** 31 - 1
MININT = -(2 ** 31)


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------

class Error(Exception):
    """Base class for client errors."""

    def __str__(self):
        return repr(self)


class ProtocolError(Error):
    def __init__(self, url, errcode, errmsg, headers):
        Error.__init__(self)
        self.url = url
        self.errcode = errcode
        self.errmsg = errmsg
        self.headers = headers

    def __repr__(self):
        return (
            "<%s for %s: %s %s>" %
            (self.__class__.__name__, self.url, self.errcode, self.errmsg)
        )


class ResponseError(Error):
    pass


class Fault(Error):
    """Indicates an XML-RPC fault response."""

    def __init__(self, faultCode, faultString, **extra):
        Error.__init__(self)
        self.faultCode = faultCode
        self.faultString = faultString

    def __repr__(self):
        return "<%s %s: %r>" % (
            self.__class__.__name__, self.faultCode, self.faultString
        )


# ---------------------------------------------------------------------------
# Boolean wrapper
# ---------------------------------------------------------------------------

class Boolean:
    """Boolean wrapper for explicit XML-RPC booleans."""

    def __init__(self, value=0):
        self.value = bool(value)

    def encode(self, out):
        out.write("<value><boolean>%d</boolean></value>\n" % int(self.value))

    def __cmp__(self, other):
        if isinstance(other, Boolean):
            other = other.value
        return (self.value > other) - (self.value < other)

    def __eq__(self, other):
        if isinstance(other, Boolean):
            return self.value == other.value
        return self.value == bool(other)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self.value)

    def __repr__(self):
        if self.value:
            return "<Boolean True at 0x%x>" % id(self)
        return "<Boolean False at 0x%x>" % id(self)

    def __int__(self):
        return int(self.value)

    def __bool__(self):
        return self.value

    __nonzero__ = __bool__


True_ = Boolean(1)
False_ = Boolean(0)


def _boolean(value, _truefalse=(False_, True_)):
    return _truefalse[bool(value)]


# ---------------------------------------------------------------------------
# DateTime wrapper
# ---------------------------------------------------------------------------

class DateTime:
    """A wrapper for XML-RPC dateTime.iso8601 values."""

    def __init__(self, value=0):
        if isinstance(value, str):
            self.value = value
        elif isinstance(value, _datetime.datetime):
            self.value = value.strftime("%Y%m%dT%H:%M:%S")
        elif isinstance(value, (tuple, _time.struct_time)):
            self.value = _time.strftime("%Y%m%dT%H:%M:%S", value)
        elif isinstance(value, (int, float)):
            self.value = _time.strftime(
                "%Y%m%dT%H:%M:%S", _time.localtime(value)
            )
        else:
            self.value = str(value)

    def make_comparable(self, other):
        if isinstance(other, DateTime):
            return self.value, other.value
        if isinstance(other, _datetime.datetime):
            return self.value, other.strftime("%Y%m%dT%H:%M:%S")
        if isinstance(other, str):
            return self.value, other
        if hasattr(other, "timetuple"):
            return self.timetuple(), other.timetuple()
        raise TypeError("Cannot compare DateTime with %s" % type(other).__name__)

    def __lt__(self, other):
        s, o = self.make_comparable(other)
        return s < o

    def __le__(self, other):
        s, o = self.make_comparable(other)
        return s <= o

    def __gt__(self, other):
        s, o = self.make_comparable(other)
        return s > o

    def __ge__(self, other):
        s, o = self.make_comparable(other)
        return s >= o

    def __eq__(self, other):
        try:
            s, o = self.make_comparable(other)
        except TypeError:
            return NotImplemented
        return s == o

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self.value)

    def timetuple(self):
        return _time.strptime(self.value, "%Y%m%dT%H:%M:%S")

    def __str__(self):
        return self.value

    def __repr__(self):
        return "<DateTime %r at 0x%x>" % (self.value, id(self))

    def decode(self, data):
        self.value = str(data).strip()

    def encode(self, out):
        out.write("<value><dateTime.iso8601>")
        out.write(self.value)
        out.write("</dateTime.iso8601></value>\n")


def _datetime_type(data):
    value = _datetime.datetime.strptime(data, "%Y%m%dT%H:%M:%S")
    return value


# ---------------------------------------------------------------------------
# Binary wrapper
# ---------------------------------------------------------------------------

class Binary:
    """Wrapper for binary data."""

    def __init__(self, data=None):
        if data is None:
            data = b""
        elif not isinstance(data, (bytes, bytearray)):
            raise TypeError("expected bytes or bytearray, not %s" %
                            data.__class__.__name__)
        self.data = bytes(data)

    def __str__(self):
        return self.data.decode("latin-1")

    def __eq__(self, other):
        if isinstance(other, Binary):
            return self.data == other.data
        return self.data == other

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self.data)

    def decode(self, data):
        self.data = _base64.decodebytes(data)

    def encode(self, out):
        out.write("<value><base64>\n")
        encoded = _base64.encodebytes(self.data)
        out.write(encoded.decode("ascii"))
        out.write("</base64></value>\n")


def _binary(data):
    value = Binary()
    value.decode(data)
    return value


# ---------------------------------------------------------------------------
# Marshalling
# ---------------------------------------------------------------------------

def _escape(s):
    s = s.replace("&", "&amp;")
    s = s.replace("<", "&lt;")
    s = s.replace(">", "&gt;")
    return s


class Marshaller:
    """Generate XML-RPC value blocks."""

    dispatch = {}

    def __init__(self, encoding=None, allow_none=False):
        self.memo = {}
        self.data = None
        self.encoding = encoding
        self.allow_none = allow_none

    def dumps(self, values):
        out = []
        write = out.append
        if isinstance(values, Fault):
            write("<fault>\n")
            self.__dump({
                "faultCode": values.faultCode,
                "faultString": values.faultString,
            }, write)
            write("</fault>\n")
        else:
            write("<params>\n")
            for v in values:
                write("<param>\n")
                self.__dump(v, write)
                write("</param>\n")
            write("</params>\n")
        result = "".join(out)
        return result

    def __dump(self, value, write):
        try:
            f = self.dispatch[type(value)]
        except KeyError:
            # check subclasses
            if not hasattr(value, "_marshallable_attrs"):
                for type_, fn in self.dispatch.items():
                    if isinstance(value, type_):
                        fn(self, value, write)
                        return
            raise TypeError("cannot marshal %s objects" % type(value).__name__)
        else:
            f(self, value, write)

    def dump_nil(self, value, write):
        if not self.allow_none:
            raise TypeError("cannot marshal None unless allow_none is enabled")
        write("<value><nil/></value>")
    dispatch[type(None)] = dump_nil

    def dump_bool(self, value, write):
        write("<value><boolean>")
        write("1" if value else "0")
        write("</boolean></value>\n")
    dispatch[bool] = dump_bool

    def dump_long(self, value, write):
        if value > MAXINT or value < MININT:
            raise OverflowError("int exceeds XML-RPC limits")
        write("<value><int>")
        write(str(int(value)))
        write("</int></value>\n")
    dispatch[int] = dump_long

    def dump_double(self, value, write):
        write("<value><double>")
        write(repr(value))
        write("</double></value>\n")
    dispatch[float] = dump_double

    def dump_unicode(self, value, write):
        write("<value><string>")
        write(_escape(value))
        write("</string></value>\n")
    dispatch[str] = dump_unicode

    def dump_bytes(self, value, write):
        write("<value><base64>\n")
        encoded = _base64.encodebytes(value)
        write(encoded.decode("ascii"))
        write("</base64></value>\n")
    dispatch[bytes] = dump_bytes
    dispatch[bytearray] = dump_bytes

    def dump_array(self, value, write):
        if id(value) in self.memo:
            raise TypeError("cannot marshal recursive sequences")
        self.memo[id(value)] = None
        try:
            write("<value><array><data>\n")
            for v in value:
                self.__dump(v, write)
            write("</data></array></value>\n")
        finally:
            del self.memo[id(value)]
    dispatch[tuple] = dump_array
    dispatch[list] = dump_array

    def dump_struct(self, value, write):
        if id(value) in self.memo:
            raise TypeError("cannot marshal recursive dictionaries")
        self.memo[id(value)] = None
        try:
            write("<value><struct>\n")
            for k, v in value.items():
                write("<member>\n")
                if not isinstance(k, str):
                    raise TypeError(
                        "dictionary key must be a string"
                    )
                write("<name>%s</name>\n" % _escape(k))
                self.__dump(v, write)
                write("</member>\n")
            write("</struct></value>\n")
        finally:
            del self.memo[id(value)]
    dispatch[dict] = dump_struct

    def dump_datetime(self, value, write):
        write("<value><dateTime.iso8601>")
        write(value.strftime("%Y%m%dT%H:%M:%S"))
        write("</dateTime.iso8601></value>\n")
    dispatch[_datetime.datetime] = dump_datetime

    def dump_instance(self, value, write):
        # support DateTime, Binary, Boolean instances via encode()
        if hasattr(value, "encode"):
            value.encode(self)
            return
        # fallback to __dict__
        self.dump_struct(value.__dict__, write)
    dispatch[DateTime] = lambda self, v, w: v.encode(_WriterAdapter(w))
    dispatch[Binary] = lambda self, v, w: v.encode(_WriterAdapter(w))
    dispatch[Boolean] = lambda self, v, w: v.encode(_WriterAdapter(w))


class _WriterAdapter:
    """Adapts a list-append callable into an object with .write()."""

    def __init__(self, write):
        self.write = write


# ---------------------------------------------------------------------------
# Unmarshalling
# ---------------------------------------------------------------------------

class Unmarshaller:
    """Convert an XML-RPC document into Python values."""

    def __init__(self, use_datetime=False, use_builtin_types=False):
        self._type = None
        self._stack = []
        self._marks = []
        self._data = []
        self._methodname = None
        self._encoding = "utf-8"
        self.append = self._stack.append
        self._use_datetime = use_builtin_types or use_datetime
        self._use_bytes = use_builtin_types

    def close(self):
        if self._type is None or self._marks:
            raise ResponseError("response error")
        if self._type == "fault":
            raise Fault(**self._stack[0])
        return tuple(self._stack)

    def getmethodname(self):
        return self._methodname

    def xml(self, encoding, standalone):
        self._encoding = encoding

    def start(self, tag, attrs):
        if tag == "array" or tag == "struct":
            self._marks.append(len(self._stack))
        self._data = []
        if self._value and tag == "value":
            self._data = []
        self._value = (tag == "value")

    def data(self, text):
        self._data.append(text)

    def end(self, tag):
        try:
            f = self.dispatch[tag]
        except KeyError:
            return
        return f(self, "".join(self._data))

    dispatch = {}

    def end_dispatch(self, tag, data):
        try:
            f = self.dispatch[tag]
        except KeyError:
            return
        return f(self, data)

    def end_nil(self, data):
        self.append(None)
        self._value = 0
    dispatch["nil"] = end_nil

    def end_boolean(self, data):
        if data == "0":
            self.append(False)
        elif data == "1":
            self.append(True)
        else:
            raise TypeError("bad boolean value")
        self._value = 0
    dispatch["boolean"] = end_boolean

    def end_int(self, data):
        self.append(int(data))
        self._value = 0
    dispatch["i4"] = end_int
    dispatch["i8"] = end_int
    dispatch["int"] = end_int

    def end_double(self, data):
        self.append(float(data))
        self._value = 0
    dispatch["double"] = end_double

    def end_string(self, data):
        self.append(data)
        self._value = 0
    dispatch["string"] = end_string
    dispatch["name"] = end_string

    def end_array(self, data):
        mark = self._marks.pop()
        self._stack[mark:] = [self._stack[mark:]]
        self._value = 0
    dispatch["array"] = end_array

    def end_struct(self, data):
        mark = self._marks.pop()
        items = self._stack[mark:]
        d = {}
        for i in range(0, len(items), 2):
            d[items[i]] = items[i + 1]
        self._stack[mark:] = [d]
        self._value = 0
    dispatch["struct"] = end_struct

    def end_base64(self, data):
        value = Binary()
        value.decode(data.encode("ascii"))
        if self._use_bytes:
            self.append(value.data)
        else:
            self.append(value)
        self._value = 0
    dispatch["base64"] = end_base64

    def end_dateTime(self, data):
        value = DateTime()
        value.decode(data)
        if self._use_datetime:
            self.append(_datetime_type(data))
        else:
            self.append(value)
        self._value = 0
    dispatch["dateTime.iso8601"] = end_dateTime

    def end_value(self, data):
        # default: treat as string
        if self._value:
            self.end_string(data)
    dispatch["value"] = end_value

    def end_params(self, data):
        self._type = "params"
    dispatch["params"] = end_params

    def end_fault(self, data):
        self._type = "fault"
    dispatch["fault"] = end_fault

    def end_methodName(self, data):
        self._methodname = data
        self._type = "methodName"
    dispatch["methodName"] = end_methodName


# ---------------------------------------------------------------------------
# Simple XML parser (regex-based, sufficient for XML-RPC)
# ---------------------------------------------------------------------------

_TAG_RE = _re.compile(
    r"<\s*(/?)\s*([A-Za-z_][\w\.\-]*)\s*([^/>]*?)\s*(/?)\s*>"
)
_DECL_RE = _re.compile(r"<\?xml[^?]*\?>", _re.DOTALL)
_COMMENT_RE = _re.compile(r"<!--.*?-->", _re.DOTALL)


def _unescape(s):
    s = s.replace("&lt;", "<")
    s = s.replace("&gt;", ">")
    s = s.replace("&quot;", '"')
    s = s.replace("&apos;", "'")
    s = s.replace("&amp;", "&")
    # numeric refs
    def numref(m):
        body = m.group(1)
        try:
            if body.startswith("x") or body.startswith("X"):
                return chr(int(body[1:], 16))
            return chr(int(body))
        except (ValueError, OverflowError):
            return m.group(0)
    s = _re.sub(r"&#([0-9a-fA-FxX]+);", numref, s)
    return s


def _parse_xml(data, target):
    """Tiny XML parser that drives an Unmarshaller-like target."""
    if isinstance(data, bytes):
        try:
            data = data.decode("utf-8")
        except UnicodeDecodeError:
            data = data.decode("latin-1")
    # strip declaration & comments
    data = _DECL_RE.sub("", data)
    data = _COMMENT_RE.sub("", data)

    pos = 0
    text_buf = []
    while pos < len(data):
        m = _TAG_RE.search(data, pos)
        if not m:
            break
        # accumulate text between pos and tag start
        if m.start() > pos:
            text_buf.append(data[pos:m.start()])
        closing, name, _attrs, self_close = m.group(1), m.group(2), m.group(3), m.group(4)
        text = _unescape("".join(text_buf))
        text_buf = []
        if closing:
            target.data(text)
            target.end(name)
        else:
            target.start(name, {})
            if self_close:
                target.end(name)
            else:
                # next text belongs to this tag
                pass
        pos = m.end()
        # collect text after tag
        # (handled at top of next iteration)
    return target


# ---------------------------------------------------------------------------
# Top-level dumps / loads
# ---------------------------------------------------------------------------

def dumps(params, methodname=None, methodresponse=None,
          encoding=None, allow_none=False):
    """Convert a tuple of arguments into an XML-RPC packet."""
    if not isinstance(params, (tuple, Fault)):
        raise TypeError("argument must be tuple or Fault instance")
    if isinstance(params, Fault):
        methodresponse = 1
    elif methodresponse and isinstance(params, tuple):
        if len(params) != 1:
            raise ValueError("response tuple must be a singleton")

    if not encoding:
        encoding = "utf-8"

    if encoding != "utf-8":
        xmlheader = '<?xml version="1.0" encoding="%s"?>\n' % encoding
    else:
        xmlheader = "<?xml version='1.0'?>\n"

    m = Marshaller(encoding, allow_none)
    body = m.dumps(params)

    if methodname:
        if not isinstance(methodname, str):
            methodname = methodname.encode(encoding)
        data = (
            xmlheader +
            "<methodCall>\n"
            "<methodName>" + _escape(methodname) + "</methodName>\n" +
            body +
            "</methodCall>\n"
        )
    elif methodresponse:
        data = (
            xmlheader +
            "<methodResponse>\n" +
            body +
            "</methodResponse>\n"
        )
    else:
        return body
    return data


def loads(data, use_datetime=False, use_builtin_types=False):
    """Parse an XML-RPC packet, returning (params, methodname)."""
    u = Unmarshaller(
        use_datetime=use_datetime, use_builtin_types=use_builtin_types
    )
    _parse_xml(data, u)
    return u.close(), u.getmethodname()


def gzip_encode(data):
    raise NotImplementedError("gzip not supported in clean-room build")


def gzip_decode(data, max_decode=20 * 1024 * 1024):
    raise NotImplementedError("gzip not supported in clean-room build")


# ---------------------------------------------------------------------------
# Invariants
# ---------------------------------------------------------------------------

def xmlrpc2_boolean():
    """Boolean wrapper round-trips and serializes correctly."""
    b_true = Boolean(1)
    b_false = Boolean(0)
    if not bool(b_true):
        return False
    if bool(b_false):
        return False
    if b_true == b_false:
        return False
    out = _WriterAdapter([].append)
    buf = []
    out2 = type("X", (), {"write": buf.append})()
    b_true.encode(out2)
    s_true = "".join(buf)
    if "<boolean>1</boolean>" not in s_true:
        return False
    buf = []
    out2 = type("X", (), {"write": buf.append})()
    b_false.encode(out2)
    s_false = "".join(buf)
    if "<boolean>0</boolean>" not in s_false:
        return False
    # also check that dumps emits booleans
    payload = dumps((True, False))
    if "<boolean>1</boolean>" not in payload:
        return False
    if "<boolean>0</boolean>" not in payload:
        return False
    return True


def xmlrpc2_fault():
    """Fault objects construct, str, and round-trip via dumps."""
    f = Fault(42, "boom")
    if f.faultCode != 42:
        return False
    if f.faultString != "boom":
        return False
    if "42" not in repr(f):
        return False
    if not isinstance(f, Exception):
        return False
    payload = dumps(f)
    if "<fault>" not in payload:
        return False
    if "faultCode" not in payload:
        return False
    if "faultString" not in payload:
        return False
    if "boom" not in payload:
        return False
    if "42" not in payload:
        return False
    return True


def xmlrpc2_dumps():
    """dumps marshals a representative variety of values."""
    payload = dumps(
        (1, "hello", [1, 2, 3], {"k": "v"}, True, 3.5),
        methodname="ping",
    )
    checks = [
        "<methodCall>",
        "<methodName>ping</methodName>",
        "<int>1</int>",
        "<string>hello</string>",
        "<array>",
        "<struct>",
        "<name>k</name>",
        "<string>v</string>",
        "<boolean>1</boolean>",
        "<double>",
        "</methodCall>",
    ]
    for token in checks:
        if token not in payload:
            return False
    # response form
    resp = dumps((42,), methodresponse=True)
    if "<methodResponse>" not in resp:
        return False
    if "<int>42</int>" not in resp:
        return False
    # fault form
    fpayload = dumps(Fault(1, "x"))
    if "<fault>" not in fpayload:
        return False
    # bad input
    try:
        dumps("not a tuple")
    except TypeError:
        pass
    else:
        return False
    return True