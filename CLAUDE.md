# Veritas Index — Project Context

Read this fully before doing anything in this repo. It's the handoff
document from the session that built this project from nothing, and it
captures decisions and hard-won findings that aren't obvious from the
code alone.

## What this is

A curated, trust-vetted neural search index. Not a general web search
engine — a deliberately narrow one that only indexes sources vetted for
reputation, and is honest about which access method each source
actually permits rather than treating "get the content" as one uniform
problem.

## Why it exists

Two motivations, both real, both still active:

1. **A concrete need**: TruthGuard (the sibling project at
   `../truth_guard`) verifies WhatsApp-forward misinformation claims
   against evidence. Its coverage gap is claims no fact-checker has
   published on yet — those get stuck at UNVERIFIED with only Wikipedia
   as evidence. A broader, curated evidence index closes that gap. This
   project's `EvidenceKind.SEARCH` in TruthGuard's backend
   (`backend/app/models.py`) is a reserved, currently-empty slot
   waiting for exactly this.
2. **Learning by building, with a real product ambition attached**: the
   goal is to actually understand how retrieval systems like Tavily and
   Exa work — not by reading about them, but by building the real
   pieces and hitting the real problems they solve. The person driving
   this explicitly wants to understand the mechanics, and has said the
   longer-term ambition is a standalone, sellable product in that same
   space — differentiated by curation/quality over raw breadth. Treat
   that ambition as real and worth building toward, not just a learning
   exercise to be indulged. But also don't let "eventually sellable
   product" justify skipping rigor now — the discipline below is what
   makes either outcome (a real learning project, a real product)
   actually hold up.

## Non-negotiable principles

These came from real decisions made during the build, several of them
after explicitly rejecting a tempting shortcut. Don't relitigate them
without a real reason — if a new session forgets this and reaches for
the shortcut again, that's a regression, not a fresh idea:

1. **Respect each source's own access terms — always, no workarounds.**
   For crawlable sites: `robots.txt`, checked before every fetch, no
   exceptions. For everything else: use the source's own official API
   if one exists. **Never** scrape a search engine's results page,
   automate a browser against a consumer AI product's authenticated
   session, or build anything whose purpose is evading bot-detection.
   This isn't a gray area — Google's actual December 2025 DMCA lawsuit
   against SerpApi is the concrete outcome of ignoring it. Two related
   proposals were explicitly rejected during this project's build for
   exactly this reason (session-cookie proxying against ChatGPT/Claude/
   Perplexity; browser automation against Google/Bing search). If a
   future idea rhymes with either of those, it gets rejected the same
   way, not reconsidered because the framing changed.
2. **Official API beats crawling, every time one exists.** Wikipedia →
   its API (already true in TruthGuard). Research papers → arXiv,
   PubMed E-utilities, Semantic Scholar, CrossRef — never Google
   Scholar (no API, aggressive anti-scraping, same risk category as
   SerpApi). Historical page states → the Wayback Machine's API, not
   crawling publisher archives (which are usually paywalled by design).
   Check for an official API before writing a scraper, not after.
3. **Verify against real, live data before trusting an assumption.**
   Every module in this codebase was built this way, and it's not a
   style preference — it's what caught three real bugs that pure
   code review would have missed (see "Hard-won findings" below).
   Continue this discipline: when adding a new source or connector,
   check its actual `robots.txt`/API response for real before writing
   the integration, the same way Reuters' and Snopes' real files
   changed the plan mid-build.
4. **Curated over comprehensive.** The product thesis is a quality bar,
   not coverage. Don't add a source just because it's crawlable —
   evaluate whether it belongs on a "reputable, evidence-grade" list
   the same way a human editor would.

## Architecture

Three connector types, one shared pipeline. The real lesson from
building two connectors before generalizing: **don't force a common
fetch() verb** — crawling a known URL and searching a query are
genuinely different operations. What's actually shared is the *output
contract* (`ExtractedPage` + a `url`) and the ingestion step.

```
robots.py ─┐
           ├─→ fetcher.py ─→ extractor.py ─┐
crawler.py ─┘                              ├─→ ingest.py ─→ storage.py ─→ search
arxiv.py   ───────────────────────────────┤        ↑
wayback.py ─────────────────────────────────────────┘         embedder.py
```

- `robots.py` — permission checking. Caches one parsed `robots.txt` per
  domain. Identifies honestly as `VeritasIndexBot/0.1`.
- `fetcher.py` — per-domain rate-limited, honest-UA HTTP fetching.
- `extractor.py` — HTML → clean article text via `trafilatura`
  (the "Markdown Tax" problem — raw HTML is ~90% boilerplate).
- `storage.py` — SQLite, content-hash dedup, embeddings stored as
  packed-float BLOBs, brute-force cosine similarity search. Brute
  force is fine at this scale (low thousands of rows); a real vector
  index is a "when it's actually needed" problem, not a now problem.
- `embedder.py` — local `sentence-transformers` (`all-MiniLM-L6-v2`),
  free, CPU, no API dependency. Vectors are normalized so cosine
  similarity reduces to a dot product.
- `ingest.py` — the one shared step every connector funnels through:
  embed + dedup-aware store. This is the real "interface."
- `crawler.py` — HTML connector: robots-check → fetch → extract → ingest.
- `arxiv.py` — official arXiv API connector, same `ExtractedPage` output.
- `wayback.py` — Internet Archive Availability API connector. Stores
  results keyed by the **snapshot URL**, not the original URL — a
  deliberate decision: a historical snapshot and today's live version
  of the same URL are different artifacts representing different
  points in time, and collapsing them to one row would make history
  silently overwrite the present (or vice versa).
- `seed.py` / `scripts/run_seed.py` — batch runner driven by
  `sources.yaml`. Only `crawl` and `arxiv` sources belong in that
  config — they're proactive "keep this corpus fresh" operations.
  `wayback` is deliberately NOT there: it's an on-demand, "what did
  this specific page say at this specific time" lookup triggered by a
  real need, not something to routinely re-run on a schedule.

## Hard-won findings — don't rediscover these from scratch

Real, current (as of 2026-07-24), specific facts about real sources,
found by actually checking rather than assuming:

- **Reuters' `robots.txt`** (`User-agent: *` → `Disallow: /`, with
  named partners like Googlebot allowlisted) is direct, concrete
  evidence for *why* Tavily-style services license search indexes
  instead of crawling news sites directly — Reuters explicitly permits
  only specific named partners, not generic crawlers.
- **Politifact and BOOM Live** return `HTTP 403` to an honest crawler
  User-Agent before `robots.txt` is even readable (Cloudflare
  bot-protection). Don't try to work around this. Both are already
  covered through TruthGuard's Fact Check Tools API integration, which
  is the correct alternate path, not a crawler workaround.
- **BBC, AP News, Snopes, FactCheck.org, Alt News, Wikipedia, gov.uk**
  are all real, currently crawlable with an honest identity.
- **Snopes' `Content-Signal: search=yes,ai-train=no`** — a real, current
  robots.txt extension distinguishing "index for search" (granted) from
  "train a model on this" (denied). This project only ever does the
  former. If anything resembling model training on crawled content is
  ever proposed, that's a different permission most sources are
  actively withholding — treat it as a hard stop pending real
  per-source review, not a formality.
- **SQLite schema migrations aren't automatic.**
  `CREATE TABLE IF NOT EXISTS` only helps a brand-new database — an
  existing one needs explicit `ALTER TABLE` handling (see `_migrate()`
  in `storage.py`). Same category of problem TruthGuard's Room database
  solves with `AutoMigration` — expect it again for any future schema
  change here.
- **"Content unchanged" ≠ "field already computed."** The dedup fast
  path (`UpsertResult.UNCHANGED`) originally skipped rows whose content
  hash matched but which predated a newly-added column (`embedding`),
  silently leaving them permanently unsearchable. Fixed by checking
  whether the derived field is actually populated, not just whether the
  hash matches. Watch for this exact shape of bug with any future new
  derived column.
- **Wayback's Availability API matching is scheme-sensitive** —
  querying with a full `https://...` URL only matched when a timestamp
  was also given; querying with a bare `domain/path` (no scheme) worked
  reliably in every case tested. `wayback.py` normalizes to the bare
  form before querying. This isn't documented anywhere obvious — it was
  found by testing all four combinations directly.

## Current state

First two commits: `fa86b92` (the full working pipeline — crawler,
arXiv, Wayback, unified ingest/search) and `71bc75b` (README). Proven
live: 14 stored pages across 4 real sources, cross-source semantic
search correctly ranking by meaning (a paraphrased query about "foreign
interference with voting systems" correctly scored a Venezuela/CIA
election article at 0.48 vs. an unrelated Delhi protest article at
0.02 — real discrimination, not luck).

No GitHub remote yet — local-only. `.venv/` and `data/*.db` are
gitignored; everything else is tracked.

To run things: `.venv/Scripts/python scripts/run_seed.py` runs the full
configured batch (`sources.yaml`). Individual pipeline pieces have
proof-of-concept scripts under `tests/demo_*.py` (not real pytest tests
yet — that's still to build).

## How to work on this project

This was built lesson-by-lesson, teaching-as-we-go, deliberately slower
than "just write the finished code": explain the concept, write the
smallest real working piece, run it against live data, only then move
on. That pace is a stated preference, not an artifact of this being new
— keep working this way unless told otherwise. Concretely: before
writing a connector or fixing a bug, check the real behavior (a live
`robots.txt`, a real API response, an actual error) rather than
assuming it from documentation or prior knowledge — every real bug
found in this project so far was caught exactly because of that habit.

## Not yet built (real roadmap, not aspirational)

- Sitemap-based URL discovery (grow crawl targets automatically instead
  of one hand-picked URL at a time)
- More research connectors: PubMed E-utilities, Semantic Scholar,
  CrossRef (same pattern as `arxiv.py`)
- Wrapping this as an HTTP service TruthGuard's backend (or anything
  else) can actually query
- A GitHub remote
- Real pytest test suite (the `tests/demo_*.py` scripts are proofs of
  concept, not a real test suite)
- A real vector index, if/when brute-force cosine similarity actually
  becomes a bottleneck (not before)
