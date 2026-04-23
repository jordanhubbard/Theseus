"""
theseus_smtplib_cr — Clean-room smtplib module.
No import of the standard `smtplib` module.
"""

import socket as _socket
import re as _re
import base64 as _base64
import hmac as _hmac
import copy as _copy


SMTP_PORT = 25
SMTP_SSL_PORT = 465
CRLF = '\r\n'
bCRLF = b'\r\n'
_MAXLINE = 8192

OLDSTYLE_AUTH = _re.compile(r'auth=(.*)', _re.I)


class SMTPException(OSError):
    pass

class SMTPNotSupportedError(SMTPException):
    pass

class SMTPServerDisconnected(SMTPException):
    pass

class SMTPResponseException(SMTPException):
    def __init__(self, code, msg):
        self.smtp_code = code
        self.smtp_error = msg
        self.args = (code, msg)

class SMTPSenderRefused(SMTPResponseException):
    def __init__(self, code, msg, sender):
        self.smtp_code = code
        self.smtp_error = msg
        self.sender = sender
        self.args = (code, msg, sender)

class SMTPRecipientsRefused(SMTPException):
    def __init__(self, recipients):
        self.recipients = recipients
        self.args = (recipients,)

class SMTPDataError(SMTPResponseException):
    pass

class SMTPConnectError(SMTPResponseException):
    pass

class SMTPHeloError(SMTPResponseException):
    pass

class SMTPAuthenticationError(SMTPResponseException):
    pass


def quoteaddr(addrstring):
    """Quote a subset of the email addresses defined by RFC 821."""
    displayname, addr = _parseaddr(addrstring)
    if (displayname, addr) == (None, None):
        return '<%s>' % addrstring.strip()
    if addr is None:
        return '<%s>' % addrstring.strip()
    if addr == '':
        raise SMTPSenderRefused(500, 'Empty address', addrstring)
    return '<%s>' % addr


def _parseaddr(addr):
    """Simple address parser."""
    addr = addr.strip()
    m = _re.match(r'^.*<([^>]+)>\s*$', addr)
    if m:
        return addr[:m.start(1)-1].strip(), m.group(1)
    return None, addr


def quotedata(data):
    """Quote data for sending."""
    return _re.sub(r'(?m)^\.', '..', data.replace('\r\n', '\n').replace('\r', '\n').replace('\n', CRLF))


def _quote_periods(bindata):
    return _re.sub(rb'(?m)^\.', b'..', bindata)


def _fix_eols(data):
    return _re.sub(r'(?:\r\n|\n|\r(?!\n))', CRLF, data)


class SMTP:
    """SMTP client."""

    debuglevel = 0
    sock = None
    file = None
    helo_resp = None
    ehlo_msg = 'ehlo'
    ehlo_resp = None
    does_esmtp = False
    default_port = SMTP_PORT

    def __init__(self, host='', port=0, local_hostname=None, timeout=_socket._GLOBAL_DEFAULT_TIMEOUT, source_address=None):
        self._host = host
        self.timeout = timeout
        self.esmtp_features = {}
        self.command_encoding = 'ascii'
        self.source_address = source_address
        if local_hostname is not None:
            self.local_hostname = local_hostname
        else:
            fqdn = _socket.getfqdn()
            if '.' in fqdn:
                self.local_hostname = fqdn
            else:
                addr = '127.0.0.1'
                try:
                    addr = _socket.gethostbyname(_socket.gethostname())
                except _socket.gaierror:
                    pass
                self.local_hostname = '[%s]' % addr
        if host:
            code, msg = self.connect(host, port, source_address=source_address)
            if code != 220:
                try:
                    self.quit()
                except SMTPServerDisconnected:
                    pass
                raise SMTPConnectError(code, msg)

    def set_debuglevel(self, debuglevel):
        self.debuglevel = debuglevel

    def _print_debug(self, *args):
        if self.debuglevel > 0:
            import sys
            print(*args, file=sys.stderr)

    def _get_socket(self, host, port, timeout):
        return _socket.create_connection((host, port), timeout, self.source_address)

    def connect(self, host='localhost', port=0, source_address=None):
        if source_address:
            self.source_address = source_address
        if not port:
            port = self.default_port
        if ':' in host:
            _host, _port = host.rsplit(':', 1)
            try:
                port = int(_port)
                host = _host
            except ValueError:
                pass
        self.sock = self._get_socket(host, port, self.timeout)
        self.sock.setsockopt(_socket.SOL_SOCKET, _socket.SO_KEEPALIVE, 1)
        (code, msg) = self.getreply()
        if self.debuglevel > 0:
            self._print_debug('connect:', repr(msg))
        return (code, msg)

    def send(self, s):
        if self.sock is None:
            raise SMTPServerDisconnected('please run connect() first')
        if isinstance(s, str):
            s = s.encode('ascii')
        try:
            self.sock.sendall(s)
        except OSError:
            self.close()
            raise SMTPServerDisconnected('Connection unexpectedly closed')

    def putcmd(self, cmd, args=''):
        if args == '':
            s = '%s%s' % (cmd, CRLF)
        else:
            s = '%s %s%s' % (cmd, args, CRLF)
        self.send(s)

    def getreply(self):
        resp = []
        if self.file is None:
            self.file = self.sock.makefile('rb')
        while True:
            try:
                line = self.file.readline(_MAXLINE + 1)
            except OSError:
                self.close()
                raise SMTPServerDisconnected("Connection unexpectedly closed")
            if not line:
                self.close()
                raise SMTPServerDisconnected("Connection unexpectedly closed")
            if self.debuglevel > 0:
                self._print_debug('reply:', repr(line))
            if len(line) > _MAXLINE:
                self.close()
                raise SMTPResponseException(500, "Line too long.")
            resp.append(line[4:].strip(b' \t\r\n'))
            code = line[:3]
            try:
                errcode = int(code)
            except ValueError:
                errcode = -1
                break
            if line[3:4] != b'-':
                break
        errmsg = b'\n'.join(resp)
        if self.debuglevel > 0:
            self._print_debug('reply: retcode (%s); Msg: %a' % (errcode, errmsg))
        return errcode, errmsg

    def docmd(self, cmd, args=''):
        self.putcmd(cmd, args)
        return self.getreply()

    def helo(self, name=''):
        self.putcmd('helo', name or self.local_hostname)
        (code, msg) = self.getreply()
        self.helo_resp = msg
        return (code, msg)

    def ehlo(self, name=''):
        self.esmtp_features = {}
        self.putcmd(self.ehlo_msg, name or self.local_hostname)
        (code, msg) = self.getreply()
        if code == -1 and len(msg) == 0:
            self.close()
            raise SMTPServerDisconnected("Server not connected")
        self.ehlo_resp = msg
        if code != 250:
            return (code, msg)
        self.does_esmtp = True
        resp = msg.decode('latin-1').split('\n')
        del resp[0]
        for each in resp:
            auth_match = OLDSTYLE_AUTH.match(each)
            if auth_match:
                self.esmtp_features['auth'] = self.esmtp_features.get('auth', '') + ' ' + auth_match.groups(0)[0]
                continue
            m = _re.match(r'(?P<feature>[A-Za-z0-9][A-Za-z0-9\-]*) ?', each)
            if m:
                feature = m.group('feature').lower()
                params = m.string[m.end():].strip()
                if feature == 'auth':
                    self.esmtp_features[feature] = self.esmtp_features.get(feature, '') + ' ' + params
                else:
                    self.esmtp_features[feature] = params
        return (code, msg)

    def has_extn(self, opt):
        return opt.lower() in self.esmtp_features

    def help(self, args=''):
        self.putcmd('help', args)
        return self.getreply()[1]

    def rset(self):
        self.command_encoding = 'ascii'
        return self.docmd('rset')

    def noop(self):
        return self.docmd('noop')

    def mail(self, sender, options=()):
        optionlist = ''
        if options and self.does_esmtp:
            if any(x.lower() == 'smtputf8' for x in options):
                if self.has_extn('smtputf8'):
                    self.command_encoding = 'utf-8'
                else:
                    raise SMTPNotSupportedError('SMTPUTF8 not supported by server')
            optionlist = ' ' + ' '.join(options)
        self.putcmd('mail', 'FROM:%s%s' % (quoteaddr(sender), optionlist))
        return self.getreply()

    def rcpt(self, recip, options=()):
        optionlist = ''
        if options and self.does_esmtp:
            optionlist = ' ' + ' '.join(options)
        self.putcmd('rcpt', 'TO:%s%s' % (quoteaddr(recip), optionlist))
        return self.getreply()

    def data(self, msg):
        self.putcmd('data')
        (code, repl) = self.getreply()
        if self.debuglevel > 0:
            self._print_debug('data:', (code, repl))
        if code != 354:
            raise SMTPDataError(code, repl)
        if isinstance(msg, str):
            msg = _fix_eols(msg).encode('ascii')
        q = _quote_periods(msg)
        if q[-2:] != bCRLF:
            q = q + bCRLF
        q = q + b'.' + bCRLF
        self.send(q)
        (code, msg) = self.getreply()
        if self.debuglevel > 0:
            self._print_debug('data:', (code, msg))
        if code != 250:
            raise SMTPDataError(code, msg)
        return (code, msg)

    def verify(self, address):
        self.putcmd('vrfy', _re.sub(r'\n', ' ', address))
        return self.getreply()

    vrfy = verify

    def expn(self, address):
        self.putcmd('expn', _re.sub(r'\n', ' ', address))
        return self.getreply()

    def ehlo_or_helo_if_needed(self):
        if self.helo_resp is None and self.ehlo_resp is None:
            if not (200 <= self.ehlo(self.local_hostname)[0] <= 299):
                (code, resp) = self.helo(self.local_hostname)
                if not (200 <= code <= 299):
                    raise SMTPHeloError(code, resp)

    def login(self, user, password, *, initial_response_ok=True):
        self.ehlo_or_helo_if_needed()
        advertised_authlist = self.esmtp_features.get('auth', '').split()
        try_auths = []
        if 'LOGIN' in advertised_authlist:
            try_auths.append('LOGIN')
        if 'PLAIN' in advertised_authlist:
            try_auths.append('PLAIN')
        if not try_auths:
            raise SMTPException('No suitable authentication method found.')
        for authmethod in try_auths:
            try:
                return self.auth(authmethod, self._auth_plain if authmethod == 'PLAIN' else self._auth_login, initial_response_ok=initial_response_ok)
            except SMTPAuthenticationError:
                pass
        raise SMTPAuthenticationError(535, b'Authentication failed.')

    def _auth_plain(self, challenge=None):
        credentials = '\0%s\0%s' % (self.user, self.password) if hasattr(self, 'user') else '\0\0'
        return _base64.b64encode(credentials.encode('utf-8')).decode('ascii')

    def _auth_login(self, challenge=None):
        if challenge is None or challenge.lower() == b'user name:':
            return _base64.b64encode(b'').decode('ascii')
        return _base64.b64encode(b'').decode('ascii')

    def auth(self, mechanism, authobject, *, initial_response_ok=True):
        mechanism = mechanism.upper()
        initial_response = None
        if initial_response_ok:
            try:
                initial_response = authobject(None)
            except SMTPException:
                initial_response = None
        if initial_response is not None:
            response, code, resp = initial_response, *self.docmd('AUTH', mechanism + ' ' + initial_response)
        else:
            code, resp = self.docmd('AUTH', mechanism)
        if code in (334, 235):
            challenge = _base64.decodebytes(resp)
            response = authobject(challenge)
        if code == 334:
            code, resp = self.docmd(response or '=')
        if code == 235:
            return (code, resp)
        raise SMTPAuthenticationError(code, resp)

    def sendmail(self, from_addr, to_addrs, msg, mail_options=(), rcpt_options=()):
        self.ehlo_or_helo_if_needed()
        esmtp_opts = []
        if isinstance(msg, str):
            msg = _fix_eols(msg).encode('ascii')
        if self.does_esmtp:
            if self.has_extn('size'):
                esmtp_opts.append('size=%d' % len(msg))
            for opt in mail_options:
                esmtp_opts.append(opt)
        (code, resp) = self.mail(from_addr, esmtp_opts)
        if code != 250:
            if code == 421:
                self.close()
            else:
                self._rset()
            raise SMTPSenderRefused(code, resp, from_addr)
        senderrs = {}
        if isinstance(to_addrs, str):
            to_addrs = [to_addrs]
        for each in to_addrs:
            (code, resp) = self.rcpt(each, rcpt_options)
            if code not in (250, 251):
                senderrs[each] = (code, resp)
        if len(senderrs) == len(to_addrs):
            self._rset()
            raise SMTPRecipientsRefused(senderrs)
        (code, resp) = self.data(msg)
        if senderrs:
            raise SMTPRecipientsRefused(senderrs)
        return senderrs

    def _rset(self):
        try:
            self.rset()
        except SMTPServerDisconnected:
            pass

    def send_message(self, msg, from_addr=None, to_addrs=None, mail_options=(), rcpt_options=()):
        from email.generator import BytesGenerator
        import io
        resent = msg.get_all('Resent-Date')
        if resent is None:
            header_prefix = ''
        elif len(resent) == 1:
            header_prefix = 'Resent-'
        else:
            raise ValueError('message has more than one \'Resent-\' header block')
        if from_addr is None:
            from_addr = (msg[header_prefix + 'Sender'] if (header_prefix + 'Sender') in msg else msg[header_prefix + 'From'])
        if to_addrs is None:
            addr_fields = [f for f in (msg[header_prefix + 'To'], msg[header_prefix + 'Cc'], msg[header_prefix + 'Bcc']) if f is not None]
            to_addrs = [a for f in addr_fields for a in _re.split(r',\s*', f)]
        msg_copy = _copy.copy(msg)
        del msg_copy['Bcc']
        del msg_copy['Resent-Bcc']
        flatmsg = io.BytesIO()
        g = BytesGenerator(flatmsg)
        g.flatten(msg_copy, linesep='\r\n')
        flatmsg = flatmsg.getvalue()
        return self.sendmail(from_addr, to_addrs, flatmsg, mail_options, rcpt_options)

    def close(self):
        try:
            file = self.file
            self.file = None
            if file:
                file.close()
        finally:
            sock = self.sock
            self.sock = None
            if sock:
                sock.close()

    def quit(self):
        res = self.docmd('quit')
        self.close()
        return res

    def starttls(self, keyfile=None, certfile=None, context=None):
        self.ehlo_or_helo_if_needed()
        if not self.has_extn('starttls'):
            raise SMTPNotSupportedError("STARTTLS extension not supported by server.")
        import ssl
        (resp, reply) = self.docmd('STARTTLS')
        if resp == 220:
            if context is None:
                context = ssl.create_default_context()
            self.sock = context.wrap_socket(self.sock, server_hostname=self._host)
            self.file = None
            self.helo_resp = None
            self.ehlo_resp = None
            self.esmtp_features = {}
            self.does_esmtp = False
        return (resp, reply)


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def smtplib2_exceptions():
    """smtplib exception classes exist and inherit correctly; returns True."""
    return (issubclass(SMTPException, OSError) and
            issubclass(SMTPServerDisconnected, SMTPException) and
            issubclass(SMTPResponseException, SMTPException) and
            issubclass(SMTPAuthenticationError, SMTPResponseException))


def smtplib2_quoteaddr():
    """quoteaddr wraps email address in angle brackets; returns True."""
    result = quoteaddr('user@example.com')
    return result == '<user@example.com>'


def smtplib2_quotedata():
    """quotedata doubles leading dots in SMTP data; returns True."""
    result = quotedata('line1\n.dotline\nline3')
    return '..dotline' in result


__all__ = [
    'SMTP', 'SMTPException', 'SMTPNotSupportedError', 'SMTPServerDisconnected',
    'SMTPResponseException', 'SMTPSenderRefused', 'SMTPRecipientsRefused',
    'SMTPDataError', 'SMTPConnectError', 'SMTPHeloError', 'SMTPAuthenticationError',
    'SMTP_PORT', 'SMTP_SSL_PORT', 'quoteaddr', 'quotedata',
    'smtplib2_exceptions', 'smtplib2_quoteaddr', 'smtplib2_quotedata',
]
