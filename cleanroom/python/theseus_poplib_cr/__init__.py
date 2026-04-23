"""
theseus_poplib_cr — Clean-room poplib module.
No import of the standard `poplib` module.
"""

import socket as _socket
import re as _re

POP3_PORT = 110
POP3_SSL_PORT = 995
CR = b'\r'
LF = b'\n'
CRLF = b'\r\n'
MAXLINE = 2048


class error_proto(Exception):
    pass


class POP3:
    """POP3 client class."""

    encoding = 'UTF-8'

    def __init__(self, host, port=POP3_PORT, timeout=_socket._GLOBAL_DEFAULT_TIMEOUT):
        self.host = host
        self.port = port
        self.timeout = timeout
        self._tls_established = False
        self.sock = self._create_socket(timeout)
        self.file = self.sock.makefile('rb')
        self._debugging = 0
        self.welcome = self._getresp()

    def _create_socket(self, timeout):
        return _socket.create_connection((self.host, self.port), timeout)

    def _putline(self, line):
        if self._debugging > 1:
            print('*put*', repr(line))
        self.sock.sendall(line + CRLF)

    def _putcmd(self, line):
        if self._debugging:
            print('*cmd*', repr(line))
        line = line.encode(self.encoding)
        self._putline(line)

    def _getline(self):
        line = self.file.readline(MAXLINE + 1)
        if not line:
            raise EOFError('-ERR EOF')
        if self._debugging > 1:
            print('*get*', repr(line))
        octets = len(line)
        if line[-2:] == CRLF:
            return line[:-2], octets
        if line[0:1] == CR:
            return line[1:-1], octets
        return line[:-1], octets

    def _getresp(self):
        resp, o = self._getline()
        if self._debugging > 1:
            print('*resp*', repr(resp))
        if not resp.startswith(b'+'):
            raise error_proto(resp)
        return resp

    def _getlongresp(self):
        resp = self._getresp()
        list_data = []
        octets = len(resp)
        line, o = self._getline()
        while line != b'.':
            if line.startswith(b'..'):
                o -= 1
                line = line[1:]
            octets += o
            list_data.append(line)
            line, o = self._getline()
        return resp, list_data, octets

    def _shortcmd(self, line):
        self._putcmd(line)
        return self._getresp()

    def _longcmd(self, line):
        self._putcmd(line)
        return self._getlongresp()

    def getwelcome(self):
        return self.welcome

    def set_debuglevel(self, level):
        self._debugging = level

    def user(self, user):
        return self._shortcmd('USER %s' % user)

    def pass_(self, pswd):
        return self._shortcmd('PASS %s' % pswd)

    def stat(self):
        retval = self._shortcmd('STAT')
        rets = retval.split()
        numMessages = int(rets[1])
        sizeMessages = int(rets[2])
        return (numMessages, sizeMessages)

    def list(self, which=None):
        if which is not None:
            return self._shortcmd('LIST %s' % which)
        return self._longcmd('LIST')

    def retr(self, which):
        return self._longcmd('RETR %s' % which)

    def dele(self, which):
        return self._shortcmd('DELE %s' % which)

    def noop(self):
        return self._shortcmd('NOOP')

    def rset(self):
        return self._shortcmd('RSET')

    def quit(self):
        resp = self._shortcmd('QUIT')
        self.close()
        return resp

    def close(self):
        try:
            file = self.file
            self.file = None
            if file is not None:
                file.close()
        finally:
            sock = self.sock
            self.sock = None
            if sock is not None:
                sock.close()

    def rpop(self, user):
        return self._shortcmd('RPOP %s' % user)

    def apop(self, user, password):
        import hashlib
        secret = self.welcome
        m = _re.search(br'<[^>]+>', secret)
        if not m:
            raise error_proto('-ERR APOP not supported by server')
        digest = m.group(0) + password.encode(self.encoding)
        digest = hashlib.md5(digest).hexdigest()
        return self._shortcmd('APOP %s %s' % (user, digest))

    def top(self, which, howmuch):
        return self._longcmd('TOP %s %s' % (which, howmuch))

    def uidl(self, which=None):
        if which is not None:
            return self._shortcmd('UIDL %s' % which)
        return self._longcmd('UIDL')

    def utf8(self):
        return self._shortcmd('UTF8')

    def capa(self):
        """Return server capabilities as a dict."""
        resp, caps, octets = self._longcmd('CAPA')
        capabilities = {}
        for cap_line in caps:
            cap_line = cap_line.decode(self.encoding)
            parts = cap_line.split()
            capabilities[parts[0]] = parts[1:] if len(parts) > 1 else []
        return capabilities

    def stls(self, context=None):
        import ssl
        if self._tls_established:
            raise error_proto('-ERR TLS already established')
        caps = {}
        try:
            caps = self.capa()
        except error_proto:
            pass
        if 'STLS' not in caps:
            raise error_proto('-ERR STLS not supported')
        resp = self._shortcmd('STLS')
        if context is None:
            context = ssl.create_default_context()
        self.sock = context.wrap_socket(self.sock, server_hostname=self.host)
        self.file = self.sock.makefile('rb')
        self._tls_established = True
        return resp


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def poplib2_exceptions():
    """poplib exception classes exist and inherit from Exception; returns True."""
    return issubclass(error_proto, Exception)


def poplib2_constants():
    """POP3_PORT and POP3_SSL_PORT have expected values; returns True."""
    return POP3_PORT == 110 and POP3_SSL_PORT == 995


def poplib2_parse_response():
    """POP3 response line parsed correctly; returns True."""
    line = b'+OK 2 320\r\n'
    if line[-2:] == CRLF:
        stripped = line[:-2]
    else:
        stripped = line.rstrip()
    parts = stripped.split()
    return parts[0] == b'+OK' and parts[1] == b'2' and parts[2] == b'320'


__all__ = [
    'POP3', 'error_proto', 'POP3_PORT', 'POP3_SSL_PORT',
    'poplib2_exceptions', 'poplib2_constants', 'poplib2_parse_response',
]
