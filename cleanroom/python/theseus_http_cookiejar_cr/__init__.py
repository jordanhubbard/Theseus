"""Clean-room reimplementation of http.cookiejar (minimal subset)."""

import re
import time


class CookieError(Exception):
    pass


class Cookie:
    """A simple HTTP cookie."""

    def __init__(self, version=0, name="", value="",
                 port=None, port_specified=False,
                 domain="", domain_specified=True, domain_initial_dot=False,
                 path="/", path_specified=True,
                 secure=False, expires=None,
                 discard=True, comment=None, comment_url=None,
                 rest=None, rfc2109=False):
        if name is None:
            raise ValueError("cookie name must not be None")
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
        self.rfc2109 = rfc2109
        self._rest = dict(rest) if rest else {}

    def has_nonstandard_attr(self, name):
        return name in self._rest

    def get_nonstandard_attr(self, name, default=None):
        return self._rest.get(name, default)

    def set_nonstandard_attr(self, name, value):
        self._rest[name] = value

    def is_expired(self, now=None):
        if now is None:
            now = time.time()
        if self.expires is not None and self.expires <= now:
            return True
        return False

    def __repr__(self):
        return "Cookie(version=%r, name=%r, value=%r, domain=%r, path=%r)" % (
            self.version, self.name, self.value, self.domain, self.path)

    def __str__(self):
        if self.port is None:
            p = ""
        else:
            p = ":" + self.port
        limit = self.domain + p + self.path
        if self.value is None:
            namevalue = self.name
        else:
            namevalue = "%s=%s" % (self.name, self.value)
        return "<Cookie %s for %s>" % (namevalue, limit)


class CookiePolicy:
    """Base class for cookie policies."""

    def set_ok(self, cookie, request):
        raise NotImplementedError

    def return_ok(self, cookie, request):
        raise NotImplementedError

    def domain_return_ok(self, domain, request):
        return True

    def path_return_ok(self, path, request):
        return True


class DefaultCookiePolicy(CookiePolicy):
    """Default policy. Accepts and returns cookies under common rules."""

    DomainStrictNoDots = 1
    DomainStrictNonDomain = 2
    DomainRFC2965Match = 4
    DomainLiberal = 0
    DomainStrict = DomainStrictNoDots | DomainStrictNonDomain

    def __init__(self,
                 blocked_domains=None,
                 allowed_domains=None,
                 netscape=True,
                 rfc2965=False,
                 rfc2109_as_netscape=None,
                 hide_cookie2=False,
                 strict_domain=False,
                 strict_rfc2965_unverifiable=True,
                 strict_ns_unverifiable=False,
                 strict_ns_domain=DomainLiberal,
                 strict_ns_set_initial_dollar=False,
                 strict_ns_set_path=False,
                 secure_protocols=("https", "wss")):
        self.netscape = netscape
        self.rfc2965 = rfc2965
        self.rfc2109_as_netscape = rfc2109_as_netscape
        self.hide_cookie2 = hide_cookie2
        self.strict_domain = strict_domain
        self.strict_rfc2965_unverifiable = strict_rfc2965_unverifiable
        self.strict_ns_unverifiable = strict_ns_unverifiable
        self.strict_ns_domain = strict_ns_domain
        self.strict_ns_set_initial_dollar = strict_ns_set_initial_dollar
        self.strict_ns_set_path = strict_ns_set_path
        self.secure_protocols = secure_protocols
        self._blocked_domains = tuple(blocked_domains or ())
        self._allowed_domains = (
            tuple(allowed_domains) if allowed_domains is not None else None
        )

    def blocked_domains(self):
        return self._blocked_domains

    def set_blocked_domains(self, blocked_domains):
        self._blocked_domains = tuple(blocked_domains)

    def is_blocked(self, domain):
        for blocked in self._blocked_domains:
            if domain == blocked or domain.endswith("." + blocked):
                return True
        return False

    def allowed_domains(self):
        return self._allowed_domains

    def set_allowed_domains(self, allowed_domains):
        self._allowed_domains = (
            tuple(allowed_domains) if allowed_domains is not None else None
        )

    def is_not_allowed(self, domain):
        if self._allowed_domains is None:
            return False
        for allowed in self._allowed_domains:
            if domain == allowed or domain.endswith("." + allowed):
                return False
        return True

    def set_ok(self, cookie, request):
        if self.is_blocked(cookie.domain):
            return False
        if self.is_not_allowed(cookie.domain):
            return False
        return True

    def return_ok(self, cookie, request):
        if self.is_blocked(cookie.domain):
            return False
        if self.is_not_allowed(cookie.domain):
            return False
        if cookie.is_expired():
            return False
        return True


class CookieJar:
    """Collection of HTTP cookies."""

    def __init__(self, policy=None):
        if policy is None:
            policy = DefaultCookiePolicy()
        self._policy = policy
        # nested: domain -> path -> name -> Cookie
        self._cookies = {}

    def set_policy(self, policy):
        self._policy = policy

    def cookies_for_request(self, request):
        # Minimal placeholder; real implementation matches by domain/path.
        result = []
        for domain, paths in self._cookies.items():
            for path, names in paths.items():
                for name, cookie in names.items():
                    if not cookie.is_expired():
                        result.append(cookie)
        return result

    def set_cookie(self, cookie):
        if not isinstance(cookie, Cookie):
            raise TypeError("expected Cookie instance")
        domain = cookie.domain
        path = cookie.path
        name = cookie.name
        if domain not in self._cookies:
            self._cookies[domain] = {}
        if path not in self._cookies[domain]:
            self._cookies[domain][path] = {}
        self._cookies[domain][path][name] = cookie

    def set_cookie_if_ok(self, cookie, request):
        if self._policy.set_ok(cookie, request):
            self.set_cookie(cookie)

    def clear(self, domain=None, path=None, name=None):
        if domain is None:
            self._cookies = {}
            return
        if domain not in self._cookies:
            raise KeyError(domain)
        if path is None:
            del self._cookies[domain]
            return
        if path not in self._cookies[domain]:
            raise KeyError(path)
        if name is None:
            del self._cookies[domain][path]
            return
        if name not in self._cookies[domain][path]:
            raise KeyError(name)
        del self._cookies[domain][path][name]

    def clear_expired_cookies(self):
        now = time.time()
        for domain in list(self._cookies):
            for path in list(self._cookies[domain]):
                for name in list(self._cookies[domain][path]):
                    if self._cookies[domain][path][name].is_expired(now):
                        del self._cookies[domain][path][name]
                if not self._cookies[domain][path]:
                    del self._cookies[domain][path]
            if not self._cookies[domain]:
                del self._cookies[domain]

    def clear_session_cookies(self):
        for domain in list(self._cookies):
            for path in list(self._cookies[domain]):
                for name in list(self._cookies[domain][path]):
                    if self._cookies[domain][path][name].discard:
                        del self._cookies[domain][path][name]
                if not self._cookies[domain][path]:
                    del self._cookies[domain][path]
            if not self._cookies[domain]:
                del self._cookies[domain]

    def __iter__(self):
        for domain in self._cookies:
            for path in self._cookies[domain]:
                for name in self._cookies[domain][path]:
                    yield self._cookies[domain][path][name]

    def __len__(self):
        n = 0
        for domain in self._cookies:
            for path in self._cookies[domain]:
                n += len(self._cookies[domain][path])
        return n

    def __repr__(self):
        cookies = list(self)
        return "<%s[%s]>" % (
            self.__class__.__name__,
            ", ".join(repr(c) for c in cookies),
        )


class LoadError(IOError):
    pass


class FileCookieJar(CookieJar):
    """Base class for cookie jars that can be saved to / loaded from disk."""

    def __init__(self, filename=None, delayload=False, policy=None):
        super().__init__(policy)
        if filename is not None:
            filename = str(filename)
        self.filename = filename
        self.delayload = bool(delayload)

    def save(self, filename=None, ignore_discard=False, ignore_expires=False):
        raise NotImplementedError

    def load(self, filename=None, ignore_discard=False, ignore_expires=False):
        if filename is None:
            if self.filename is not None:
                filename = self.filename
            else:
                raise ValueError("no filename specified")
        with open(filename) as f:
            self._really_load(f, filename, ignore_discard, ignore_expires)

    def revert(self, filename=None, ignore_discard=False, ignore_expires=False):
        if filename is None:
            if self.filename is not None:
                filename = self.filename
            else:
                raise ValueError("no filename specified")
        old_state = self._cookies
        self._cookies = {}
        try:
            self.load(filename, ignore_discard, ignore_expires)
        except (LoadError, OSError):
            self._cookies = old_state
            raise

    def _really_load(self, f, filename, ignore_discard, ignore_expires):
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Invariant test functions
# ---------------------------------------------------------------------------

def cookiejar2_create():
    """A CookieJar can be created with a default policy."""
    jar = CookieJar()
    if not isinstance(jar._policy, DefaultCookiePolicy):
        return False
    if len(jar) != 0:
        return False
    custom = DefaultCookiePolicy(blocked_domains=("evil.example",))
    jar2 = CookieJar(policy=custom)
    if jar2._policy is not custom:
        return False
    if not custom.is_blocked("evil.example"):
        return False
    return True


def cookiejar2_cookie():
    """A Cookie can be constructed and exposes its attributes."""
    c = Cookie(
        version=0,
        name="session",
        value="abc123",
        domain="example.com",
        domain_specified=True,
        path="/",
        path_specified=True,
        secure=False,
        expires=int(time.time()) + 3600,
        discard=False,
    )
    if c.name != "session" or c.value != "abc123":
        return False
    if c.domain != "example.com" or c.path != "/":
        return False
    if c.is_expired(now=0):
        # current expiry is far in the future; not expired at epoch 0
        return False
    expired = Cookie(name="x", value="y", domain="d", path="/", expires=1)
    if not expired.is_expired():
        return False
    c.set_nonstandard_attr("HttpOnly", True)
    if not c.has_nonstandard_attr("HttpOnly"):
        return False
    if c.get_nonstandard_attr("HttpOnly") is not True:
        return False
    return True


def cookiejar2_set_cookie():
    """Cookies can be added, iterated, and cleared from a CookieJar."""
    jar = CookieJar()
    a = Cookie(name="a", value="1", domain="example.com", path="/")
    b = Cookie(name="b", value="2", domain="example.com", path="/api")
    c = Cookie(name="c", value="3", domain="other.example", path="/")
    jar.set_cookie(a)
    jar.set_cookie(b)
    jar.set_cookie(c)
    if len(jar) != 3:
        return False
    names = sorted(ck.name for ck in jar)
    if names != ["a", "b", "c"]:
        return False
    # Overwrite existing
    a2 = Cookie(name="a", value="updated", domain="example.com", path="/")
    jar.set_cookie(a2)
    if len(jar) != 3:
        return False
    found = None
    for ck in jar:
        if ck.name == "a":
            found = ck
            break
    if found is None or found.value != "updated":
        return False
    # Clear by domain/path/name
    jar.clear("example.com", "/api", "b")
    if len(jar) != 2:
        return False
    jar.clear("example.com")
    if len(jar) != 1:
        return False
    jar.clear()
    if len(jar) != 0:
        return False
    # set_cookie_if_ok with blocking policy
    policy = DefaultCookiePolicy(blocked_domains=("blocked.example",))
    jar2 = CookieJar(policy=policy)
    blocked = Cookie(name="x", value="y",
                     domain="blocked.example", path="/")
    jar2.set_cookie_if_ok(blocked, request=None)
    if len(jar2) != 0:
        return False
    allowed = Cookie(name="x", value="y", domain="ok.example", path="/")
    jar2.set_cookie_if_ok(allowed, request=None)
    if len(jar2) != 1:
        return False
    # TypeError on non-Cookie
    try:
        jar2.set_cookie("not a cookie")
    except TypeError:
        pass
    else:
        return False
    return True