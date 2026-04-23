"""
theseus_http_cookiejar_cr — Clean-room http.cookiejar module.
No import of the standard `http.cookiejar` module.
"""

import time as _time
import re as _re
import threading as _threading


class LoadError(OSError):
    pass


class Cookie:
    """HTTP Cookie."""

    def __init__(self, version, name, value,
                 port, port_specified,
                 domain, domain_specified, domain_initial_dot,
                 path, path_specified,
                 secure,
                 expires,
                 discard,
                 comment,
                 comment_url,
                 rest,
                 rfc2109=False):
        self.version = version
        self.name = name
        self.value = value
        self.port = port
        self.port_specified = port_specified
        self.domain = domain
        self.domain_specified = domain_specified
        self.domain_initial_dot = domain_initial_dot
        self.path = path
        self.path_specified = path_specified
        self.secure = secure
        self.expires = expires
        self.discard = discard
        self.comment = comment
        self.comment_url = comment_url
        self._rest = rest
        self.rfc2109 = rfc2109

    def has_nonstandard_attr(self, name):
        return name in self._rest

    def get_nonstandard_attr(self, name, default=None):
        return self._rest.get(name, default)

    def set_nonstandard_attr(self, name, value):
        self._rest[name] = value

    def is_expired(self, now=None):
        if now is None:
            now = _time.time()
        if self.expires is not None and self.expires <= now:
            return True
        return False

    def __repr__(self):
        if self.port is None:
            p = ''
        else:
            p = ':' + self.port
        limit = self.domain + p + self.path
        return '<Cookie %s=%s for %s>' % (self.name, self.value, limit)

    def __str__(self):
        return repr(self)


class CookiePolicy:
    """Defines which cookies are accepted."""

    def set_ok(self, cookie, request):
        raise NotImplementedError

    def return_ok(self, cookie, request):
        raise NotImplementedError

    def domain_return_ok(self, domain, request):
        raise NotImplementedError

    def path_return_ok(self, path, request):
        raise NotImplementedError


class DefaultCookiePolicy(CookiePolicy):
    """Default cookie policy."""

    DomainStrictNoDots = 1
    DomainStrictNonDomain = 2
    DomainRFC2965Match = 4
    DomainLiberal = 0
    DomainStrict = DomainStrictNoDots | DomainStrictNonDomain

    def __init__(self, blocked_domains=None, allowed_domains=None, **kw):
        self._blocked_domains = tuple(blocked_domains or [])
        self._allowed_domains = None if allowed_domains is None else tuple(allowed_domains)
        self.netscape = kw.get('netscape', True)
        self.rfc2965 = kw.get('rfc2965', False)
        self.rfc2109_as_netscape = kw.get('rfc2109_as_netscape', None)
        self.hide_cookie2 = kw.get('hide_cookie2', False)
        self.strict_domain = kw.get('strict_domain', False)
        self.strict_rfc2965_unverifiable = kw.get('strict_rfc2965_unverifiable', True)
        self.strict_ns_unverifiable = kw.get('strict_ns_unverifiable', False)
        self.strict_ns_domain = kw.get('strict_ns_domain', self.DomainLiberal)
        self.strict_ns_set_initial_dollar = kw.get('strict_ns_set_initial_dollar', False)
        self.strict_ns_set_path = kw.get('strict_ns_set_path', False)

    def blocked_domains(self):
        return self._blocked_domains

    def set_blocked_domains(self, blocked_domains):
        self._blocked_domains = tuple(blocked_domains)

    def is_blocked(self, domain):
        for blocked in self._blocked_domains:
            if domain.endswith(blocked):
                return True
        return False

    def allowed_domains(self):
        return self._allowed_domains

    def set_allowed_domains(self, allowed_domains):
        if allowed_domains is None:
            self._allowed_domains = None
        else:
            self._allowed_domains = tuple(allowed_domains)

    def is_not_allowed(self, domain):
        if self._allowed_domains is None:
            return False
        for allowed in self._allowed_domains:
            if domain.endswith(allowed):
                return False
        return True

    def set_ok(self, cookie, request):
        return True

    def return_ok(self, cookie, request):
        return True

    def domain_return_ok(self, domain, request):
        return True

    def path_return_ok(self, path, request):
        return True


class CookieJar:
    """Collection of Cookies."""

    non_word_re = _re.compile(r'\W')
    quote_re = _re.compile(r"([\\\"'\\\\])")

    def __init__(self, policy=None):
        if policy is None:
            policy = DefaultCookiePolicy()
        self._policy = policy
        self._cookies_lock = _threading.RLock()
        self._cookies = {}

    def set_policy(self, policy):
        self._policy = policy

    def _cookies_for_domain(self, domain, request):
        cookies = []
        if domain in self._cookies:
            for path, name_map in self._cookies[domain].items():
                for name, cookie in name_map.items():
                    if not cookie.is_expired():
                        cookies.append(cookie)
        return cookies

    def _cookies_for_request(self, request):
        cookies = []
        with self._cookies_lock:
            for domain in self._cookies:
                cookies.extend(self._cookies_for_domain(domain, request))
        return cookies

    def set_cookie(self, cookie):
        with self._cookies_lock:
            domain = cookie.domain
            if domain not in self._cookies:
                self._cookies[domain] = {}
            c = self._cookies[domain]
            if cookie.path not in c:
                c[cookie.path] = {}
            c[cookie.path][cookie.name] = cookie

    def set_cookie_if_ok(self, cookie, request):
        if self._policy.set_ok(cookie, request):
            self.set_cookie(cookie)

    def clear(self, domain=None, path=None, name=None):
        with self._cookies_lock:
            if domain is None:
                self._cookies = {}
            elif path is None:
                if domain in self._cookies:
                    del self._cookies[domain]
            elif name is None:
                if domain in self._cookies and path in self._cookies[domain]:
                    del self._cookies[domain][path]
            else:
                if (domain in self._cookies and
                        path in self._cookies[domain] and
                        name in self._cookies[domain][path]):
                    del self._cookies[domain][path][name]

    def clear_expired_cookies(self):
        with self._cookies_lock:
            for domain in list(self._cookies.keys()):
                for path in list(self._cookies[domain].keys()):
                    for name in list(self._cookies[domain][path].keys()):
                        if self._cookies[domain][path][name].is_expired():
                            del self._cookies[domain][path][name]

    def __iter__(self):
        with self._cookies_lock:
            for domain in self._cookies:
                for path in self._cookies[domain]:
                    for name, cookie in self._cookies[domain][path].items():
                        yield cookie

    def __len__(self):
        count = 0
        with self._cookies_lock:
            for domain in self._cookies:
                for path in self._cookies[domain]:
                    count += len(self._cookies[domain][path])
        return count

    def __repr__(self):
        return '<%s[%s]>' % (self.__class__.__name__, ', '.join(repr(c) for c in self))

    def __str__(self):
        return repr(self)


class FileCookieJar(CookieJar):
    """CookieJar that can be saved/loaded from a file."""

    def __init__(self, filename=None, delayload=False, policy=None):
        CookieJar.__init__(self, policy)
        if filename is not None:
            try:
                filename = str(filename)
            except:
                raise ValueError('invalid filename')
        self.filename = filename
        self.delayload = delayload

    def save(self, filename=None, ignore_discard=False, ignore_expires=False):
        raise NotImplementedError

    def load(self, filename=None, ignore_discard=False, ignore_expires=False):
        raise NotImplementedError

    def revert(self, filename=None, ignore_discard=False, ignore_expires=False):
        old_state = self._cookies.copy()
        self._cookies = {}
        try:
            self.load(filename, ignore_discard, ignore_expires)
        except OSError:
            self._cookies = old_state
            raise


def _make_cookie(name, value, domain, path='/', expires=None, secure=False, version=0):
    """Helper to create a simple Cookie."""
    return Cookie(
        version=version,
        name=name,
        value=value,
        port=None,
        port_specified=False,
        domain=domain,
        domain_specified=True,
        domain_initial_dot=domain.startswith('.'),
        path=path,
        path_specified=True,
        secure=secure,
        expires=expires,
        discard=expires is None,
        comment=None,
        comment_url=None,
        rest={},
    )


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def cookiejar2_create():
    """CookieJar can be created and is empty initially; returns True."""
    jar = CookieJar()
    return len(jar) == 0


def cookiejar2_cookie():
    """Cookie object can be created with required attributes; returns True."""
    c = _make_cookie('session', 'abc123', '.example.com')
    return c.name == 'session' and c.value == 'abc123' and c.domain == '.example.com'


def cookiejar2_set_cookie():
    """CookieJar.set_cookie adds cookie to jar; returns True."""
    jar = CookieJar()
    c = _make_cookie('test', 'value', '.example.com')
    jar.set_cookie(c)
    return len(jar) == 1


__all__ = [
    'LoadError', 'Cookie', 'CookiePolicy', 'DefaultCookiePolicy',
    'CookieJar', 'FileCookieJar',
    'cookiejar2_create', 'cookiejar2_cookie', 'cookiejar2_set_cookie',
]
