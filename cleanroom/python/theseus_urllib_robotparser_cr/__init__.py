"""Clean-room implementation of urllib.robotparser.

Implements RobotFileParser without using urllib.robotparser or any third-party
libraries. URL parsing is done manually.
"""

import re
import time


__all__ = [
    "RobotFileParser",
    "RuleLine",
    "Entry",
    "robotparser2_allow",
    "robotparser2_disallow",
    "robotparser2_wildcard",
]


def _unquote(s):
    """Minimal percent-decoder for paths."""
    if "%" not in s:
        return s
    out = []
    i = 0
    n = len(s)
    while i < n:
        c = s[i]
        if c == "%" and i + 2 < n:
            try:
                out.append(chr(int(s[i + 1:i + 3], 16)))
                i += 3
                continue
            except ValueError:
                pass
        out.append(c)
        i += 1
    return "".join(out)


def _split_url(url):
    """Return (scheme, host, path) for a URL string. Manual parser."""
    scheme = ""
    rest = url
    if "://" in rest:
        scheme, rest = rest.split("://", 1)
    # Strip query/fragment from rest for path determination
    # Find first '/' which separates host and path
    if "/" in rest:
        host, path = rest.split("/", 1)
        path = "/" + path
    else:
        host = rest
        path = ""
    if not path:
        path = "/"
    # Trim fragment
    if "#" in path:
        path = path.split("#", 1)[0]
    return scheme, host, path


def _pattern_to_regex(pattern):
    """Convert a robots.txt path pattern (with '*' and trailing '$')
    to a compiled regular expression that anchors at the start."""
    parts = ["^"]
    n = len(pattern)
    i = 0
    while i < n:
        c = pattern[i]
        if c == "*":
            parts.append(".*")
        elif c == "$" and i == n - 1:
            parts.append("$")
        else:
            parts.append(re.escape(c))
        i += 1
    return re.compile("".join(parts))


class RuleLine:
    """A single Allow/Disallow rule paired with its path pattern."""

    def __init__(self, path, allowance):
        if path == "" and not allowance:
            # An empty Disallow means "allow everything".
            allowance = True
        path = _unquote(path)
        self.path = path
        self.allowance = bool(allowance)
        self._regex = _pattern_to_regex(path) if path else None

    def applies_to(self, filename):
        if self.path == "*":
            return True
        if not self.path:
            # Empty path was rewritten to allowance=True; matches everything.
            return True
        return self._regex.match(filename) is not None

    def __str__(self):
        return ("Allow" if self.allowance else "Disallow") + ": " + self.path


class Entry:
    """A group of rules for one or more user-agents."""

    def __init__(self):
        self.useragents = []
        self.rulelines = []
        self.delay = None
        self.req_rate = None

    def applies_to(self, useragent):
        useragent = useragent.split("/")[0].lower()
        for agent in self.useragents:
            if agent == "*":
                return True
            if agent.lower() in useragent:
                return True
        return False

    def allowance(self, filename):
        for line in self.rulelines:
            if line.applies_to(filename):
                return line.allowance
        return True

    def __str__(self):
        ua_lines = ["User-agent: " + a for a in self.useragents]
        rules = [str(r) for r in self.rulelines]
        return "\n".join(ua_lines + rules)


class RobotFileParser:
    """Parses robots.txt content and answers can_fetch queries."""

    def __init__(self, url=""):
        self.entries = []
        self.sitemaps = []
        self.default_entry = None
        self.disallow_all = False
        self.allow_all = False
        self.last_checked = 0
        self.url = ""
        self.host = ""
        self.path = ""
        self.set_url(url)

    def mtime(self):
        return self.last_checked

    def modified(self):
        self.last_checked = time.time()

    def set_url(self, url):
        self.url = url or ""
        if url:
            _, self.host, self.path = _split_url(url)
        else:
            self.host = ""
            self.path = ""

    def read(self):
        # Network reading is intentionally not supported in this clean-room
        # implementation; consumers feed lines via parse() directly.
        raise NotImplementedError(
            "RobotFileParser.read() is not supported in this clean-room build; "
            "use parse(lines) instead."
        )

    def _add_entry(self, entry):
        if "*" in entry.useragents:
            if self.default_entry is None:
                self.default_entry = entry
        else:
            self.entries.append(entry)

    def parse(self, lines):
        """Parse an iterable of robots.txt lines."""
        state = 0  # 0=between entries, 1=saw UA, 2=saw rules
        entry = Entry()
        self.modified()

        for raw in lines:
            line = raw

            # Blank lines separate entries.
            stripped_for_blank = line.strip() if line is not None else ""
            if not stripped_for_blank:
                if state == 1:
                    entry = Entry()
                    state = 0
                elif state == 2:
                    self._add_entry(entry)
                    entry = Entry()
                    state = 0
                continue

            # Strip comments.
            hash_pos = line.find("#")
            if hash_pos >= 0:
                line = line[:hash_pos]
            line = line.strip()
            if not line:
                continue

            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            key = key.strip().lower()
            value = value.strip()

            if key == "user-agent":
                if state == 2:
                    self._add_entry(entry)
                    entry = Entry()
                entry.useragents.append(value)
                state = 1
            elif key == "disallow":
                if state != 0:
                    entry.rulelines.append(RuleLine(value, False))
                    state = 2
            elif key == "allow":
                if state != 0:
                    entry.rulelines.append(RuleLine(value, True))
                    state = 2
            elif key == "crawl-delay":
                if state != 0:
                    try:
                        entry.delay = int(value)
                    except ValueError:
                        try:
                            entry.delay = float(value)
                        except ValueError:
                            pass
                    state = 2
            elif key == "request-rate":
                if state != 0:
                    try:
                        nums = value.split("/", 1)
                        if len(nums) == 2:
                            req = int(nums[0])
                            sec = int(nums[1])
                            entry.req_rate = (req, sec)
                    except ValueError:
                        pass
                    state = 2
            elif key == "sitemap":
                self.sitemaps.append(value)

        if state in (1, 2):
            self._add_entry(entry)

    def can_fetch(self, useragent, url):
        """Return True if `useragent` is allowed to fetch `url`."""
        if self.disallow_all:
            return False
        if self.allow_all:
            return True
        if not self.last_checked:
            return False

        # Extract a path from the URL. Empty path means "/".
        if not url:
            path = "/"
        else:
            _, _, path = _split_url(url)
            if not path:
                path = "/"

        path = _unquote(path)

        for entry in self.entries:
            if entry.applies_to(useragent):
                return entry.allowance(path)

        if self.default_entry is not None:
            return self.default_entry.allowance(path)

        return True

    def crawl_delay(self, useragent):
        if not self.mtime():
            return None
        for entry in self.entries:
            if entry.applies_to(useragent):
                return entry.delay
        if self.default_entry is not None:
            return self.default_entry.delay
        return None

    def request_rate(self, useragent):
        if not self.mtime():
            return None
        for entry in self.entries:
            if entry.applies_to(useragent):
                return entry.req_rate
        if self.default_entry is not None:
            return self.default_entry.req_rate
        return None

    def site_maps(self):
        if not self.sitemaps:
            return None
        return list(self.sitemaps)

    def __str__(self):
        parts = []
        for entry in self.entries:
            parts.append(str(entry))
        if self.default_entry is not None:
            parts.append(str(self.default_entry))
        return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# Invariant test functions
# ---------------------------------------------------------------------------

def robotparser2_allow():
    """An explicit Allow rule must override a broader Disallow."""
    rp = RobotFileParser()
    rp.parse([
        "User-agent: *",
        "Allow: /public/",
        "Disallow: /",
    ])
    allowed_public = rp.can_fetch("*", "http://example.com/public/page.html")
    blocked_root = rp.can_fetch("*", "http://example.com/private.html")
    return bool(allowed_public) and (blocked_root is False)


def robotparser2_disallow():
    """A Disallow rule must block matching paths and leave others open."""
    rp = RobotFileParser()
    rp.parse([
        "User-agent: *",
        "Disallow: /private/",
    ])
    blocked = rp.can_fetch("*", "http://example.com/private/secret.html")
    open_path = rp.can_fetch("*", "http://example.com/index.html")
    return (blocked is False) and (open_path is True)


def robotparser2_wildcard():
    """A '*' User-agent group must apply to every specific bot, and
    pattern wildcards ('*' and trailing '$') must work in paths."""
    rp = RobotFileParser()
    rp.parse([
        "User-agent: *",
        "Disallow: /*.pdf$",
        "Disallow: /tmp/",
    ])
    pdf_blocked = rp.can_fetch("MyBot", "http://example.com/files/report.pdf")
    tmp_blocked = rp.can_fetch("OtherBot", "http://example.com/tmp/x.txt")
    html_ok = rp.can_fetch("MyBot", "http://example.com/files/report.html")
    pdf_with_query_ok = rp.can_fetch(
        "MyBot", "http://example.com/files/report.pdf.bak"
    )
    return (
        (pdf_blocked is False)
        and (tmp_blocked is False)
        and (html_ok is True)
        and (pdf_with_query_ok is True)
    )