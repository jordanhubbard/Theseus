"""Clean-room reimplementation of a subset of ftplib.

Implements the FTP client class and helpers for parsing PASV (227) and
MKD/PWD (257) replies.  No imports from the original ftplib module.
"""

import socket
import re


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FTP_PORT = 21
MSG_OOB = 0x1
MAXLINE = 8192
CRLF = "\r\n"
B_CRLF = b"\r\n"
_GLOBAL_DEFAULT_TIMEOUT = object()


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class Error(Exception):
    """Base class for all FTP-related errors."""
    pass


class error_reply(Error):
    """Unexpected [123]xx reply from server."""
    pass


class error_temp(Error):
    """4xx errors: transient failures."""
    pass


class error_perm(Error):
    """5xx errors: permanent failures."""
    pass


class error_proto(Error):
    """Response that does not begin with a valid digit (1-5)."""
    pass


all_errors = (Error, OSError, EOFError)


# ---------------------------------------------------------------------------
# FTP client
# ---------------------------------------------------------------------------

class FTP:
    """Minimal clean-room FTP client.

    Supports: connect, login, quit, nlst, retrbinary, storbinary.
    """

    debugging = 0
    host = ""
    port = FTP_PORT
    maxline = MAXLINE
    sock = None
    file = None
    welcome = None
    passiveserver = 1
    encoding = "latin-1"
    timeout = _GLOBAL_DEFAULT_TIMEOUT

    def __init__(self, host="", user="", passwd="", acct="",
                 timeout=_GLOBAL_DEFAULT_TIMEOUT, source_address=None,
                 *, encoding="utf-8"):
        self.encoding = encoding
        self.source_address = source_address
        self.timeout = timeout
        if host:
            self.connect(host)
            if user:
                self.login(user, passwd, acct)

    # ----- low-level connection -----

    def connect(self, host="", port=0, timeout=-999, source_address=None):
        if host != "":
            self.host = host
        if port > 0:
            self.port = port
        if timeout != -999:
            self.timeout = timeout
        if self.timeout is not None and not self.timeout:
            raise ValueError("Non-blocking socket (timeout=0) is not supported")
        if source_address is not None:
            self.source_address = source_address
        sys_default = socket.getdefaulttimeout()
        timeout_arg = (sys_default if self.timeout is _GLOBAL_DEFAULT_TIMEOUT
                       else self.timeout)
        self.sock = socket.create_connection(
            (self.host, self.port),
            timeout_arg if timeout_arg is not None else socket._GLOBAL_DEFAULT_TIMEOUT,
            source_address=self.source_address,
        )
        self.af = self.sock.family
        self.file = self.sock.makefile("r", encoding=self.encoding)
        self.welcome = self.getresp()
        return self.welcome

    def getwelcome(self):
        if self.debugging:
            print("*welcome*", self.sanitize(self.welcome))
        return self.welcome

    def set_debuglevel(self, level):
        self.debugging = level

    debug = set_debuglevel

    def set_pasv(self, val):
        self.passiveserver = val

    @staticmethod
    def sanitize(s):
        if s[:5] in {"pass ", "PASS "}:
            i = len(s.rstrip("\r\n"))
            s = s[:5] + "*" * (i - 5) + s[i:]
        return repr(s)

    # ----- raw send / recv -----

    def putline(self, line):
        if "\r" in line or "\n" in line:
            raise ValueError("an illegal newline character should not be contained")
        line = line + CRLF
        if self.debugging > 1:
            print("*put*", self.sanitize(line))
        self.sock.sendall(line.encode(self.encoding))

    def putcmd(self, line):
        if self.debugging:
            print("*cmd*", self.sanitize(line))
        self.putline(line)

    def getline(self):
        line = self.file.readline(self.maxline + 1)
        if len(line) > self.maxline:
            raise Error("got more than %d bytes" % self.maxline)
        if self.debugging > 1:
            print("*get*", self.sanitize(line))
        if not line:
            raise EOFError
        if line[-2:] == CRLF:
            line = line[:-2]
        elif line[-1:] in CRLF:
            line = line[:-1]
        return line

    def getmultiline(self):
        line = self.getline()
        if line[3:4] == "-":
            code = line[:3]
            while True:
                nextline = self.getline()
                line = line + ("\n" + nextline)
                if nextline[:3] == code and nextline[3:4] != "-":
                    break
        return line

    def getresp(self):
        resp = self.getmultiline()
        if self.debugging:
            print("*resp*", self.sanitize(resp))
        self.lastresp = resp[:3]
        c = resp[:1]
        if c in {"1", "2", "3"}:
            return resp
        if c == "4":
            raise error_temp(resp)
        if c == "5":
            raise error_perm(resp)
        raise error_proto(resp)

    def voidresp(self):
        resp = self.getresp()
        if resp[:1] != "2":
            raise error_reply(resp)
        return resp

    def sendcmd(self, cmd):
        self.putcmd(cmd)
        return self.getresp()

    def voidcmd(self, cmd):
        self.putcmd(cmd)
        return self.voidresp()

    # ----- data connections -----

    def makepasv(self):
        if self.af == socket.AF_INET:
            host, port = parse227(self.sendcmd("PASV"))
        else:
            host, port = parse229(self.sendcmd("EPSV"), self.sock.getpeername())
        return host, port

    def ntransfercmd(self, cmd, rest=None):
        size = None
        if self.passiveserver:
            host, port = self.makepasv()
            sys_default = socket.getdefaulttimeout()
            timeout_arg = (sys_default if self.timeout is _GLOBAL_DEFAULT_TIMEOUT
                           else self.timeout)
            conn = socket.create_connection(
                (host, port),
                timeout_arg if timeout_arg is not None else socket._GLOBAL_DEFAULT_TIMEOUT,
                source_address=self.source_address,
            )
            try:
                if rest is not None:
                    self.sendcmd("REST %s" % rest)
                resp = self.sendcmd(cmd)
                if resp[0] == "2":
                    resp = self.getresp()
                if resp[0] != "1":
                    raise error_reply(resp)
            except Exception:
                conn.close()
                raise
        else:
            raise Error("active mode not supported in clean-room build")
        if resp[:3] == "150":
            size = parse150(resp)
        return conn, size

    def transfercmd(self, cmd, rest=None):
        return self.ntransfercmd(cmd, rest)[0]

    # ----- public commands -----

    def login(self, user="", passwd="", acct=""):
        if not user:
            user = "anonymous"
        if not passwd:
            passwd = ""
        if not acct:
            acct = ""
        if user == "anonymous" and passwd in {"", "-"}:
            passwd = passwd + "anonymous@"
        resp = self.sendcmd("USER " + user)
        if resp[0] == "3":
            resp = self.sendcmd("PASS " + passwd)
        if resp[0] == "3":
            resp = self.sendcmd("ACCT " + acct)
        if resp[0] != "2":
            raise error_reply(resp)
        return resp

    def retrbinary(self, cmd, callback, blocksize=8192, rest=None):
        self.voidcmd("TYPE I")
        with self.transfercmd(cmd, rest) as conn:
            while True:
                data = conn.recv(blocksize)
                if not data:
                    break
                callback(data)
        return self.voidresp()

    def storbinary(self, cmd, fp, blocksize=8192, callback=None, rest=None):
        self.voidcmd("TYPE I")
        with self.transfercmd(cmd, rest) as conn:
            while True:
                buf = fp.read(blocksize)
                if not buf:
                    break
                conn.sendall(buf)
                if callback:
                    callback(buf)
        return self.voidresp()

    def nlst(self, *args):
        cmd = "NLST"
        for arg in args:
            cmd = cmd + (" " + arg)
        files = []
        self.retrlines(cmd, files.append)
        return files

    def retrlines(self, cmd, callback=None):
        if callback is None:
            callback = print_line
        resp = self.sendcmd("TYPE A")
        with self.transfercmd(cmd) as conn, \
                conn.makefile("r", encoding=self.encoding) as fp:
            while True:
                line = fp.readline(self.maxline + 1)
                if len(line) > self.maxline:
                    raise Error("got more than %d bytes" % self.maxline)
                if not line:
                    break
                if line[-2:] == CRLF:
                    line = line[:-2]
                elif line[-1:] == "\n":
                    line = line[:-1]
                callback(line)
        return self.voidresp()

    def pwd(self):
        resp = self.voidcmd("PWD")
        return parse257(resp)

    def mkd(self, dirname):
        resp = self.voidcmd("MKD " + dirname)
        if not resp.startswith("257"):
            return ""
        return parse257(resp)

    def rmd(self, dirname):
        return self.voidcmd("RMD " + dirname)

    def cwd(self, dirname):
        if dirname == "..":
            try:
                return self.voidcmd("CDUP")
            except error_perm as msg:
                if msg.args[0][:3] != "500":
                    raise
        elif dirname == "":
            dirname = "."
        cmd = "CWD " + dirname
        return self.voidcmd(cmd)

    def delete(self, filename):
        resp = self.sendcmd("DELE " + filename)
        if resp[:3] in {"250", "200"}:
            return resp
        raise error_reply(resp)

    def rename(self, fromname, toname):
        resp = self.sendcmd("RNFR " + fromname)
        if resp[0] != "3":
            raise error_reply(resp)
        return self.voidcmd("RNTO " + toname)

    def quit(self):
        resp = self.voidcmd("QUIT")
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

    def __enter__(self):
        return self

    def __exit__(self, *args):
        if self.sock is not None:
            try:
                self.quit()
            except (OSError, EOFError):
                pass
            finally:
                if self.sock is not None:
                    self.close()


def print_line(line):
    print(line)


# ---------------------------------------------------------------------------
# Reply parsers
# ---------------------------------------------------------------------------

_227_re = re.compile(r"(\d+),(\d+),(\d+),(\d+),(\d+),(\d+)", re.ASCII)


def parse227(resp):
    """Parse a 227 PASV reply, returning (host, port)."""
    if resp[:3] != "227":
        raise error_reply(resp)
    m = _227_re.search(resp)
    if not m:
        raise error_proto(resp)
    numbers = m.groups()
    host = ".".join(numbers[:4])
    port = (int(numbers[4]) << 8) + int(numbers[5])
    return host, port


def parse229(resp, peer):
    """Parse a 229 EPSV reply, returning (host, port)."""
    if resp[:3] != "229":
        raise error_reply(resp)
    left = resp.find("(")
    if left < 0:
        raise error_proto(resp)
    right = resp.find(")", left + 1)
    if right < 0:
        raise error_proto(resp)
    if resp[left + 1] != resp[right - 1]:
        raise error_proto(resp)
    parts = resp[left + 1:right].split(resp[left + 1])
    if len(parts) != 5:
        raise error_proto(resp)
    host = peer[0]
    port = int(parts[3])
    return host, port


def parse257(resp):
    """Parse a 257 MKD/PWD reply, returning the directory name."""
    if resp[:3] != "257":
        raise error_reply(resp)
    if resp[3:5] != ' "':
        return ""
    dirname = ""
    i = 5
    n = len(resp)
    while i < n:
        c = resp[i]
        i += 1
        if c == '"':
            if i >= n or resp[i] != '"':
                break
            i += 1
        dirname = dirname + c
    return dirname


def parse150(resp):
    """Parse the optional size hint out of a 150 reply.  Returns int or None."""
    if resp[:3] != "150":
        raise error_reply(resp)
    m = re.search(r"\((\d+)(?:\s+bytes)?\)", resp, re.IGNORECASE)
    if not m:
        return None
    return int(m.group(1))


# ---------------------------------------------------------------------------
# Invariant probes
# ---------------------------------------------------------------------------

def ftplib2_exceptions():
    """Confirm the four named exceptions exist and inherit from Exception."""
    for exc in (error_reply, error_temp, error_perm, error_proto):
        if not isinstance(exc, type):
            return False
        if not issubclass(exc, Exception):
            return False
    # Each exception should be distinct.
    names = {error_reply, error_temp, error_perm, error_proto}
    if len(names) != 4:
        return False
    # Instantiation should work and round-trip the message.
    try:
        for exc in names:
            inst = exc("hello")
            if str(inst) != "hello":
                return False
    except Exception:
        return False
    return True


def ftplib2_parse227():
    """Confirm parse227 decodes a sample PASV reply correctly."""
    cases = [
        ("227 Entering Passive Mode (127,0,0,1,4,1).",
         ("127.0.0.1", (4 << 8) + 1)),
        ("227 =192,168,1,2,200,21",
         ("192.168.1.2", (200 << 8) + 21)),
    ]
    for resp, expected in cases:
        try:
            got = parse227(resp)
        except Exception:
            return False
        if got != expected:
            return False
    # Wrong code should raise error_reply.
    try:
        parse227("228 nope")
    except error_reply:
        pass
    except Exception:
        return False
    else:
        return False
    # Malformed body should raise error_proto.
    try:
        parse227("227 no numbers here")
    except error_proto:
        pass
    except Exception:
        return False
    else:
        return False
    return True


def ftplib2_parse257():
    """Confirm parse257 decodes MKD/PWD replies correctly."""
    cases = [
        ('257 "/home/user" created.', "/home/user"),
        ('257 "" is current directory.', ""),
        ('257 "with""quote" created.', 'with"quote'),
        ("257 no-quotes-here", ""),
    ]
    for resp, expected in cases:
        try:
            got = parse257(resp)
        except Exception:
            return False
        if got != expected:
            return False
    # Wrong code should raise error_reply.
    try:
        parse257("550 not found")
    except error_reply:
        pass
    except Exception:
        return False
    else:
        return False
    return True