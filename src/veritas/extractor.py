"""HTML -> clean article text. This is the "Markdown Tax" problem: a raw
news page is mostly navigation, ads, cookie banners, and related-article
widgets, not the article itself. trafilatura implements the actual
research-grade approach to this (density/boilerplate heuristics honed
against real news sites), which is why we reach for it instead of a
naive "strip HTML tags" pass — a naive strip still leaves nav-menu text
and footer boilerplate sitting in the output, indistinguishable from the
real article to anything reading it downstream.
"""

from dataclasses import dataclass

import trafilatura


@dataclass
class ExtractedPage:
    title: str | None
    text: str
    author: str | None
    date: str | None


def extract(html: str, url: str) -> ExtractedPage | None:
    metadata = trafilatura.extract_metadata(html, default_url=url)
    text = trafilatura.extract(html, url=url, favor_recall=False)

    if not text:
        return None

    return ExtractedPage(
        title=metadata.title if metadata else None,
        text=text,
        author=metadata.author if metadata else None,
        date=metadata.date if metadata else None,
    )
