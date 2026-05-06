"""
theseus_email_utils_cr — Clean-room reimplementation of selected
``email.utils`` helpers.

This module does NOT import ``email.utils`` (or any wrapper around it).
Only Python standard-library primitives (re, time, calendar, random,
socket, datetime) are used.

Required exports for the Theseus invariant suite:
    * emailutils2_parseaddr
    * emailutils2_formataddr
    * emailutils2_mktime_tz
"""

import re as _re
import time as _time
import calendar as _calendar
import random as _random


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

COMMASPACE = ', '
EMPTYSTRING = ''
UEMPTYSTRING = ''

_MONTHS = {
    'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
    'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12,
}

_MONTHNAMES = [None, 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
               'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

_DAYNAMES = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

# Characters in a display-name that force quoting per RFC 5322 specials.
_SPECIALS = '()<>[]:;@\\,."'


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _strip_outer_quotes(name):
    """Strip a single matching pair of surrounding double quotes."""
    if len(name) >= 2 and name[0] == '"' and name[-1] == '"':
        return name[1:-1]
    return name


def _unescape(s):
    """Process backslash escapes inside a quoted string."""
    out = []
    i = 0
    n = len(s)
    while i < n:
        c = s[i]
        if c == '\\' and i + 1 < n:
            out.append(s[i + 1])
            i += 2
        else:
            out.append(c)
            i += 1
    return ''.join(out)


# ---------------------------------------------------------------------------
# Address parsing / formatting
# ---------------------------------------------------------------------------

def parseaddr(addr):
    """Parse an address into a ``(realname, email_address)`` tuple.

    Accepts a single string or an iterable of strings (joined with
    spaces — matching the stdlib semantics). Returns ``('', '')`` when
    the input is empty or unparseable.
    """
    if addr is None:
        return ('', '')

    if isinstance(addr, (list, tuple)):
        if len(addr) == 0:
            return ('', '')
        if len(addr) == 1:
            addr = addr[0]
        else:
            try:
                addr = ' '.join(str(x) for x in addr)
            except Exception:
                return ('', '')

    if not isinstance(addr, str):
        return ('', '')

    s = addr.strip()
    if not s:
        return ('', '')

    # Form 1: optional display name followed by <addr-spec>
    lt = s.rfind('<')
    gt = s.rfind('>')
    if lt != -1 and gt != -1 and gt > lt:
        email_part = s[lt + 1:gt].strip()
        name_part = s[:lt].strip()
        name_part = _unescape(_strip_outer_quotes(name_part))
        return (name_part, email_part)

    # Form 2: addr-spec with parenthesized comment as display name
    lp = s.find('(')
    rp = s.rfind(')')
    if lp != -1 and rp != -1 and rp > lp:
        before = s[:lp].strip()
        after = s[rp + 1:].strip()
        email_part = (before + ' ' + after).strip()
        name_part = s[lp + 1:rp].strip()
        return (name_part, email_part)

    # Form 3: bare addr-spec
    return ('', s)


def formataddr(pair, charset='utf-8'):
    """Format a ``(realname, email_address)`` pair as a header value.

    Quotes the display name when it contains RFC 5322 specials and
    backslash-escapes embedded quotes/backslashes. ``charset`` is accepted
    for API compatibility; non-ASCII names are returned as-is.
    """
    if pair is None:
        return ''
    try:
        name, address = pair
    except (TypeError, ValueError):
        return ''

    name = '' if name is None else str(name)
    address = '' if address is None else str(address)

    if name:
        needs_quote = any(ch in _SPECIALS for ch in name)
        if needs_quote:
            escaped = name.replace('\\', '\\\\').replace('"', '\\"')
            return '"%s" <%s>' % (escaped, address)
        return '%s <%s>' % (name, address)
    return address


def getaddresses(fieldvalues):
    """Parse multiple addresses from a list of header field values."""
    if not fieldvalues:
        return []
    joined = COMMASPACE.join(fieldvalues)
    out = []
    for piece in joined.split(','):
        piece = piece.strip()
        if piece:
            out.append(parseaddr(piece))
    return out


# ---------------------------------------------------------------------------
# Date parsing / formatting
# ---------------------------------------------------------------------------

def _parse_tz(tz_str):
    """Parse an RFC 2822 timezone field into seconds east of UTC."""
    if not tz_str:
        return None
    tz_str = tz_str.strip()
    if tz_str in ('UT', 'UTC', 'GMT', 'Z'):
        return 0
    m = _re.match(r'^([+-])(\d{2})(\d{2})$', tz_str)
    if m:
        sign = 1 if m.group(1) == '+' else -1
        hours = int(m.group(2))
        minutes = int(m.group(3))
        return sign * (hours * 3600 + minutes * 60)
    # Common military / US zones
    named = {
        'EST': -5 * 3600, 'EDT': -4 * 3600,
        'CST': -6 * 3600, 'CDT': -5 * 3600,
        'MST': -7 * 3600, 'MDT': -6 * 3600,
        'PST': -8 * 3600, 'PDT': -7 * 3600,
    }
    return named.get(tz_str.upper())


def _parse_date_components(date):
    if not date:
        return None
    date = date.strip()
    m = _re.match(r'^[A-Za-z]+,\s*', date)
    if m:
        date = date[m.end():]
    m = _re.match(
        r'^(\d{1,2})\s+([A-Za-z]+)\s+(\d{2,4})\s+'
        r'(\d{2}):(\d{2})(?::(\d{2}))?'
        r'(?:\s+([+-]\d{4}|[A-Za-z]+))?\s*$',
        date,
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
    tz = _parse_tz(m.group(7) or '')
    return (year, mon, day, hour, minute, second, tz)


def parsedate(date):
    """Parse an RFC 2822 date string into a 9-tuple (no timezone)."""
    parts = _parse_date_components(date)
    if not parts:
        return None
    y, mo, d, h, mi, s, _tz = parts
    return (y, mo, d, h, mi, s, 0, 1, -1)


def parsedate_tz(date):
    """Parse an RFC 2822 date string into a 10-tuple including tz offset."""
    parts = _parse_date_components(date)
    if not parts:
        return None
    y, mo, d, h, mi, s, tz = parts
    return (y, mo, d, h, mi, s, 0, 1, -1, tz)


def mktime_tz(data):
    """Turn a 10-tuple (as returned by ``parsedate_tz``) into a UTC timestamp.

    The 10-tuple format is::
        (year, month, day, hour, minute, second,
         weekday, yearday, isdst, tz_offset_seconds)

    If ``tz_offset_seconds`` is ``None`` the time is treated as local
    time and converted via :func:`time.mktime`; otherwise the tuple is
    treated as wall clock at the given offset and converted to UTC by
    subtracting that offset from the corresponding UTC epoch seconds.
    """
    if data is None:
        raise TypeError("mktime_tz requires a 10-tuple, got None")
    if len(data) < 10:
        raise TypeError("mktime_tz requires a 10-tuple")

    tz_offset = data[9]
    nine = (data[0], data[1], data[2], data[3], data[4], data[5],
            data[6], data[7], data[8])

    if tz_offset is None:
        local_nine = (nine[0], nine[1], nine[2], nine[3], nine[4], nine[5],
                      nine[6], nine[7], -1)
        return _time.mktime(local_nine)

    return _calendar.timegm(nine) - tz_offset


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
    """Format a :class:`datetime.datetime` into an RFC 2822 string."""
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
    """Return local time as an aware :class:`datetime.datetime`."""
    import datetime as _datetime
    if dt is None:
        return _datetime.datetime.now(_datetime.timezone.utc).astimezone()
    return dt


def make_msgid(idstring=None, domain=None):
    """Return a string suitable for an RFC 2822 ``Message-ID`` header."""
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
    return '<%s.%05d.%05d%s@%s>' % (utcdate, pid, randint, idstring, domain)


# ---------------------------------------------------------------------------
# RFC 2231 helpers
# ---------------------------------------------------------------------------

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
    """Remove surrounding quotes/angle brackets from a header value."""
    if len(s) > 1:
        if s.startswith('"') and s.endswith('"'):
            return s[1:-1].replace('\\\\', '\\').replace('\\"', '"')
        if s.startswith('<') and s.endswith('>'):
            return s[1:-1]
    return s


def quote(s):
    """Quote backslashes and double quotes for use inside an RFC 2822 quoted-string."""
    return s.replace('\\', '\\\\').replace('"', '\\"')


# ---------------------------------------------------------------------------
# Invariant functions (probed by the Theseus test harness)
# ---------------------------------------------------------------------------

def emailutils2_parseaddr():
    """parseaddr() correctly parses ``Name <addr>`` form."""
    name, addr = parseaddr('John Doe <john@example.com>')
    if not (name == 'John Doe' and addr == 'john@example.com'):
        return False
    # Bare address
    n2, a2 = parseaddr('alice@example.org')
    if not (n2 == '' and a2 == 'alice@example.org'):
        return False
    # Empty input
    if parseaddr('') != ('', ''):
        return False
    return True


def emailutils2_formataddr():
    """formataddr() correctly formats a (name, addr) pair."""
    result = formataddr(('John Doe', 'john@example.com'))
    if 'john@example.com' not in result or 'John Doe' not in result:
        return False
    # Bare address (no name) returns just the address.
    if formataddr(('', 'a@b.com')) != 'a@b.com':
        return False
    # Special characters force quoting.
    quoted = formataddr(('Doe, John', 'jd@example.com'))
    if not quoted.startswith('"') or 'jd@example.com' not in quoted:
        return False
    return True


def emailutils2_mktime_tz():
    """mktime_tz() converts a 10-tuple to a numeric POSIX timestamp."""
    # 2000-01-01 00:00:00 UTC
    data = (2000, 1, 1, 0, 0, 0, 5, 1, -1, 0)
    ts = mktime_tz(data)
    if not isinstance(ts, (int, float)) or ts <= 0:
        return False
    # tz offset must shift the result.
    data2 = (2000, 1, 1, 0, 0, 0, 5, 1, -1, 3600)
    ts2 = mktime_tz(data2)
    if abs((ts - ts2) - 3600) > 1e-6:
        return False
    return True


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