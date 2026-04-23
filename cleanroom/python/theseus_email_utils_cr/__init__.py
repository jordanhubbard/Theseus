"""
theseus_email_utils_cr — Clean-room email.utils module.
No import of the standard `email.utils` module.
"""

import re as _re
import time as _time
import calendar as _calendar
import random as _random

_MONTHS = {
    'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
    'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
}

_MONTHNAMES = [None, 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
               'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

_DAYNAMES = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

COMMASPACE = ', '
EMPTYSTRING = ''
UEMPTYSTRING = ''

# RFC 2822 address patterns
_addr_spec_re = _re.compile(r'''
    \s*                    # leading whitespace
    (?P<name>              # optional display name
        "(?:[^"\\]|\\.)*"  # double-quoted string
        |
        [^<,@]*            # unquoted name
    )?
    \s*
    (?:
        <(?P<addr>[^>]*)>  # angle-bracket address
        |
        (?P<bare_addr>[^\s,]+)  # bare address
    )
    \s*
''', _re.VERBOSE)


def parseaddr(addr):
    """Parse an address into a (name, address) tuple."""
    if not addr:
        return ('', '')
    addr = addr.strip()
    # Try angle bracket format first
    m = _re.match(r'^(.*?)\s*<([^>]*)>\s*$', addr)
    if m:
        name = m.group(1).strip().strip('"')
        address = m.group(2).strip()
        return (name, address)
    # Check if it's just an email address
    if '@' in addr:
        return ('', addr)
    return ('', addr)


def formataddr(pair, charset='utf-8'):
    """Format a (name, address) pair into a string."""
    name, address = pair
    if name:
        # Quote the name if it contains special characters
        if _re.search(r'[^\w\s.\-]', name):
            name = '"' + name.replace('\\', '\\\\').replace('"', '\\"') + '"'
        return '%s <%s>' % (name, address)
    return address


def getaddresses(fieldvalues):
    """Parse multiple addresses from header field values."""
    all_addresses = COMMASPACE.join(fieldvalues)
    addresses = []
    for addr in all_addresses.split(','):
        addr = addr.strip()
        if addr:
            addresses.append(parseaddr(addr))
    return addresses


def parsedate(date):
    """Parse a date as specified by RFC 2822."""
    if not date:
        return None
    date = date.strip()
    # Remove day of week if present
    m = _re.match(r'^[A-Za-z]+,\s*', date)
    if m:
        date = date[m.end():]
    # Parse: DD Mon YYYY HH:MM:SS [TZ]
    m = _re.match(
        r'^(\d{1,2})\s+([A-Za-z]+)\s+(\d{2,4})\s+'
        r'(\d{2}):(\d{2})(?::(\d{2}))?'
        r'(?:\s+(.+))?$',
        date
    )
    if not m:
        return None
    day = int(m.group(1))
    mon = _MONTHS.get(m.group(2).lower(), 0)
    year = int(m.group(3))
    if year < 100:
        year += 1900 if year >= 70 else 2000
    hour = int(m.group(4))
    minute = int(m.group(5))
    second = int(m.group(6)) if m.group(6) else 0
    return (year, mon, day, hour, minute, second, 0, 1, -1)


def parsedate_tz(date):
    """Parse a date with timezone as specified by RFC 2822."""
    if not date:
        return None
    date = date.strip()
    # Remove day of week if present
    m = _re.match(r'^[A-Za-z]+,\s*', date)
    if m:
        date = date[m.end():]
    m = _re.match(
        r'^(\d{1,2})\s+([A-Za-z]+)\s+(\d{2,4})\s+'
        r'(\d{2}):(\d{2})(?::(\d{2}))?'
        r'(?:\s+([+-]\d{4}|[A-Z]+))?$',
        date
    )
    if not m:
        return None
    day = int(m.group(1))
    mon = _MONTHS.get(m.group(2).lower(), 0)
    year = int(m.group(3))
    if year < 100:
        year += 1900 if year >= 70 else 2000
    hour = int(m.group(4))
    minute = int(m.group(5))
    second = int(m.group(6)) if m.group(6) else 0
    tz_str = m.group(7) or ''
    tz = _parse_tz(tz_str)
    return (year, mon, day, hour, minute, second, 0, 1, -1, tz)


def _parse_tz(tz_str):
    if not tz_str:
        return None
    tz_str = tz_str.strip()
    if tz_str in ('UT', 'UTC', 'GMT'):
        return 0
    m = _re.match(r'^([+-])(\d{2})(\d{2})$', tz_str)
    if m:
        sign = 1 if m.group(1) == '+' else -1
        hours = int(m.group(2))
        minutes = int(m.group(3))
        return sign * (hours * 3600 + minutes * 60)
    return None


def mktime_tz(data):
    """Turn a 10-tuple as returned by parsedate_tz() into a POSIX timestamp."""
    if data[9] is None:
        return _time.mktime(data[:9])
    t = _calendar.timegm(data[:9])
    return t - data[9]


def formatdate(timeval=None, localtime=False, usegmt=False):
    """Return a date string as specified by RFC 2822."""
    if timeval is None:
        timeval = _time.time()
    if localtime or usegmt:
        now = _time.localtime(timeval)
        if usegmt:
            tz_str = 'GMT'
        else:
            offset = -_time.timezone
            sign = '+' if offset >= 0 else '-'
            h, m = divmod(abs(offset) // 60, 60)
            tz_str = '%s%02d%02d' % (sign, h, m)
    else:
        now = _time.gmtime(timeval)
        tz_str = '-0000'
    return '%s, %02d %s %04d %02d:%02d:%02d %s' % (
        _DAYNAMES[now.tm_wday],
        now.tm_mday,
        _MONTHNAMES[now.tm_mon],
        now.tm_year,
        now.tm_hour,
        now.tm_min,
        now.tm_sec,
        tz_str,
    )


def format_datetime(dt, usegmt=False):
    """Format a datetime.datetime into an RFC 2822 string."""
    dow = _DAYNAMES[dt.weekday()]
    mon = _MONTHNAMES[dt.month]
    if usegmt:
        tz_str = 'GMT'
    elif dt.tzinfo is None:
        tz_str = '-0000'
    else:
        offset = dt.utcoffset()
        total_seconds = int(offset.total_seconds())
        sign = '+' if total_seconds >= 0 else '-'
        h, m = divmod(abs(total_seconds) // 60, 60)
        tz_str = '%s%02d%02d' % (sign, h, m)
    return '%s, %02d %s %04d %02d:%02d:%02d %s' % (
        dow, dt.day, mon, dt.year, dt.hour, dt.minute, dt.second, tz_str
    )


def localtime(dt=None, isdst=-1):
    """Return local time as an aware datetime object."""
    import datetime as _datetime
    if dt is None:
        return _datetime.datetime.now(_datetime.timezone.utc).astimezone()
    return dt


def make_msgid(idstring=None, domain=None):
    """Return a string suitable for RFC 2822 compliant Message-ID."""
    timeval = _time.time()
    utcdate = _time.strftime('%Y%m%d%H%M%S', _time.gmtime(timeval))
    pid = _random.randint(1, 99999)
    randint = _random.randint(1, 99999)
    if idstring is None:
        idstring = ''
    else:
        idstring = '.' + idstring
    if domain is None:
        import socket as _socket
        domain = _socket.getfqdn()
    msgid = '<%s.%05d.%05d%s@%s>' % (utcdate, pid, randint, idstring, domain)
    return msgid


def collapse_rfc2231_value(value, errors='replace', fallback_charset='us-ascii'):
    """Collapse a header value from RFC 2231 encoding."""
    if isinstance(value, tuple):
        rawval = value[2]
        charset = value[0] or fallback_charset
        try:
            return rawval.encode('raw-unicode-escape').decode(charset, errors=errors)
        except (LookupError, UnicodeDecodeError):
            return rawval
    return value


def decode_rfc2231(s):
    """Decode a string according to RFC 2231."""
    parts = s.split("'", 2)
    if len(parts) < 3:
        return None, None, s
    charset, language, value = parts
    return charset, language, value


def encode_rfc2231(s, charset=None, language=None):
    """Encode a string according to RFC 2231."""
    s = _re.sub(r'[^\w\-.!~*\'()]', lambda m: '%%%02X' % ord(m.group(0)), s)
    if charset is not None or language is not None:
        s = "%s'%s'%s" % (charset or '', language or '', s)
    return s


def unquote(s):
    """Remove quotes from a string."""
    if len(s) > 1:
        if s.startswith('"') and s.endswith('"'):
            return s[1:-1].replace('\\\\', '\\').replace('\\"', '"')
        if s.startswith('<') and s.endswith('>'):
            return s[1:-1]
    return s


def quote(s):
    """Quote a string of header characters."""
    return s.replace('\\', '\\\\').replace('"', '\\"')


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def emailutils2_parseaddr():
    """parseaddr() parses 'Name <addr>' format; returns True."""
    name, addr = parseaddr('John Doe <john@example.com>')
    return name == 'John Doe' and addr == 'john@example.com'


def emailutils2_formataddr():
    """formataddr() formats (name, addr) tuple; returns True."""
    result = formataddr(('John Doe', 'john@example.com'))
    return 'John Doe' in result and 'john@example.com' in result


def emailutils2_mktime_tz():
    """mktime_tz() converts tuple to timestamp; returns True."""
    # (year, mon, day, hour, min, sec, weekday, julianday, dst, tz_offset)
    data = (2000, 1, 1, 0, 0, 0, 5, 1, -1, 0)
    ts = mktime_tz(data)
    return isinstance(ts, (int, float)) and ts > 0


__all__ = [
    'COMMASPACE', 'EMPTYSTRING', 'UEMPTYSTRING',
    'parseaddr', 'formataddr', 'getaddresses',
    'parsedate', 'parsedate_tz', 'mktime_tz',
    'formatdate', 'format_datetime', 'localtime',
    'make_msgid', 'collapse_rfc2231_value',
    'decode_rfc2231', 'encode_rfc2231',
    'unquote', 'quote',
    'emailutils2_parseaddr', 'emailutils2_formataddr', 'emailutils2_mktime_tz',
]
