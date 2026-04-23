"""
theseus_ftplib_cr — Clean-room ftplib module.
No import of the standard `ftplib` module.
"""

import socket as _socket
import re as _re


class Error(Exception):
    pass

class error_reply(Error):
    pass

class error_temp(Error):
    pass

class error_perm(Error):
    pass

class error_proto(Error):
    pass

all_errors = (Error, OSError, EOFError)

FTP_PORT = 21
MAXLINE = 8192


class FTP:
    """FTP client class."""

    host = ''
    port = FTP_PORT
    sock = None
    file = None
    welcome = None
    passiveserver = True
    encoding = 'latin-1'
    timeout = _socket._GLOBAL_DEFAULT_TIMEOUT

    def __init__(self, host='', user='', passwd='', acct='', timeout=_socket._GLOBAL_DEFAULT_TIMEOUT, source_address=None):
        self.source_address = source_address
        self.timeout = timeout
        if host:
            self.connect(host)
            if user:
                self.login(user, passwd, acct)

    def connect(self, host='', port=0, timeout=-999, source_address=None):
        if host:
            self.host = host
        if port:
            self.port = port
        if timeout != -999:
            self.timeout = timeout
        if source_address is not None:
            self.source_address = source_address
        self.sock = _socket.create_connection((self.host, self.port), self.timeout, source_address=self.source_address)
        self.af = self.sock.family
        self.file = self.sock.makefile('r', encoding=self.encoding)
        self.welcome = self.getresp()
        return self.welcome

    def getwelcome(self):
        return self.welcome

    def set_debuglevel(self, level):
        pass

    def set_pasv(self, val):
        self.passiveserver = val

    def _putline(self, line):
        line = line + '\r\n'
        self.sock.sendall(line.encode(self.encoding))

    def putcmd(self, line):
        self._putline(line)

    def _getline(self):
        line = self.file.readline(MAXLINE + 1)
        if not line:
            raise EOFError
        if line[-2:] == '\r\n':
            line = line[:-2]
        elif line[-1:] in '\r\n':
            line = line[:-1]
        return line

    def getmultiline(self):
        line = self._getline()
        if line[3:4] == '-':
            code = line[:3]
            while True:
                nextline = self._getline()
                line = line + ('\n' + nextline)
                if nextline[:3] == code and nextline[3:4] != '-':
                    break
        return line

    def getresp(self):
        resp = self.getmultiline()
        c = resp[:1]
        if c in {'1', '2', '3'}:
            return resp
        if c == '4':
            raise error_temp(resp)
        if c == '5':
            raise error_perm(resp)
        raise error_proto(resp)

    def voidresp(self):
        resp = self.getresp()
        if resp[:1] != '2':
            raise error_reply(resp)
        return resp

    def sendcmd(self, cmd):
        self.putcmd(cmd)
        return self.getresp()

    def voidcmd(self, cmd):
        self.putcmd(cmd)
        return self.voidresp()

    def login(self, user='', passwd='', acct=''):
        if not user:
            user = 'anonymous'
        if not passwd:
            passwd = ''
        resp = self.sendcmd('USER ' + user)
        if resp[0] == '3':
            resp = self.sendcmd('PASS ' + passwd)
        if resp[0] == '3':
            resp = self.sendcmd('ACCT ' + acct)
        if resp[0] != '2':
            raise error_reply(resp)
        return resp

    def quit(self):
        resp = self.voidcmd('QUIT')
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

    def pwd(self):
        resp = self.sendcmd('PWD')
        return parse257(resp)

    def cwd(self, dirname):
        if dirname == '..':
            try:
                return self.voidcmd('CDUP')
            except error_perm:
                pass
        elif dirname == '':
            dirname = '.'
        return self.voidcmd('CWD ' + dirname)

    def nlst(self, *args):
        cmd = 'NLST'
        for arg in args:
            cmd = cmd + (' ' + arg)
        files = []
        self.retrlines(cmd, files.append)
        return files

    def dir(self, *args):
        cmd = 'LIST'
        func = None
        if args[-1:] and not isinstance(args[-1], str):
            args, func = args[:-1], args[-1]
        for arg in args:
            if arg:
                cmd = cmd + (' ' + arg)
        self.retrlines(cmd, func)

    def mlsd(self, path='', facts=[]):
        if facts:
            self.sendcmd('OPTS MLST ' + ';'.join(facts) + ';')
        if path:
            cmd = 'MLSD %s' % path
        else:
            cmd = 'MLSD'
        lines = []
        self.retrlines(cmd, lines.append)
        for line in lines:
            facts_found, _, name = line.rstrip().partition(' ')
            entry = {}
            for fact in facts_found[:-1].split(';'):
                key, _, value = fact.partition('=')
                entry[key.lower()] = value
            yield entry, name

    def size(self, filename):
        resp = self.sendcmd('SIZE ' + filename)
        if resp[:3] == '213':
            s = resp[3:].strip()
            return int(s)

    def mkd(self, dirname):
        resp = self.voidcmd('MKD ' + dirname)
        return parse257(resp)

    def rmd(self, dirname):
        return self.voidcmd('RMD ' + dirname)

    def delete(self, filename):
        resp = self.sendcmd('DELE ' + filename)
        if resp[:3] in {'250', '200'}:
            return resp
        raise error_reply(resp)

    def rename(self, fromname, toname):
        resp = self.sendcmd('RNFR ' + fromname)
        if resp[0] != '3':
            raise error_reply(resp)
        return self.voidcmd('RNTO ' + toname)

    def retrlines(self, cmd, callback=None):
        if callback is None:
            callback = print
        resp = self.sendcmd(cmd)
        if resp[0] not in {'1', '2'}:
            raise error_reply(resp)
        return resp

    def retrbinary(self, cmd, callback, blocksize=8192, rest=None):
        self.voidcmd('TYPE I')
        conn = self.transfercmd(cmd, rest)
        try:
            while True:
                data = conn.recv(blocksize)
                if not data:
                    break
                callback(data)
            conn.close()
        except:
            conn.close()
            raise
        return self.voidresp()

    def storbinary(self, cmd, fp, blocksize=8192, callback=None, rest=None):
        self.voidcmd('TYPE I')
        conn = self.transfercmd(cmd, rest)
        try:
            while True:
                buf = fp.read(blocksize)
                if not buf:
                    break
                conn.sendall(buf)
                if callback:
                    callback(buf)
            conn.close()
        except:
            conn.close()
            raise
        return self.voidresp()

    def transfercmd(self, cmd, rest=None):
        if self.passiveserver:
            host, port = self.makepasv()
            conn = _socket.create_connection((host, port), self.timeout)
            try:
                if rest is not None:
                    self.sendcmd('REST %s' % rest)
                resp = self.sendcmd(cmd)
                if resp[0] == '2':
                    resp = self.getresp()
                if resp[0] != '1':
                    raise error_reply(resp)
            except:
                conn.close()
                raise
        else:
            sock = self.makeport()
            if rest is not None:
                self.sendcmd('REST %s' % rest)
            resp = self.sendcmd(cmd)
            if resp[0] == '2':
                resp = self.getresp()
            if resp[0] != '1':
                raise error_reply(resp)
            conn, _ = sock.accept()
            sock.close()
        return conn

    def makepasv(self):
        if self.af == _socket.AF_INET:
            host, port = parse227(self.sendcmd('PASV'))
        else:
            host, port = parse229(self.sendcmd('EPSV'), self.sock.getpeername())
        return host, port

    def makeport(self):
        err = None
        sock = None
        for res in _socket.getaddrinfo(None, 0, self.af, _socket.SOCK_STREAM, 0, _socket.AI_PASSIVE):
            af, socktype, proto, canonname, sa = res
            try:
                sock = _socket.socket(af, socktype, proto)
                sock.bind(sa)
                sock.listen(1)
                break
            except _socket.error as e:
                err = e
                if sock:
                    sock.close()
        if sock is None:
            raise err
        port = sock.getsockname()[1]
        host = self.sock.getsockname()[0]
        resp = self.sendcmd('PORT %s,%d,%d' % (host.replace('.', ','), port >> 8, port & 0xff))
        return sock


def parse227(resp):
    """Parse the response from PASV command."""
    if resp[:3] != '227':
        raise error_reply(resp)
    m = _re.search(r'(\d+),(\d+),(\d+),(\d+),(\d+),(\d+)', resp)
    if not m:
        raise error_proto(resp)
    numbers = m.groups()
    host = '.'.join(numbers[:4])
    port = (int(numbers[4]) << 8) + int(numbers[5])
    return host, port


def parse229(resp, peer):
    """Parse response from EPSV."""
    if resp[:3] != '229':
        raise error_reply(resp)
    m = _re.search(r'\((.)\1\1(\d+)\1\)', resp)
    if not m:
        raise error_proto(resp)
    host = peer[0]
    port = int(m.group(2))
    return host, port


def parse257(resp):
    """Parse the response from PWD/MKD command."""
    if resp[:3] not in {'257', '200'}:
        raise error_reply(resp)
    if resp[3:4] != ' ':
        return ''
    if resp[4:5] != '"':
        return resp[4:]
    dirname = ''
    i = 5
    n = len(resp)
    while i < n:
        c = resp[i]
        i += 1
        if c == '"':
            if i >= n or resp[i] != '"':
                break
            i += 1
        dirname += c
    return dirname


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def ftplib2_exceptions():
    """ftplib exception classes exist and inherit from Error; returns True."""
    return (issubclass(error_reply, Error) and
            issubclass(error_temp, Error) and
            issubclass(error_perm, Error) and
            issubclass(error_proto, Error))


def ftplib2_parse227():
    """PASV response parser returns host and port; returns True."""
    host, port = parse227('227 Entering Passive Mode (192,168,1,1,10,20).')
    return host == '192.168.1.1' and port == 10 * 256 + 20


def ftplib2_parse257():
    """PWD response parser returns directory path; returns True."""
    path = parse257('257 "/home/user" is current directory')
    return path == '/home/user'


__all__ = [
    'FTP', 'Error', 'error_reply', 'error_temp', 'error_perm', 'error_proto',
    'all_errors', 'FTP_PORT', 'parse227', 'parse229', 'parse257',
    'ftplib2_exceptions', 'ftplib2_parse227', 'ftplib2_parse257',
]
