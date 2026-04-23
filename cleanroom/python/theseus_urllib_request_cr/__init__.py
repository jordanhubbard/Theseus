"""
theseus_urllib_request_cr — Clean-room urllib.request module.
No import of the standard `urllib.request` module.
"""

import socket as _socket
import http.client as _http_client
import io as _io
import os as _os
import re as _re
import base64 as _base64
import email.message as _email_message
import urllib.parse as _urllib_parse
import urllib.error as _urllib_error
import urllib.response as _urllib_response
import sys as _sys
import time as _time
import ssl as _ssl


__version__ = __import__('sys').version[:3]

_opener = None


def urlopen(url, data=None, timeout=_socket._GLOBAL_DEFAULT_TIMEOUT, *,
            cafile=None, capath=None, cadefault=False, context=None):
    """Open the URL url, which can be a string or a Request object."""
    global _opener
    if _opener is None:
        _opener = build_opener()
    return _opener.open(url, data, timeout)


def urlretrieve(url, filename=None, reporthook=None, data=None):
    """Retrieve a URL into a temporary location on disk."""
    global _opener
    if _opener is None:
        _opener = build_opener()
    url_type, path = _urllib_parse.splittype(url) if hasattr(_urllib_parse, 'splittype') else ('', url)
    try:
        response = urlopen(url, data)
    except _urllib_error.ContentTooShortError:
        raise
    headers = response.info()
    if filename:
        tfp = open(filename, 'wb')
    else:
        import tempfile
        suffix = _os.path.splitext(_urllib_parse.urlsplit(url).path)[1]
        fd, filename = tempfile.mkstemp(suffix)
        tfp = _os.fdopen(fd, 'wb')
    result = filename, headers
    bs = 1024 * 8
    size = -1
    read = 0
    blocknum = 0
    if 'content-length' in headers:
        size = int(headers['content-length'])
    if reporthook:
        reporthook(blocknum, bs, size)
    while True:
        block = response.read(bs)
        if not block:
            break
        read += len(block)
        tfp.write(block)
        blocknum += 1
        if reporthook:
            reporthook(blocknum, bs, size)
    tfp.close()
    del fp
    if size >= 0 and read < size:
        raise _urllib_error.ContentTooShortError(
            'retrieval incomplete: got only %i out of %i bytes' % (read, size),
            result
        )
    return result


def install_opener(opener):
    """Install opener as the default global URLopener."""
    global _opener
    _opener = opener


def build_opener(*handlers):
    """Create an opener object from a list of handlers."""
    opener = OpenerDirector()
    default_classes = [
        ProxyHandler,
        UnknownHandler,
        HTTPHandler,
        HTTPDefaultErrorHandler,
        HTTPRedirectHandler,
        HTTPErrorProcessor,
    ]
    if hasattr(_http_client, 'HTTPSConnection'):
        default_classes.append(HTTPSHandler)
    skip = set()
    for klass in handlers:
        skip.add(type(klass).__name__)
    for klass in default_classes:
        if klass.__name__ not in skip:
            opener.add_handler(klass())
    for handler in handlers:
        if isinstance(handler, type):
            handler = handler()
        opener.add_handler(handler)
    return opener


class Request:
    """Describes an HTTP request."""

    def __init__(self, url, data=None, headers={},
                 origin_req_host=None, unverifiable=False,
                 method=None):
        self.full_url = url
        self.headers = {}
        self.unredirected_hdrs = {}
        self._data = None
        self.data = data
        self._r_host = origin_req_host
        self.unverifiable = unverifiable
        self._method = method
        for key, value in headers.items():
            self.add_header(key, value)

    @property
    def full_url(self):
        if self.fragment:
            return '%s#%s' % (self._full_url, self.fragment)
        return self._full_url

    @full_url.setter
    def full_url(self, url):
        self._full_url = url
        self._full_url, self.fragment = _urllib_parse.splittag(url) if hasattr(_urllib_parse, 'splittag') else (url, None)
        self._parse()

    def _parse(self):
        self.type, rest = _urllib_parse.splittype(self._full_url) if hasattr(_urllib_parse, 'splittype') else self._split_type(self._full_url)
        if self.type is None:
            raise ValueError('unknown url type: %r' % self._full_url)
        self.host, self.selector = _urllib_parse.splithost(rest) if hasattr(_urllib_parse, 'splithost') else self._split_host(rest)
        if self.host:
            self.host = _urllib_parse.unquote(self.host)

    def _split_type(self, url):
        m = _re.match(r'^([a-zA-Z][-a-zA-Z0-9+.]*):(.*)', url)
        if m:
            return m.group(1).lower(), m.group(2)
        return None, url

    def _split_host(self, url):
        if url.startswith('//'):
            host, sep, path = url[2:].partition('/')
            return host, '/' + path
        return None, url

    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, data):
        if data is not None:
            self._data = data
            if not self.has_header('Content-type'):
                self.add_unredirected_header('Content-type', 'application/x-www-form-urlencoded')
            if not self.has_header('Content-length'):
                self.add_unredirected_header('Content-length', '%d' % len(data))
        else:
            self._data = None

    def get_method(self):
        if self._method is not None:
            return self._method
        if self.data is not None:
            return 'POST'
        return 'GET'

    def add_header(self, key, val):
        self.headers[key.capitalize()] = val

    def add_unredirected_header(self, key, val):
        self.unredirected_hdrs[key.capitalize()] = val

    def has_header(self, header_name):
        return (header_name.capitalize() in self.headers or
                header_name.capitalize() in self.unredirected_hdrs)

    def get_header(self, header_name, default=None):
        return self.headers.get(
            header_name.capitalize(),
            self.unredirected_hdrs.get(header_name.capitalize(), default))

    def header_items(self):
        hdrs = {k.capitalize(): v for k, v in self.unredirected_hdrs.items()}
        hdrs.update(self.headers)
        return list(hdrs.items())

    def get_full_url(self):
        return self.full_url

    def set_proxy(self, host, type):
        self.host, self.type = host, type
        self.selector = self.full_url

    @property
    def origin_req_host(self):
        return self._r_host or self.host

    def __str__(self):
        return '<Request [%s]>' % self.get_method()


class OpenerDirector:
    """Manage multiple handlers."""

    def __init__(self):
        client_version = "Python/%s" % _sys.version[:3]
        self.addheaders = [('User-Agent', client_version)]
        self.handlers = []
        self.handle_open = {}
        self.handle_error = {}

    def add_handler(self, handler):
        if not hasattr(handler, 'add_parent'):
            raise TypeError("expected BaseHandler instance, got %r" % type(handler))
        added = False
        for meth in dir(handler):
            if meth in ('redirect_request', 'do_open', 'proxy_open'):
                continue
            condition = meth.startswith
            if condition('http_error_'):
                kind = 'error'
                lookup = self.handle_error
                scheme, condition, priority = 'http', meth[len('http_error_'):], handler.handler_order
            elif condition('https_error_'):
                kind = 'error'
                lookup = self.handle_error
                scheme, condition, priority = 'https', meth[len('https_error_'):], handler.handler_order
            elif condition('_open'):
                kind = 'open'
                lookup = self.handle_open
                scheme = meth[:-len('_open')]
                priority = handler.handler_order
            elif condition('_request'):
                kind = 'request'
                continue
            elif condition('_response'):
                kind = 'response'
                continue
            else:
                continue
            lookup.setdefault(scheme, []).append((priority, handler))
            added = True
        if added:
            bisect_handlers(self.handlers, handler)
            handler.add_parent(self)

    def _call_chain(self, chain, kind, meth, *args):
        for handler in chain:
            func = getattr(handler, meth)
            result = func(*args)
            if result is not None:
                return result

    def open(self, fullurl, data=None, timeout=_socket._GLOBAL_DEFAULT_TIMEOUT):
        if isinstance(fullurl, str):
            fullurl = Request(fullurl, data)
        else:
            if data is not None:
                fullurl.data = data
        fullurl.timeout = timeout
        protocol = fullurl.type
        meth = getattr(self, '%s_request' % protocol, None)
        if meth:
            req = meth(fullurl)
        else:
            req = fullurl
        meth = getattr(self, '%s_open' % protocol, None)
        if meth:
            response = meth(req)
        else:
            chain = self.handle_open.get(protocol, [])
            chain = sorted(chain, key=lambda x: x[0])
            for _, handler in chain:
                func = getattr(handler, '%s_open' % protocol, None)
                if func:
                    response = func(req)
                    if response:
                        break
            else:
                raise _urllib_error.URLError('unknown url type: %r' % protocol)
        return response

    def error(self, proto, *args):
        if proto in ('http', 'https'):
            args = args + (400, '', {}, None)
        lookup = self.handle_error.get(proto, {})
        for _, handler in sorted(lookup, key=lambda x: x[0]):
            meth = getattr(handler, 'http_error_%s' % args[0], None)
            if meth:
                result = meth(*args[1:])
                if result:
                    return result
        raise _urllib_error.HTTPError(*args[:5])


def bisect_handlers(handlers, handler):
    bisect = 0
    for i, h in enumerate(handlers):
        if h.handler_order > handler.handler_order:
            bisect = i
            break
        bisect = i + 1
    handlers.insert(bisect, handler)


class BaseHandler:
    handler_order = 500

    def add_parent(self, parent):
        self.parent = parent

    def close(self):
        self.parent = None

    def __lt__(self, other):
        if not hasattr(other, 'handler_order'):
            return True
        return self.handler_order < other.handler_order


class HTTPDefaultErrorHandler(BaseHandler):
    def http_error_default(self, req, fp, code, msg, hdrs):
        raise _urllib_error.HTTPError(req.full_url, code, msg, hdrs, fp)


class HTTPRedirectHandler(BaseHandler):
    max_repeats = 4
    max_redirections = 10

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        m = req.get_method()
        if code in (301, 302, 303, 307, 308) and m in ('GET', 'HEAD'):
            return Request(newurl, headers={
                'Host': headers.get('host', req.host),
            })
        return None

    def http_error_302(self, req, fp, code, msg, headers):
        if 'location' in headers:
            newurl = headers['location']
            return self.parent.open(Request(newurl))
        return None

    http_error_301 = http_error_303 = http_error_307 = http_error_302


class HTTPErrorProcessor(BaseHandler):
    handler_order = 1000

    def http_response(self, request, response):
        code, msg, hdrs = response.code, response.msg, response.info()
        if not (200 <= code < 300):
            response = self.parent.error('http', request, response, code, msg, hdrs)
        return response

    https_response = http_response


class HTTPHandler(BaseHandler):
    def http_open(self, req):
        return self.do_open(_http_client.HTTPConnection, req)

    def do_open(self, http_class, req, **http_conn_args):
        host = req.host
        if not host:
            raise _urllib_error.URLError('no host given')
        try:
            h = http_class(host, timeout=req.timeout, **http_conn_args)
            headers = dict(req.header_items())
            h.request(req.get_method(), req.selector or '/', req.data, headers)
            r = h.getresponse()
        except OSError as err:
            raise _urllib_error.URLError(err)
        r.url = req.get_full_url()
        r.msg = r.reason
        return r


class HTTPSHandler(BaseHandler):
    def __init__(self, debuglevel=0, context=None, check_hostname=None):
        BaseHandler.__init__(self)
        self._debuglevel = debuglevel
        self._context = context

    def https_open(self, req):
        return self.do_open(
            lambda host, **kw: _http_client.HTTPSConnection(
                host, context=self._context, **kw
            ),
            req,
        )

    do_open = HTTPHandler.do_open


class UnknownHandler(BaseHandler):
    def unknown_open(self, req):
        type = req.type
        raise _urllib_error.URLError('unknown url type: %r' % type)


class ProxyHandler(BaseHandler):
    handler_order = 100

    def __init__(self, proxies=None):
        if proxies is None:
            proxies = _os.environ
        self.proxies = proxies

    def proxy_open(self, req, proxy, type):
        orig_type = req.type
        proxy = _urllib_parse.unquote(proxy) if proxy else None
        if proxy:
            req.set_proxy(proxy.replace('%s://' % type, ''), type)
        return None

    def __lt__(self, other):
        if not hasattr(other, 'handler_order'):
            return True
        return self.handler_order < other.handler_order


class FileHandler(BaseHandler):
    def open_local_file(self, req):
        import mimetypes
        host = req.host
        filename = req.selector
        localfile = _urllib_request_url2pathname(filename)
        try:
            stats = _os.stat(localfile)
        except OSError as msg:
            raise _urllib_error.URLError(msg)
        size = stats.st_size
        modified = _time.gmtime(stats.st_mtime)
        mtype = mimetypes.guess_type(localfile)[0]
        headers = _email_message.Message()
        headers.add_header('Content-type', mtype or 'text/plain')
        headers.add_header('Content-length', str(size))
        headers.add_header('Last-modified', _time.strftime('%a, %d %b %Y %H:%M:%S GMT', modified))
        if not host:
            urlfile = filename
            if filename.startswith('///'):
                filename = filename[2:]
            localfile = _urllib_request_url2pathname(filename)
        try:
            stats = _os.stat(localfile)
        except OSError as msg:
            raise _urllib_error.URLError(msg)
        fp = open(localfile, 'rb')
        return _urllib_response.addinfourl(fp, headers, 'file:' + filename)

    def file_open(self, req):
        url = req.selector
        if url[:2] == '//' and url[:3] != '///':
            req.type = 'ftp'
            return self.parent.open(req)
        else:
            return self.open_local_file(req)


def pathname2url(pathname):
    """Convert a pathname to a file URL path."""
    if pathname.startswith('/'):
        return pathname
    return '/' + pathname


def url2pathname(pathname):
    """Convert a file URL path to a pathname."""
    if pathname.startswith('/'):
        return pathname
    return pathname


_urllib_request_url2pathname = url2pathname


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def urllib_request2_request():
    """Request object stores URL and headers; returns True."""
    r = Request('http://example.com/path', headers={'Accept': 'text/html'})
    return r.full_url == 'http://example.com/path' and r.get_method() == 'GET'


def urllib_request2_add_header():
    """Request.add_header stores header values; returns True."""
    r = Request('http://example.com/')
    r.add_header('User-Agent', 'TestBot/1.0')
    r.add_header('Accept', 'text/plain')
    return r.get_header('User-agent') == 'TestBot/1.0'


def urllib_request2_pathname2url():
    """pathname2url converts filesystem path to URL path; returns True."""
    result = pathname2url('/usr/local/bin')
    return result.startswith('/usr/local/bin')


__all__ = [
    'Request', 'OpenerDirector', 'BaseHandler',
    'HTTPHandler', 'HTTPSHandler', 'HTTPDefaultErrorHandler',
    'HTTPRedirectHandler', 'HTTPErrorProcessor',
    'UnknownHandler', 'ProxyHandler', 'FileHandler',
    'urlopen', 'urlretrieve', 'install_opener', 'build_opener',
    'pathname2url', 'url2pathname',
    'urllib_request2_request', 'urllib_request2_add_header',
    'urllib_request2_pathname2url',
]
