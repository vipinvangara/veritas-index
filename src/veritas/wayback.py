"""Internet Archive Wayback Machine connector — for "what did this page
say at a point in time," which live crawling fundamentally can't answer.
Publisher archives are usually paywalled precisely because they
monetize this; the Wayback Machine is Archive.org's own free, official,
mission-aligned API for it.

Storage key is deliberately the *snapshot* URL (web.archive.org/web/
{timestamp}/{original}), not the original URL. A snapshot from a year
ago and today's live-crawled version of the same URL are different
artifacts representing different points in time — collapsing them to
one storage row under the original URL would silently make history
overwrite the present (or vice versa), which defeats the entire point
of archival access.

Rate limiting note: unlike arXiv, the Internet Archive doesn't publish a
specific documented per-request limit for this endpoint that we found.
Rather than assume "no limit," we default to the same conservative delay
the web crawler uses elsewhere in this project — treating unknown as
"be careful," not as "anything goes."
"""

import time
from dataclasses import dataclass

import httpx

from .extractor import ExtractedPage, extract

AVAILABILITY_API = "https://archive.org/wayback/available"
DEFAULT_DELAY_SECONDS = 3.0

_last_request_at: float | None = None


@dataclass
class WaybackResult:
    snapshot_url: str
    original_url: str
    timestamp: str
    page: ExtractedPage


def _wait() -> None:
    global _last_request_at
    if _last_request_at is not None:
        remaining = DEFAULT_DELAY_SECONDS - (time.monotonic() - _last_request_at)
        if remaining > 0:
            time.sleep(remaining)
    _last_request_at = time.monotonic()


def find_snapshot(url: str, timestamp: str | None = None) -> tuple[str, str] | None:
    """Returns (snapshot_url, snapshot_timestamp) for the closest archived
    capture of `url`, or None if nothing's archived. `timestamp`
    (YYYYMMDD or more precise) asks for the closest capture to that date;
    omitted, the API returns its most recent capture.
    """
    # The Availability API's matching is inconsistent about URL scheme: a
    # bare "domain/path" (no https://) matches reliably in every case we
    # tested; the full https:// form only matched when a timestamp was
    # also given, and silently returned nothing otherwise. Stripping the
    # scheme before querying avoids depending on that undocumented
    # asymmetry.
    bare_url = url.removeprefix("https://").removeprefix("http://")
    params = {"url": bare_url}
    if timestamp:
        params["timestamp"] = timestamp

    _wait()
    response = httpx.get(AVAILABILITY_API, params=params, timeout=10.0)
    response.raise_for_status()
    data = response.json()

    closest = data.get("archived_snapshots", {}).get("closest")
    if not closest or not closest.get("available"):
        return None

    return closest["url"], closest["timestamp"]


def fetch_snapshot(url: str, timestamp: str | None = None) -> WaybackResult | None:
    found = find_snapshot(url, timestamp)
    if found is None:
        return None
    snapshot_url, snapshot_timestamp = found

    _wait()
    response = httpx.get(snapshot_url, timeout=10.0, follow_redirects=True)
    if response.status_code != 200:
        return None

    page = extract(response.text, url)
    if page is None:
        return None

    return WaybackResult(
        snapshot_url=snapshot_url,
        original_url=url,
        timestamp=snapshot_timestamp,
        page=page,
    )
