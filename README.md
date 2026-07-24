# Veritas Index

A curated, trust-vetted neural search index — built from scratch, source
by source, as both a learning project and a real prototype for a
sellable product in the Tavily/Exa space, but differentiated by
*quality over breadth*: every source is vetted for reputation, not
crawled indiscriminately.

## Why

Two motivations converged:

1. **TruthGuard** (the sibling project this grew out of) has a real
   coverage gap — claims that no fact-checker has covered yet get stuck
   at UNVERIFIED with only Wikipedia evidence. A broader, curated
   evidence index closes that gap.
2. **Learning by building** — understanding how retrieval systems like
   Tavily and Exa actually work (and don't work) by building the real
   pieces, not reading about them. Every lesson below was built and
   verified against live data, not assumed.

The "index of truth" framing is admittedly ambitious for where this is
today, but the differentiation logic is real: general web search
indexes everything and ranks by relevance; this indexes a deliberately
curated set of reputable sources and doesn't try to be anything broader.

## How it works

Three source types, each accessed the way its *own* source actually
permits — this was a deliberate, hard-won lesson, not a default:

| Source type | Access method | Why |
|---|---|---|
| News / fact-check sites | `robots.txt`-respecting HTML crawl (`crawler.py`) | Most permit it; some (Politifact, BOOM Live) don't and are correctly skipped, not worked around |
| Research papers | Official arXiv API (`arxiv.py`) | Structured, free, no scraping needed — official APIs beat crawling wherever they exist (same logic extends to PubMed, Semantic Scholar, CrossRef, not yet built) |
| Historical/archival pages | Internet Archive's Wayback Machine API (`wayback.py`) | Point-in-time lookups that live crawling fundamentally can't answer; publisher archives are usually paywalled by design |

All three funnel through one shared step (`ingest.py`): embed the
content locally (`embedder.py`, `sentence-transformers`, free, CPU,
no API cost) and store it with change-detection dedup (`storage.py`,
SQLite, content-hash based). Search (`storage.search`) is brute-force
cosine similarity over stored embeddings — genuinely fine at this
scale (low thousands of rows), a real vector database only earns its
complexity much further down the road.

```
robots.py ─┐
           ├─→ fetcher.py ─→ extractor.py ─┐
crawler.py ─┘                              ├─→ ingest.py ─→ storage.py ─→ search
arxiv.py   ───────────────────────────────┤        ↑
wayback.py ─────────────────────────────────────────┘         embedder.py
```

`sources.yaml` + `scripts/run_seed.py` run every configured crawl
target and arXiv query in one batch — the real entrypoint, replacing
the one-off demo scripts under `tests/` that each lesson was proven
against individually.

## What we actually found building it (not assumed)

Every lesson was checked against live sources, and it surfaced real,
non-obvious things:

- **Reuters' `robots.txt`** explicitly blocks generic crawlers
  (`Disallow: /` for `User-agent: *`) while allowlisting named partners
  — concrete evidence for *why* services like Tavily license search
  indexes instead of crawling news sites directly.
- **Politifact and BOOM Live** return `HTTP 403` to an honestly-identified
  crawler before `robots.txt` is even read (Cloudflare bot-protection) —
  handled by skipping them, not working around the block. Both are
  already covered through TruthGuard's Fact Check Tools integration
  anyway.
- **Snopes' `Content-Signal: search=yes,ai-train=no`** — a real,
  current robots.txt extension distinguishing "index for search" from
  "train a model on this," which matters directly: this project builds
  a search index, not training data, so it's squarely inside what's
  granted.
- A **SQLite schema migration gap** — adding the `embedding` column to
  `SCHEMA` didn't touch the database already on disk from an earlier
  lesson; fixed with an explicit migration check.
- An **embedding-backfill bug** — the `UNCHANGED` dedup fast path
  skipped rows whose content hadn't changed but which *predated* the
  embedding column entirely, silently making them invisible to search.
  Fixed by separating "content changed" from "field populated."
- An **undocumented Wayback API quirk** — the Availability API matches
  inconsistently depending on whether the queried URL includes
  `https://`; fixed by normalizing to a bare `domain/path` form, which
  worked reliably in every case tested.

## Current state

Proven working end to end: 14 stored pages across 4 real sources (2
crawled fact-check articles, 3 arXiv papers now 10 after later runs,
2 Wayback snapshots of the same page 2 years apart, correctly stored
as distinct artifacts rather than one overwriting the other). Cross-source
semantic search correctly ranks results by meaning, not keyword overlap,
across all source types in one query.

First commit: `fa86b92`.

## Not yet built

- Sitemap-based URL discovery (grow the crawl list automatically
  instead of hand-picked URLs)
- Additional connectors: PubMed/Semantic Scholar/CrossRef (research),
  encyclopedia sources beyond Wikipedia (already covered via TruthGuard's
  own Wikipedia API integration, not duplicated here)
- Wrapping this as an actual HTTP service TruthGuard's backend (or
  anyone else) could query
- A GitHub remote — this only exists as a local repo so far
- A real vector index (once/if scale ever justifies it over brute-force
  cosine similarity)
