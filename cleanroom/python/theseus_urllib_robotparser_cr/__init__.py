"""Clean-room urllib.robotparser subset for Theseus invariants."""


def _path_from_url(url):
    if "://" in url:
        rest = url.split("://", 1)[1]
        slash = rest.find("/")
        return "/" if slash == -1 else rest[slash:]
    return url or "/"


class RobotFileParser:
    def __init__(self, url=""):
        self.url = url
        self._rules = []
        self._agents = []

    def parse(self, lines):
        current_agents = []
        for raw in lines:
            line = raw.strip()
            if not line or ":" not in line:
                continue
            key, value = [p.strip() for p in line.split(":", 1)]
            key = key.lower()
            if key == "user-agent":
                current_agents = [value.lower()]
            elif key in ("allow", "disallow"):
                for agent in current_agents or ["*"]:
                    self._rules.append((agent, key == "allow", value or "/"))

    def can_fetch(self, useragent, url):
        agent = (useragent or "*").lower()
        path = _path_from_url(url)
        best = None
        for rule_agent, allow, rule_path in self._rules:
            if rule_agent not in ("*", agent):
                continue
            if path.startswith(rule_path):
                if best is None or len(rule_path) >= len(best[2]):
                    best = (rule_agent, allow, rule_path)
        return True if best is None else best[1]


def robotparser2_allow():
    parser = RobotFileParser()
    parser.parse(["User-agent: *", "Disallow: /private/", "Allow: /public/"])
    return parser.can_fetch("*", "http://example.com/public/page")


def robotparser2_disallow():
    parser = RobotFileParser()
    parser.parse(["User-agent: *", "Disallow: /private/"])
    return not parser.can_fetch("*", "http://example.com/private/data")


def robotparser2_wildcard():
    parser = RobotFileParser()
    parser.parse(["User-agent: *", "Disallow: /secret/"])
    return not parser.can_fetch("Googlebot", "http://example.com/secret/") and not parser.can_fetch("MyBot", "http://example.com/secret/")


__all__ = ["RobotFileParser", "robotparser2_allow", "robotparser2_disallow", "robotparser2_wildcard"]
