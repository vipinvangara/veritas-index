"""robots.txt compliance — the first gate every fetch must pass through.

Every site can publish rules at /robots.txt saying which automated agents
may access which paths, keyed by User-agent. We identify ourselves
honestly (see USER_AGENT below) rather than pretending to be a browser —
a site owner who wants to see who's crawling them and block/allow
accordingly can only do that if we're truthful about who we are.

robots.txt is a voluntary-compliance contract, not a technical barrier —
nothing stops us from ignoring it. We don't, on principle: it's the
mechanism site owners use to control access, and respecting it is what
keeps this a legitimate crawler instead of a scraper working around
site owners' wishes.
"""

from urllib import robotparser
from urllib.parse import urlparse

USER_AGENT = "VeritasIndexBot/0.1 (+https://github.com/vipinvangara/veritas-index)"


class RobotsChecker:
    """Caches one parsed robots.txt per domain so we don't re-fetch it on
    every single page check — robots.txt itself is small and rarely
    changes, but forgetting to cache it would mean doubling every request
    we make, which is exactly the kind of unnecessary load a respectful
    crawler avoids.
    """

    def __init__(self) -> None:
        self._parsers: dict[str, robotparser.RobotFileParser] = {}

    def _parser_for(self, url: str) -> robotparser.RobotFileParser:
        domain = urlparse(url).netloc
        if domain not in self._parsers:
            parser = robotparser.RobotFileParser()
            parser.set_url(f"https://{domain}/robots.txt")
            parser.read()
            self._parsers[domain] = parser
        return self._parsers[domain]

    def can_fetch(self, url: str) -> bool:
        return self._parser_for(url).can_fetch(USER_AGENT, url)

    def crawl_delay(self, url: str) -> float | None:
        domain = urlparse(url).netloc
        parser = self._parsers.get(domain)
        return parser.crawl_delay(USER_AGENT) if parser else None
