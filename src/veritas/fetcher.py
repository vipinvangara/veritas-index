"""Respectful HTTP fetching — the second gate, after robots.txt.

Passing the robots.txt check means a site *permits* crawling in general.
It doesn't mean we should hit it as fast as our network allows. Two
things this module enforces regardless of what any single request
"could" do:

1. A per-domain minimum delay between requests, so a crawl of many pages
   on one site is spread out rather than fired in a burst. We honor a
   site's own Crawl-delay from robots.txt if it specifies one, and fall
   back to a conservative default otherwise.
2. A real timeout, so one slow/hanging server can't stall the whole
   crawl.

We identify with the same honest User-Agent as robots.py — a fetch that
robots.txt would have allowed for "VeritasIndexBot" but that we then
made pretending to be a browser would defeat the entire point of
checking robots.txt in the first place.
"""

import time

import httpx

from .robots import USER_AGENT, RobotsChecker

DEFAULT_MIN_DELAY_SECONDS = 3.0
TIMEOUT_SECONDS = 10.0


class Fetcher:
    def __init__(self, robots: RobotsChecker) -> None:
        self._robots = robots
        self._last_fetch_at: dict[str, float] = {}
        self._client = httpx.Client(
            headers={"User-Agent": USER_AGENT},
            timeout=TIMEOUT_SECONDS,
            follow_redirects=True,
        )

    def _wait_for_domain(self, url: str) -> None:
        domain = httpx.URL(url).host
        delay = self._robots.crawl_delay(url) or DEFAULT_MIN_DELAY_SECONDS
        last = self._last_fetch_at.get(domain)
        if last is not None:
            elapsed = time.monotonic() - last
            remaining = delay - elapsed
            if remaining > 0:
                time.sleep(remaining)
        self._last_fetch_at[domain] = time.monotonic()

    def fetch(self, url: str) -> str | None:
        """Returns the page's HTML, or None if robots.txt disallows it or
        the request fails. Never raises for an ordinary HTTP error — a
        crawl of many pages should skip a broken one, not abort.
        """
        if not self._robots.can_fetch(url):
            return None

        self._wait_for_domain(url)

        try:
            response = self._client.get(url)
            response.raise_for_status()
        except httpx.HTTPError:
            return None

        return response.text

    def close(self) -> None:
        self._client.close()
