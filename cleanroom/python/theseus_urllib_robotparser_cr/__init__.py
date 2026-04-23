"""
theseus_urllib_robotparser_cr — Clean-room urllib.robotparser module.
No import of the standard `urllib.robotparser` module.
"""

import re as _re
import time as _time
import urllib.request as _urllib_request
import urllib.parse as _urllib_parse


class RobotFileParser:
    """Reads and parses a robots.txt file."""

    def __init__(self, url=''):
        self.entries = []
        self.sitemaps = []
        self.default_entry = None
        self.disallow_all = False
        self.allow_all = False
        self.set_url(url)
        self.last_checked = 0

    def mtime(self):
        return self.last_checked

    def modified(self):
        self.last_checked = _time.time()

    def set_url(self, url):
        self.url = url
        self.host, self.path = _urllib_parse.urlparse(url)[1:3]

    def read(self):
        try:
            f = _urllib_request.urlopen(self.url)
        except _urllib_request.HTTPError as err:
            if err.code in (401, 403):
                self.disallow_all = True
            elif err.code >= 400 and err.code < 500:
                self.allow_all = True
            return
        raw = f.read()
        self.parse(raw.decode('utf-8', errors='replace').splitlines())

    def _add_entry(self, entry):
        if '*' in entry.useragents:
            if self.default_entry is None:
                self.default_entry = entry
        else:
            self.entries.append(entry)

    def parse(self, lines):
        """Parse the robots.txt file from lines."""
        state = 0
        entry = _Entry()

        self.modified()

        for line in lines:
            if not line:
                if state == 1:
                    entry = _Entry()
                    state = 0
                elif state == 2:
                    self._add_entry(entry)
                    entry = _Entry()
                    state = 0
                continue
            if line.strip().startswith('#'):
                continue
            i = line.find('#')
            if i >= 0:
                line = line[:i]
            line = line.strip()
            if not line:
                continue
            line = line.split(':', 1)
            if len(line) == 2:
                line[0] = line[0].strip().lower()
                line[1] = line[1].strip()
                if line[0] == 'user-agent':
                    if state == 2:
                        self._add_entry(entry)
                        entry = _Entry()
                    entry.useragents.append(line[1])
                    state = 1
                elif line[0] == 'disallow':
                    if state != 0:
                        entry.rulelines.append(_RuleLine(line[1], False))
                        state = 2
                elif line[0] == 'allow':
                    if state != 0:
                        entry.rulelines.append(_RuleLine(line[1], True))
                        state = 2
                elif line[0] == 'crawl-delay':
                    if state != 0:
                        try:
                            entry.delay = float(line[1])
                        except ValueError:
                            pass
                        state = 2
                elif line[0] == 'request-rate':
                    if state != 0:
                        numbers = line[1].split('/')
                        if len(numbers) == 2:
                            try:
                                entry.req_rate = _RequestRate(int(numbers[0]), int(numbers[1]))
                            except ValueError:
                                pass
                        state = 2
                elif line[0] == 'sitemap':
                    self.sitemaps.append(line[1])

        if state == 2:
            self._add_entry(entry)

    def can_fetch(self, useragent, url):
        """Return True if the given useragent can fetch the given URL."""
        if self.disallow_all:
            return False
        if self.allow_all:
            return True
        parsed_url = _urllib_parse.urlparse(_urllib_parse.unquote(url))
        url = parsed_url.path
        if parsed_url.query:
            url += '?' + parsed_url.query
        if not url:
            url = '/'
        for entry in self.entries:
            if entry.applies_to(useragent):
                return entry.allowance(url)
        if self.default_entry:
            return self.default_entry.allowance(url)
        return True

    def crawl_delay(self, useragent):
        for entry in self.entries:
            if entry.applies_to(useragent):
                return entry.delay
        if self.default_entry:
            return self.default_entry.delay
        return None

    def request_rate(self, useragent):
        for entry in self.entries:
            if entry.applies_to(useragent):
                return entry.req_rate
        if self.default_entry:
            return self.default_entry.req_rate
        return None

    def site_maps(self):
        return self.sitemaps if self.sitemaps else None

    def __str__(self):
        entries = self.entries
        if self.default_entry is not None:
            entries = entries + [self.default_entry]
        return '\n\n'.join(map(str, entries))


class _RequestRate:
    __slots__ = ['requests', 'seconds']

    def __init__(self, requests, seconds):
        self.requests = requests
        self.seconds = seconds

    def __repr__(self):
        return 'RequestRate(requests={}, seconds={})'.format(self.requests, self.seconds)


class _RuleLine:
    def __init__(self, path, allowance):
        if path == '' and not allowance:
            allowance = True
        self.path = _urllib_parse.quote(path)
        self.allowance = allowance

    def matches(self, path):
        return _re.match(_glob_to_pattern(self.path), path)

    def __str__(self):
        if self.allowance:
            return 'Allow: ' + self.path
        else:
            return 'Disallow: ' + self.path


def _glob_to_pattern(glob_path):
    i = 0
    n = len(glob_path)
    res = ''
    while i < n:
        c = glob_path[i]
        i += 1
        if c == '*':
            res += '.*'
        elif c == '$' and i == n:
            res += '$'
        else:
            res += _re.escape(c)
    return res


class _Entry:
    def __init__(self):
        self.useragents = []
        self.rulelines = []
        self.delay = None
        self.req_rate = None

    def __str__(self):
        ret = []
        for agent in self.useragents:
            ret.append('User-agent: ' + agent)
        for line in self.rulelines:
            ret.append(str(line))
        if self.delay is not None:
            ret.append('Crawl-delay: ' + str(self.delay))
        if self.req_rate is not None:
            ret.append('Request-rate: {}/{}'.format(self.req_rate.requests, self.req_rate.seconds))
        return '\n'.join(ret)

    def applies_to(self, useragent):
        ua = useragent.split('/')[0].lower()
        for agent in self.useragents:
            if agent == '*':
                return True
            if agent.lower() == ua:
                return True
        return False

    def allowance(self, filename):
        for line in self.rulelines:
            if line.matches(filename):
                return line.allowance
        return True


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def robotparser2_allow():
    """can_fetch returns True for allowed path; returns True."""
    parser = RobotFileParser()
    parser.parse(['User-agent: *', 'Disallow: /private/', 'Allow: /public/'])
    return parser.can_fetch('*', 'http://example.com/public/page')


def robotparser2_disallow():
    """can_fetch returns False for disallowed path; returns True."""
    parser = RobotFileParser()
    parser.parse(['User-agent: *', 'Disallow: /private/'])
    return not parser.can_fetch('*', 'http://example.com/private/data')


def robotparser2_wildcard():
    """wildcard user-agent applies to all agents; returns True."""
    parser = RobotFileParser()
    parser.parse(['User-agent: *', 'Disallow: /secret/'])
    return (not parser.can_fetch('Googlebot', 'http://example.com/secret/') and
            not parser.can_fetch('MyBot', 'http://example.com/secret/'))


__all__ = [
    'RobotFileParser',
    'robotparser2_allow', 'robotparser2_disallow', 'robotparser2_wildcard',
]
