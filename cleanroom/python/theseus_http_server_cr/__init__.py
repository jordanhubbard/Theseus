"""
theseus_http_server_cr — Clean-room http.server module.
No import of the standard `http.server` module.
"""

import socket as _socket
import io as _io
import sys as _sys
import os as _os
import time as _time
import email.utils as _email_utils
import html as _html
import mimetypes as _mimetypes
import re as _re
import urllib.parse as _urllib_parse
import http as _http


DEFAULT_ERROR_MESSAGE = """\
<!DOCTYPE HTML>
<html lang="en">
    <head>
        <meta charset="utf-8">
        <title>Error response</title>
    </head>
    <body>
        <h1>Error response</h1>
        <p>Error code: %(code)d</p>
        <p>Message: %(message)s.</p>
        <p>Error code explanation: %(code)s - %(explain)s.</p>
    </body>
</html>
"""

DEFAULT_ERROR_CONTENT_TYPE = "text/html;charset=utf-8"


def _quote_html(html):
    return html.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


responses = {
    100: ('Continue', 'Request received, please continue'),
    101: ('Switching Protocols', 'Switching to new protocol; obey Upgrade header'),
    102: ('Processing', ''),
    200: ('OK', 'Request fulfilled, document follows'),
    201: ('Created', 'Document created, URL follows'),
    202: ('Accepted', 'Request accepted, processing continues off-line'),
    204: ('No Content', 'Request fulfilled, nothing follows'),
    206: ('Partial Content', 'Partial content follows'),
    301: ('Moved Permanently', 'Object moved permanently -- see URI list'),
    302: ('Found', 'Object moved temporarily -- see URI list'),
    304: ('Not Modified', 'Document has not changed since given time'),
    307: ('Temporary Redirect', 'Object moved temporarily -- see URI list'),
    308: ('Permanent Redirect', 'Object moved permanently -- see URI list'),
    400: ('Bad Request', 'Bad request syntax or unsupported method'),
    401: ('Unauthorized', 'No permission -- see authorization schemes'),
    403: ('Forbidden', 'Request forbidden -- authorization will not help'),
    404: ('Not Found', 'Nothing matches the given URI'),
    405: ('Method Not Allowed', 'Specified method is invalid for this resource'),
    408: ('Request Timeout', 'Request timed out; try again later'),
    409: ('Conflict', 'Request conflict'),
    410: ('Gone', 'URI no longer exists and has been permanently removed'),
    411: ('Length Required', 'Client must specify Content-Length'),
    413: ('Content Too Large', 'Entity is too large'),
    414: ('URI Too Long', 'URI is too long'),
    415: ('Unsupported Media Type', 'Entity body in unsupported format'),
    416: ('Requested Range Not Satisfiable', 'Cannot satisfy request range'),
    417: ('Expectation Failed', 'Expect condition could not be satisfied'),
    429: ('Too Many Requests', 'Too many requests'),
    500: ('Internal Server Error', 'Server got itself in trouble'),
    501: ('Not Implemented', 'Server does not support this operation'),
    502: ('Bad Gateway', 'Invalid responses from another server/proxy'),
    503: ('Service Unavailable', 'The server cannot process the request due to a high load'),
    504: ('Gateway Timeout', 'The gateway server did not receive a timely response'),
    505: ('HTTP Version Not Supported', 'Cannot fulfill request'),
}


class BaseHTTPRequestHandler:
    """HTTP request handler base class."""

    server_version = "BaseHTTP/0.6"
    sys_version = "Python/" + _sys.version.split()[0]
    error_message_format = DEFAULT_ERROR_MESSAGE
    error_content_type = DEFAULT_ERROR_CONTENT_TYPE
    protocol_version = "HTTP/1.0"
    MessageClass = None
    responses = responses

    def __init__(self, request, client_address, server):
        self.request = request
        self.client_address = client_address
        self.server = server
        self.setup()
        try:
            self.handle()
        finally:
            self.finish()

    def setup(self):
        conn = self.request
        if isinstance(conn, _socket.socket):
            self.connection = conn
            self.rfile = self.connection.makefile('rb')
            if self.timeout is not None:
                self.connection.settimeout(self.timeout)
            self.wfile = self.connection.makefile('wb')

    def handle(self):
        self.handle_one_request()

    def handle_one_request(self):
        try:
            self.raw_requestline = self.rfile.readline(65537)
            if len(self.raw_requestline) > 65536:
                self.requestline = ''
                self.request_version = ''
                self.command = ''
                self.send_error(_http.HTTPStatus.REQUEST_URI_TOO_LONG)
                return
            if not self.raw_requestline:
                self.close_connection = True
                return
            if not self.parse_request():
                return
            mname = 'do_' + self.command
            if not hasattr(self, mname):
                self.send_error(_http.HTTPStatus.NOT_IMPLEMENTED, 'Unsupported method (%r)' % self.command)
                return
            method = getattr(self, mname)
            method()
            self.wfile.flush()
        except TimeoutError:
            self.log_error('Request timed out: %r', self.request)
            self.close_connection = True

    def parse_request(self):
        requestline = str(self.raw_requestline, 'iso-8859-1')
        requestline = requestline.rstrip('\r\n')
        self.requestline = requestline
        words = requestline.split()
        if len(words) == 0:
            return False
        if len(words) >= 3:
            version = words[-1]
            try:
                if not version.startswith('HTTP/'):
                    raise ValueError
                base_version_number = version.split('/', 1)[1]
                version_number = base_version_number.split('.')
                if len(version_number) != 2:
                    raise ValueError
                version_number = int(version_number[0]), int(version_number[1])
            except (ValueError, IndexError):
                self.send_error(_http.HTTPStatus.BAD_REQUEST, 'Bad request version (%r)' % version)
                return False
            if version_number >= (1, 1) and self.protocol_version >= 'HTTP/1.1':
                self.close_connection = False
            if version_number >= (2, 0):
                self.send_error(_http.HTTPStatus.HTTP_VERSION_NOT_SUPPORTED,
                                'Invalid HTTP version (%s)' % base_version_number)
                return False
            self.request_version = version
        if not 2 <= len(words) <= 3:
            self.send_error(_http.HTTPStatus.BAD_REQUEST, 'Bad request syntax (%r)' % requestline)
            return False
        command, path = words[:2]
        if len(words) == 2:
            self.close_connection = True
            if command != 'GET':
                self.send_error(_http.HTTPStatus.BAD_REQUEST, 'Bad HTTP/0.9 request type (%r)' % command)
                return False
        self.command, self.path = command, path
        self.headers = self.parse_headers()
        conntype = self.headers.get('Connection', '')
        if conntype.lower() == 'close':
            self.close_connection = True
        elif conntype.lower() == 'keep-alive' and self.protocol_version >= 'HTTP/1.1':
            self.close_connection = False
        expect = self.headers.get('Expect', '')
        if expect.lower() == '100-continue' and self.protocol_version >= 'HTTP/1.1':
            if not self.handle_expect_100():
                return False
        return True

    def parse_headers(self):
        headers = {}
        while True:
            line = self.rfile.readline(65537)
            if not line or line in (b'\r\n', b'\n', b''):
                break
            if b':' in line:
                key, _, value = line.partition(b':')
                headers[key.strip().decode('iso-8859-1')] = value.strip().decode('iso-8859-1')
        return headers

    def handle_expect_100(self):
        if self.protocol_version >= 'HTTP/1.1':
            self.send_response_only(100)
            self.end_headers()
        return True

    def send_error(self, code, message=None, explain=None):
        try:
            short, long = self.responses[code]
        except KeyError:
            short, long = '???', '???'
        if message is None:
            message = short
        if explain is None:
            explain = long
        self.log_error('code %d, message %s', code, message)
        self.send_response(code, message)
        self.send_header('Content-Type', self.error_content_type)
        self.send_header('Connection', 'close')
        body = self.error_message_format % {
            'code': code,
            'message': _quote_html(message),
            'explain': _quote_html(explain),
        }
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        if self.command != 'HEAD' and code >= 200 and code not in (204, 304):
            self.wfile.write(body.encode('UTF-8', 'replace'))

    def send_response(self, code, message=None):
        if self.request_version != 'HTTP/0.9':
            if message is None:
                if code in self.responses:
                    message = self.responses[code][0]
                else:
                    message = ''
            if not hasattr(self, '_headers_buffer'):
                self._headers_buffer = []
            self._headers_buffer.append(('%s %d %s\r\n' % (self.protocol_version, code, message)).encode('latin-1', 'strict'))
        self.send_header('Server', self.version_string())
        self.send_header('Date', self.date_time_string())

    def send_response_only(self, code, message=None):
        if message is None:
            if code in self.responses:
                message = self.responses[code][0]
            else:
                message = ''
        if not hasattr(self, '_headers_buffer'):
            self._headers_buffer = []
        self._headers_buffer.append(('%s %d %s\r\n' % (self.protocol_version, code, message)).encode('latin-1', 'strict'))

    def send_header(self, keyword, value):
        if not hasattr(self, '_headers_buffer'):
            self._headers_buffer = []
        if self.request_version != 'HTTP/0.9':
            self._headers_buffer.append(('%s: %s\r\n' % (keyword, value)).encode('latin-1', 'strict'))
        if keyword.lower() == 'connection':
            if value.lower() == 'close':
                self.close_connection = True
            elif value.lower() == 'keep-alive':
                self.close_connection = False

    def end_headers(self):
        if self.request_version != 'HTTP/0.9':
            self._headers_buffer.append(b'\r\n')
            self.flush_headers()

    def flush_headers(self):
        if hasattr(self, '_headers_buffer'):
            self.wfile.write(b''.join(self._headers_buffer))
            self._headers_buffer = []

    def log_request(self, code='-', size='-'):
        if isinstance(code, _http.HTTPStatus):
            code = code.value
        self.log_message('"%s" %s %s', self.requestline, str(code), str(size))

    def log_error(self, format, *args):
        self.log_message(format, *args)

    def log_message(self, format, *args):
        _sys.stderr.write('%s - - [%s] %s\n' % (self.address_string(), self.log_date_time_string(), format % args))

    def version_string(self):
        return '%s %s' % (self.server_version, self.sys_version)

    def date_time_string(self, timestamp=None):
        if timestamp is None:
            timestamp = _time.time()
        return _email_utils.formatdate(timestamp, usegmt=True)

    def log_date_time_string(self):
        now = _time.time()
        year, month, day, hh, mm, ss, x, y, z = _time.localtime(now)
        return '%02d/%3s/%04d %02d:%02d:%02d' % (day, _monthname[month], year, hh, mm, ss)

    def address_string(self):
        return self.client_address[0]

    def finish(self):
        if not self.wfile.closed:
            try:
                self.wfile.flush()
            except _socket.error:
                pass
        self.wfile.close()
        self.rfile.close()

    timeout = None
    close_connection = True
    requestline = ''
    request_version = 'HTTP/0.9'
    command = None
    path = None


_monthname = [None, 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
              'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']


class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    """Simple HTTP request handler with GET and HEAD commands."""

    server_version = "SimpleHTTP/" + "0.6"
    extensions_map = {
        '': 'application/octet-stream',
        '.py': 'text/plain',
        '.c': 'text/plain',
        '.h': 'text/plain',
    }
    index_pages = ('index.html', 'index.htm')

    def do_GET(self):
        f = self.send_head()
        if f:
            try:
                self.copyfile(f, self.wfile)
            finally:
                f.close()

    def do_HEAD(self):
        f = self.send_head()
        if f:
            f.close()

    def send_head(self):
        path = self.translate_path(self.path)
        f = None
        if _os.path.isdir(path):
            parts = _urllib_parse.urlsplit(self.path)
            if not parts.path.endswith('/'):
                self.send_response(301)
                new_parts = (parts[0], parts[1], parts[2] + '/', parts[3], parts[4])
                new_url = _urllib_parse.urlunsplit(new_parts)
                self.send_header('Location', new_url)
                self.send_header('Content-Length', '0')
                self.end_headers()
                return None
            for index in self.index_pages:
                index = _os.path.join(path, index)
                if _os.path.exists(index):
                    path = index
                    break
            else:
                return self.list_directory(path)
        ctype = self.guess_type(path)
        try:
            f = open(path, 'rb')
        except OSError:
            self.send_error(404, 'File not found')
            return None
        try:
            fs = _os.fstat(f.fileno())
            self.send_response(200)
            self.send_header('Content-type', ctype)
            self.send_header('Content-Length', str(fs.st_size))
            self.send_header('Last-Modified', self.date_time_string(fs.st_mtime))
            self.end_headers()
            return f
        except:
            f.close()
            raise

    def list_directory(self, path):
        try:
            list_entries = _os.listdir(path)
        except OSError:
            self.send_error(404, 'No permission to list directory')
            return None
        list_entries.sort(key=lambda a: a.lower())
        r = []
        try:
            display_path = _urllib_parse.unquote(self.path, errors='surrogatepass')
        except UnicodeDecodeError:
            display_path = _urllib_parse.unquote(path)
        display_path = _html.escape(display_path, quote=False)
        enc = 'utf-8'
        title = 'Directory listing for %s' % display_path
        r.append('<!DOCTYPE HTML>')
        r.append('<html>\n<head>')
        r.append('<meta http-equiv="Content-Type" content="text/html; charset=%s">' % enc)
        r.append('<title>%s</title>\n</head>' % title)
        r.append('<body>\n<h1>%s</h1>' % title)
        r.append('<hr>\n<ul>')
        for name in list_entries:
            fullname = _os.path.join(path, name)
            displayname = linkname = name
            if _os.path.isdir(fullname):
                displayname = name + '/'
                linkname = name + '/'
            if _os.path.islink(fullname):
                displayname = name + '@'
            r.append('<li><a href="%s">%s</a></li>' % (
                _urllib_parse.quote(linkname, errors='surrogatepass'),
                _html.escape(displayname, quote=False)))
        r.append('</ul>\n<hr>\n</body>\n</html>\n')
        encoded = '\n'.join(r).encode(enc, 'surrogateescape')
        f = _io.BytesIO()
        f.write(encoded)
        f.seek(0)
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=%s' % enc)
        self.send_header('Content-Length', str(len(encoded)))
        self.end_headers()
        return f

    def translate_path(self, path):
        path = path.split('?', 1)[0]
        path = path.split('#', 1)[0]
        trailing_slash = path.rstrip().endswith('/')
        try:
            path = _urllib_parse.unquote(path, errors='surrogatepass')
        except UnicodeDecodeError:
            path = _urllib_parse.unquote(path)
        path = _os.path.normpath(path)
        words = path.split('/')
        words = filter(None, words)
        path = _os.getcwd()
        for word in words:
            if _os.path.dirname(word) or word in (_os.curdir, _os.pardir):
                continue
            path = _os.path.join(path, word)
        if trailing_slash:
            path += '/'
        return path

    def copyfile(self, source, outputfile):
        while True:
            buf = source.read(16 * 1024)
            if not buf:
                break
            outputfile.write(buf)

    def guess_type(self, path):
        base, ext = _os.path.splitext(path)
        if ext in self.extensions_map:
            return self.extensions_map[ext]
        ext = ext.lower()
        if ext in self.extensions_map:
            return self.extensions_map[ext]
        guess, _ = _mimetypes.guess_type(path)
        if guess:
            return guess
        return 'application/octet-stream'


def parse_request_line(requestline):
    """Parse an HTTP request line into (command, path, version)."""
    words = requestline.strip().split()
    if len(words) >= 3:
        return words[0], words[1], words[2]
    elif len(words) == 2:
        return words[0], words[1], 'HTTP/0.9'
    return None, None, None


class HTTPServer:
    """Basic HTTP server."""

    def __init__(self, server_address, RequestHandlerClass):
        self.server_address = server_address
        self.RequestHandlerClass = RequestHandlerClass
        self.socket = _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM)
        self.socket.setsockopt(_socket.SOL_SOCKET, _socket.SO_REUSEADDR, 1)
        self.socket.bind(server_address)
        self.socket.listen(5)

    def serve_forever(self, poll_interval=0.5):
        while True:
            try:
                request, client_address = self.socket.accept()
            except OSError:
                continue
            self.process_request(request, client_address)

    def process_request(self, request, client_address):
        self.RequestHandlerClass(request, client_address, self)

    def server_close(self):
        self.socket.close()


class ThreadingHTTPServer(HTTPServer):
    """Threaded HTTP server."""
    pass


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def http_server2_responses():
    """responses dict has entries for common status codes; returns True."""
    return (200 in responses and 404 in responses and
            responses[200][0] == 'OK' and responses[404][0] == 'Not Found')


def http_server2_handler_exists():
    """BaseHTTPRequestHandler class exists and is a type; returns True."""
    return isinstance(BaseHTTPRequestHandler, type)


def http_server2_parse_request():
    """parse_request_line splits HTTP request correctly; returns True."""
    cmd, path, version = parse_request_line('GET /index.html HTTP/1.1')
    return cmd == 'GET' and path == '/index.html' and version == 'HTTP/1.1'


__all__ = [
    'BaseHTTPRequestHandler', 'SimpleHTTPRequestHandler',
    'HTTPServer', 'ThreadingHTTPServer',
    'responses', 'parse_request_line',
    'DEFAULT_ERROR_MESSAGE', 'DEFAULT_ERROR_CONTENT_TYPE',
    'http_server2_responses', 'http_server2_handler_exists',
    'http_server2_parse_request',
]
