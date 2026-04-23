"""
theseus_nntplib_cr — Clean-room nntplib module.
No import of the standard `nntplib` module.
"""

from collections import namedtuple as _namedtuple


class NNTPError(Exception):
    pass

class NNTPReplyError(NNTPError):
    pass

class NNTPTemporaryError(NNTPError):
    pass

class NNTPPermanentError(NNTPError):
    pass

class NNTPProtocolError(NNTPError):
    pass

class NNTPDataError(NNTPError):
    pass


GroupInfo = _namedtuple('GroupInfo', ['group', 'last', 'first', 'flag'])
ArticleInfo = _namedtuple('ArticleInfo', ['number', 'message_id', 'lines'])

NNTP_PORT = 119
NNTP_SSL_PORT = 563


class _NNTPBase:
    """Base class for NNTP client."""

    encoding = 'utf-8'
    errors = 'surrogateescape'

    def __init__(self, file, host, readermode=None, timeout=30):
        self.host = host
        self.file = file
        self.debugging = 0
        self._caps = None
        self.welcome = self._getresp()
        self._caps = None

    def getwelcome(self):
        return self.welcome

    def getcapabilities(self):
        if self._caps is None:
            try:
                resp, caps = self.capabilities()
            except (NNTPPermanentError, NNTPTemporaryError):
                self._caps = {}
            else:
                self._caps = caps
        return self._caps

    def set_debuglevel(self, level):
        self.debugging = level

    def _putline(self, line):
        if self.debugging > 1:
            print('*put*', repr(line))
        line += '\r\n'
        self.file.write(line.encode(self.encoding, self.errors))
        self.file.flush()

    def _putcmd(self, line):
        if self.debugging:
            print('*cmd*', repr(line))
        self._putline(line)

    def _getline(self, strip_crlf=True):
        line = self.file.readline()
        if not line:
            raise EOFError
        if self.debugging > 1:
            print('*get*', repr(line))
        if strip_crlf:
            if line[-2:] == b'\r\n':
                line = line[:-2]
            elif line[-1:] in (b'\r', b'\n'):
                line = line[:-1]
        return line.decode(self.encoding, self.errors)

    def _getresp(self):
        resp = self._getline()
        if self.debugging > 1:
            print('*resp*', repr(resp))
        c = resp[:1]
        if c == '4':
            raise NNTPTemporaryError(resp)
        if c == '5':
            raise NNTPPermanentError(resp)
        if c not in '123':
            raise NNTPProtocolError(resp)
        return resp

    def _getlongresp(self, file=None):
        resp = self._getresp()
        lines = []
        while True:
            line = self._getline()
            if line == '.':
                break
            if line[:2] == '..':
                line = line[1:]
            if file is not None:
                file.write(line + '\n')
            else:
                lines.append(line)
        return resp, lines

    def _shortcmd(self, string):
        self._putcmd(string)
        return self._getresp()

    def _longcmd(self, string, file=None):
        self._putcmd(string)
        return self._getlongresp(file)

    def newgroups(self, date, *, file=None):
        return self._longcmd('NEWGROUPS ' + date, file)

    def newnews(self, group, date, *, file=None):
        return self._longcmd('NEWNEWS ' + group + ' ' + date, file)

    def list(self, group_pattern=None, *, file=None):
        if group_pattern is not None:
            command = 'LIST ACTIVE ' + group_pattern
        else:
            command = 'LIST'
        resp, lines = self._longcmd(command, file)
        if file is not None:
            return resp, None
        groups = []
        for line in lines:
            parts = line.split()
            if len(parts) >= 4:
                groups.append(GroupInfo(parts[0], parts[1], parts[2], parts[3]))
        return resp, groups

    def group(self, name):
        resp = self._shortcmd('GROUP ' + name)
        if resp[:3] != '211':
            raise NNTPReplyError(resp)
        words = resp.split()
        count = int(words[1])
        first = int(words[2])
        last = int(words[3])
        group = words[4]
        return resp, count, first, last, group

    def help(self, *, file=None):
        return self._longcmd('HELP', file)

    def stat(self, message_spec=None):
        if message_spec:
            resp = self._shortcmd('STAT ' + str(message_spec))
        else:
            resp = self._shortcmd('STAT')
        if resp[:3] != '223':
            raise NNTPReplyError(resp)
        words = resp.split()
        art_num = int(words[1])
        message_id = words[2]
        return resp, art_num, message_id

    def next(self):
        resp = self._shortcmd('NEXT')
        return self._parse_overview(resp)

    def last(self):
        resp = self._shortcmd('LAST')
        return self._parse_overview(resp)

    def article(self, message_spec=None, *, file=None):
        cmd = 'ARTICLE'
        if message_spec is not None:
            cmd += ' ' + str(message_spec)
        resp, lines = self._longcmd(cmd, file)
        if resp[:3] != '220':
            raise NNTPReplyError(resp)
        words = resp.split()
        art_num = int(words[1])
        message_id = words[2]
        return resp, ArticleInfo(art_num, message_id, lines)

    def head(self, message_spec=None, *, file=None):
        cmd = 'HEAD'
        if message_spec is not None:
            cmd += ' ' + str(message_spec)
        resp, lines = self._longcmd(cmd, file)
        if resp[:3] != '221':
            raise NNTPReplyError(resp)
        words = resp.split()
        art_num = int(words[1])
        message_id = words[2]
        return resp, ArticleInfo(art_num, message_id, lines)

    def body(self, message_spec=None, *, file=None):
        cmd = 'BODY'
        if message_spec is not None:
            cmd += ' ' + str(message_spec)
        resp, lines = self._longcmd(cmd, file)
        if resp[:3] != '222':
            raise NNTPReplyError(resp)
        words = resp.split()
        art_num = int(words[1])
        message_id = words[2]
        return resp, ArticleInfo(art_num, message_id, lines)

    def post(self, data):
        resp = self._shortcmd('POST')
        if resp[:3] != '340':
            raise NNTPReplyError(resp)
        if hasattr(data, 'readline'):
            while True:
                line = data.readline()
                if not line:
                    break
                if isinstance(line, str):
                    line = line.encode(self.encoding, self.errors)
                if line.startswith(b'.'):
                    line = b'.' + line
                if not line.endswith(b'\r\n'):
                    if line.endswith(b'\n'):
                        line = line[:-1] + b'\r\n'
                    else:
                        line += b'\r\n'
                self.file.write(line)
        else:
            for line in data:
                if isinstance(line, str):
                    line = line.encode(self.encoding, self.errors)
                if line.startswith(b'.'):
                    line = b'.' + line
                if not line.endswith(b'\r\n'):
                    if line.endswith(b'\n'):
                        line = line[:-1] + b'\r\n'
                    else:
                        line += b'\r\n'
                self.file.write(line)
        self.file.write(b'.\r\n')
        self.file.flush()
        return self._getresp()

    def quit(self):
        resp = self._shortcmd('QUIT')
        self.file.close()
        return resp

    def _parse_overview(self, resp):
        words = resp.split()
        art_num = int(words[1])
        message_id = words[2]
        return resp, art_num, message_id

    def capabilities(self):
        resp, caps_list = self._longcmd('CAPABILITIES')
        caps = {}
        for cap_line in caps_list:
            name_field = cap_line.split()
            if name_field:
                caps[name_field[0]] = name_field[1:] if len(name_field) > 1 else []
        return resp, caps

    def over(self, message_spec, *, file=None):
        cmd = 'OVER'
        if message_spec is not None:
            if isinstance(message_spec, tuple):
                cmd += ' {}-{}'.format(*message_spec)
            else:
                cmd += ' ' + str(message_spec)
        return self._longcmd(cmd, file)


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def nntplib2_exceptions():
    """NNTP exception hierarchy exists; returns True."""
    return (issubclass(NNTPReplyError, NNTPError) and
            issubclass(NNTPTemporaryError, NNTPError) and
            issubclass(NNTPPermanentError, NNTPError) and
            issubclass(NNTPProtocolError, NNTPError) and
            issubclass(NNTPDataError, NNTPError))


def nntplib2_groupinfo():
    """GroupInfo namedtuple has expected fields; returns True."""
    g = GroupInfo('comp.lang.python', '1000', '1', 'y')
    return g.group == 'comp.lang.python' and g.flag == 'y'


def nntplib2_articleinfo():
    """ArticleInfo namedtuple has expected fields; returns True."""
    a = ArticleInfo(42, '<msg@server>', ['line1', 'line2'])
    return a.number == 42 and a.message_id == '<msg@server>' and len(a.lines) == 2


__all__ = [
    'NNTPError', 'NNTPReplyError', 'NNTPTemporaryError', 'NNTPPermanentError',
    'NNTPProtocolError', 'NNTPDataError',
    'GroupInfo', 'ArticleInfo', '_NNTPBase',
    'NNTP_PORT', 'NNTP_SSL_PORT',
    'nntplib2_exceptions', 'nntplib2_groupinfo', 'nntplib2_articleinfo',
]
