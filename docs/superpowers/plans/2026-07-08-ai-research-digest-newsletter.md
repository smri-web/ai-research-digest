# AI Research Digest Weekly Newsletter — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A hands-off weekly newsletter that fetches recent AI/tech papers and articles, summarizes them with Claude, publishes a web page + archive to GitHub Pages, and emails subscribers via Buttondown — all on a GitHub Actions schedule.

**Architecture:** A linear pipeline of small, single-responsibility modules (fetch → dedupe → skip-seen → filter → rank → summarize → render → deliver → commit). Pure-logic modules (dedupe, filter, rank, render, state) are unit-tested; I/O modules (sources, Claude, Buttondown) are thin and exercised via a manual dry-run. `main.py` wires them together.

**Tech Stack:** Python 3.11+, `requests`, `feedparser`, `anthropic`, `python-dotenv`, `pytest` (dev only), GitHub Actions, GitHub Pages, Buttondown API.

## Global Constraints

- Python 3.11+ (uses `X | None` types, `datetime.UTC`).
- Approved dependencies only: `requests`, `feedparser`, `anthropic`, `python-dotenv`. Ask before adding others. `pytest` is dev-only.
- Summary style: short direct sentences, no filler, **no em-dashes**, no emojis, no hype adjectives ("groundbreaking", "revolutionary"), plain language over jargon.
- API keys from environment only, never hardcoded. Local `.env` is git-ignored.
- Model id: `claude-haiku-4-5-20251001` (one config constant).
- Cap the digest at 10 items total; only items published within the last 7 days.
- Owner is a product marketer — keep code readable and commit messages plain.

---

## File Structure

```
config.py                     tracks, arXiv queries, S2 keywords, RSS feeds, model id, constants
models.py                     Item dataclass + Summary dataclass (shared shapes)
state.py                      read/write processed_ids.json
sources/__init__.py
sources/arxiv.py              fetch + parse arXiv
sources/semantic_scholar.py   fetch via Semantic Scholar API
sources/rss.py                fetch any RSS/Atom feed, tag with track
dedupe.py                     cross-source dedupe by DOI/arXiv id / URL
filtering.py                  7-day window, AI/tech relevance, skip-rules
ranking.py                    relevance + recency score, citation tiebreak, per-source cap, top 10
summarize.py                  Claude call -> Summary
render.py                     markdown + digest HTML page + index + archive + email HTML
delivery.py                   Buttondown API client
main.py                       orchestrates the pipeline; supports --dry-run
.github/workflows/weekly-digest.yml
requirements.txt
.env.example
README.md                     setup walkthrough
tests/                        pytest unit tests for pure-logic modules
```

---

### Task 1: Project scaffold and config

**Files:**
- Create: `requirements.txt`, `.env.example`, `config.py`, `models.py`, `sources/__init__.py`, `tests/__init__.py`

**Interfaces:**
- Produces: `models.Item` dataclass, `models.Summary` dataclass; `config.TRACKS`, `config.RSS_FEEDS`, `config.MODEL_ID`, `config.MAX_ITEMS = 10`, `config.WINDOW_DAYS = 7`, `config.PER_SOURCE_CAP = 3`.

- [ ] **Step 1: Create `requirements.txt`**

```
requests>=2.31
feedparser>=6.0
anthropic>=0.40
python-dotenv>=1.0
```

- [ ] **Step 2: Create `.env.example`**

```
ANTHROPIC_API_KEY=sk-ant-...
BUTTONDOWN_API_KEY=...
# Your published site base, used to build "full breakdown" links in the email:
SITE_BASE_URL=https://YOUR_GITHUB_USERNAME.github.io/ai-research-digest
```

- [ ] **Step 3: Create `models.py`**

```python
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Item:
    id: str                      # arXiv id, DOI, or canonical URL
    title: str
    authors: list[str]
    source: str                  # "arXiv", "Semantic Scholar", "Simon Willison", ...
    url: str
    published: datetime          # timezone-aware, UTC
    text: str                    # abstract (papers) or excerpt (articles)
    track: str                   # a key from config.TRACKS
    content_type: str            # "paper" | "article"
    citation_count: int | None = None

    def slug(self) -> str:
        """URL-safe anchor id for this item, e.g. 'item-attention-is-all-you-need'."""
        import re
        base = re.sub(r"[^a-z0-9]+", "-", self.title.lower()).strip("-")
        return "item-" + base[:60].strip("-")


@dataclass
class Summary:
    beats: dict[str, str]        # ordered 3-part summary, label -> text
    breakdown: str               # longer plain-language explanation
```

- [ ] **Step 4: Create `config.py`** (queries copied verbatim from project instructions)

```python
MODEL_ID = "claude-haiku-4-5-20251001"
MAX_ITEMS = 10
WINDOW_DAYS = 7
PER_SOURCE_CAP = 3
PROCESSED_IDS_PATH = "processed_ids.json"

# Each track: display name, arXiv query, Semantic Scholar keywords, relevance keywords.
TRACKS = {
    "models": {
        "name": "AI models & research",
        "arxiv": '(cat:cs.AI OR cat:cs.CL OR cat:cs.LG) AND (abs:"large language model" OR abs:"foundation model" OR abs:"reasoning model" OR abs:"multimodal model")',
        "s2": ["large language models", "frontier AI models"],
        "keywords": ["language model", "foundation model", "reasoning", "multimodal", "llm"],
    },
    "systems": {
        "name": "AI system design & engineering",
        "arxiv": '(cat:cs.SE OR cat:cs.AI OR cat:cs.LG) AND (abs:"agent" OR abs:"retrieval-augmented" OR abs:"evaluation" OR abs:"prompting" OR abs:"inference")',
        "s2": ["LLM agents", "retrieval augmented generation", "LLM evaluation"],
        "keywords": ["agent", "rag", "retrieval", "eval", "prompt", "inference", "pipeline"],
    },
    "psychology": {
        "name": "AI & psychology / mental health",
        "arxiv": '(cat:cs.HC OR cat:cs.CY OR cat:cs.AI) AND (abs:psychology OR abs:"mental health" OR abs:cognitive OR abs:emotional OR abs:therapy OR abs:wellbeing)',
        "s2": ["AI psychology", "human-AI interaction mental health", "LLM therapy"],
        "keywords": ["psychology", "mental health", "cognitive", "emotional", "therapy", "wellbeing"],
    },
    "behavior": {
        "name": "AI & human behavior",
        "arxiv": '(cat:cs.HC OR cat:cs.CY) AND (abs:"human-AI interaction" OR abs:"behavior change" OR abs:"AI companion" OR abs:anthropomorphism OR abs:"cognitive offloading" OR abs:"AI reliance" OR abs:"trust in AI")',
        "s2": ["AI human behavior", "cognitive offloading AI", "AI companionship"],
        "keywords": ["human-ai", "behavior", "companion", "anthropomorphism", "offloading", "reliance", "trust"],
    },
}

# RSS/Atom feeds, tagged with the track they feed. Verified at build time (Task 8);
# any that 404 or aren't valid feeds are removed there.
RSS_FEEDS = [
    {"source": "Simon Willison", "track": "systems", "url": "https://simonwillison.net/atom/everything/"},
    {"source": "Ahead of AI", "track": "systems", "url": "https://magazine.sebastianraschka.com/feed"},
    {"source": "Hugging Face", "track": "models", "url": "https://huggingface.co/blog/feed.xml"},
    {"source": "Import AI", "track": "models", "url": "https://importai.substack.com/feed"},
    {"source": "The Gradient", "track": "psychology", "url": "https://thegradient.pub/rss/"},
    {"source": "Quanta Magazine", "track": "psychology", "url": "https://api.quantamagazine.org/feed/"},
    {"source": "MIT Technology Review", "track": "behavior", "url": "https://www.technologyreview.com/feed/"},
    {"source": "Ars Technica", "track": "behavior", "url": "https://feeds.arstechnica.com/arstechnica/index"},
]
# General-relevance keywords: an item must match at least one of these OR its track keywords.
AI_KEYWORDS = ["ai", "artificial intelligence", "machine learning", "neural", "model",
               "llm", "gpt", "transformer", "deep learning", "agent"]
```

- [ ] **Step 5: Create empty `sources/__init__.py` and `tests/__init__.py`**

- [ ] **Step 6: Commit**

```bash
git add requirements.txt .env.example config.py models.py sources/__init__.py tests/__init__.py
git commit -m "Scaffold: config, models, dependencies"
```

---

### Task 2: Processed-IDs state

**Files:**
- Create: `state.py`, `tests/test_state.py`

**Interfaces:**
- Produces: `load_seen(path) -> set[str]`, `save_seen(path, ids: set[str]) -> None`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_state.py
import state


def test_roundtrip_and_missing_file(tmp_path):
    p = tmp_path / "processed_ids.json"
    assert state.load_seen(str(p)) == set()          # missing file -> empty
    state.save_seen(str(p), {"a", "b"})
    assert state.load_seen(str(p)) == {"a", "b"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_state.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'state'`)

- [ ] **Step 3: Write minimal implementation**

```python
# state.py
import json
import os


def load_seen(path: str) -> set[str]:
    if not os.path.exists(path):
        return set()
    with open(path) as f:
        return set(json.load(f))


def save_seen(path: str, ids: set[str]) -> None:
    with open(path, "w") as f:
        json.dump(sorted(ids), f, indent=2)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_state.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add state.py tests/test_state.py
git commit -m "Add processed-IDs state store"
```

---

### Task 3: Dedupe

**Files:**
- Create: `dedupe.py`, `tests/test_dedupe.py`

**Interfaces:**
- Consumes: `models.Item`.
- Produces: `dedupe(items: list[Item]) -> list[Item]` — keeps the first occurrence of each id; treats items with the same normalized URL as duplicates.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_dedupe.py
from datetime import datetime, UTC
from models import Item
import dedupe


def _item(id, url, source="arXiv"):
    return Item(id=id, title="t", authors=[], source=source, url=url,
                published=datetime(2026, 7, 1, tzinfo=UTC), text="", track="models",
                content_type="paper")


def test_dedupe_by_id_and_url():
    a = _item("2401.001", "https://arxiv.org/abs/2401.001")
    a_dup = _item("2401.001", "https://arxiv.org/abs/2401.001", source="Semantic Scholar")
    b = _item("2401.002", "https://arxiv.org/abs/2401.001/")   # same URL, trailing slash
    c = _item("2401.003", "https://example.com/x")
    out = dedupe.dedupe([a, a_dup, b, c])
    assert [i.id for i in out] == ["2401.001", "2401.003"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_dedupe.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'dedupe'`)

- [ ] **Step 3: Write minimal implementation**

```python
# dedupe.py
from models import Item


def _norm_url(url: str) -> str:
    return url.strip().rstrip("/").lower()


def dedupe(items: list[Item]) -> list[Item]:
    seen_ids: set[str] = set()
    seen_urls: set[str] = set()
    out: list[Item] = []
    for it in items:
        u = _norm_url(it.url)
        if it.id in seen_ids or u in seen_urls:
            continue
        seen_ids.add(it.id)
        seen_urls.add(u)
        out.append(it)
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_dedupe.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add dedupe.py tests/test_dedupe.py
git commit -m "Add cross-source dedupe"
```

---

### Task 4: Filtering (7-day window, relevance, skip-rules)

**Files:**
- Create: `filtering.py`, `tests/test_filtering.py`

**Interfaces:**
- Consumes: `models.Item`, `config`.
- Produces: `filter_items(items, now, seen_ids) -> list[Item]` — drops items older than `WINDOW_DAYS`, already-seen ids, off-topic items, and skip-listed paper types.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_filtering.py
from datetime import datetime, timedelta, UTC
from models import Item
import filtering

NOW = datetime(2026, 7, 8, tzinfo=UTC)


def _item(**kw):
    base = dict(id="x", title="A large language model study", authors=[], source="arXiv",
                url="u", published=NOW, text="about llm reasoning", track="models",
                content_type="paper")
    base.update(kw)
    return Item(**base)


def test_drops_old_seen_offtopic_and_benchmark():
    fresh = _item(id="fresh")
    old = _item(id="old", published=NOW - timedelta(days=10))
    seen = _item(id="seen")
    offtopic = _item(id="off", title="Gardening tips", text="how to grow tomatoes")
    benchmark = _item(id="bench", title="A new benchmark dataset for X",
                      text="we release a benchmark dataset")
    out = filtering.filter_items([fresh, old, seen, offtopic, benchmark], NOW, {"seen"})
    assert [i.id for i in out] == ["fresh"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_filtering.py -v`
Expected: FAIL (`ModuleNotFoundError`)

- [ ] **Step 3: Write minimal implementation**

```python
# filtering.py
from datetime import datetime, timedelta
from models import Item
import config

# Papers whose title/abstract are dominated by these are skipped unless clearly applied.
_SKIP_MARKERS = ["benchmark", "dataset release", "we release a dataset", "we introduce a dataset",
                 "a new dataset", "purely theoretical"]


def _is_relevant(it: Item) -> bool:
    hay = (it.title + " " + it.text).lower()
    track_kw = config.TRACKS[it.track]["keywords"]
    return any(k in hay for k in track_kw) or any(k in hay for k in config.AI_KEYWORDS)


def _is_skippable(it: Item) -> bool:
    if it.content_type != "paper":
        return False
    hay = (it.title + " " + it.text).lower()
    applied = any(w in hay for w in ["deploy", "real-world", "clinical", "users", "practice"])
    return any(m in hay for m in _SKIP_MARKERS) and not applied


def filter_items(items: list[Item], now: datetime, seen_ids: set[str]) -> list[Item]:
    cutoff = now - timedelta(days=config.WINDOW_DAYS)
    out = []
    for it in items:
        if it.id in seen_ids:
            continue
        if it.published < cutoff:
            continue
        if not _is_relevant(it):
            continue
        if _is_skippable(it):
            continue
        out.append(it)
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_filtering.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add filtering.py tests/test_filtering.py
git commit -m "Add filtering: window, relevance, skip-rules"
```

---

### Task 5: Ranking (score, citation tiebreak, per-source cap, top 10)

**Files:**
- Create: `ranking.py`, `tests/test_ranking.py`

**Interfaces:**
- Consumes: `models.Item`, `config`.
- Produces: `rank(items, now) -> list[Item]` — sorted best-first, per-source cap applied, truncated to `MAX_ITEMS`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_ranking.py
from datetime import datetime, timedelta, UTC
from models import Item
import ranking

NOW = datetime(2026, 7, 8, tzinfo=UTC)


def _item(id, source, days_old, cites=None, kw="large language model reasoning"):
    return Item(id=id, title=kw, authors=[], source=source, url=id,
                published=NOW - timedelta(days=days_old), text=kw, track="models",
                content_type="paper", citation_count=cites)


def test_per_source_cap_and_recency():
    # Five items from one blog should be capped to PER_SOURCE_CAP (3).
    blog = [_item(f"b{i}", "Import AI", days_old=i) for i in range(5)]
    out = ranking.rank(blog, NOW)
    assert sum(1 for i in out if i.source == "Import AI") == 3


def test_citation_tiebreak():
    a = _item("a", "arXiv", days_old=1, cites=5)
    b = _item("b", "arXiv", days_old=1, cites=50)
    out = ranking.rank([a, b], NOW)
    assert out[0].id == "b"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_ranking.py -v`
Expected: FAIL (`ModuleNotFoundError`)

- [ ] **Step 3: Write minimal implementation**

```python
# ranking.py
from datetime import datetime
from models import Item
import config


def _score(it: Item, now: datetime) -> tuple:
    hay = (it.title + " " + it.text).lower()
    relevance = sum(1 for k in config.TRACKS[it.track]["keywords"] if k in hay)
    age_days = max((now - it.published).days, 0)
    recency = max(config.WINDOW_DAYS - age_days, 0)
    cites = it.citation_count or 0
    # Sort key: relevance, then recency, then citations (all descending).
    return (relevance, recency, cites)


def rank(items: list[Item], now: datetime) -> list[Item]:
    ordered = sorted(items, key=lambda it: _score(it, now), reverse=True)
    per_source: dict[str, int] = {}
    capped: list[Item] = []
    for it in ordered:
        n = per_source.get(it.source, 0)
        if n >= config.PER_SOURCE_CAP:
            continue
        per_source[it.source] = n + 1
        capped.append(it)
    return capped[: config.MAX_ITEMS]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_ranking.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add ranking.py tests/test_ranking.py
git commit -m "Add ranking with per-source cap and citation tiebreak"
```

---

### Task 6: arXiv source

**Files:**
- Create: `sources/arxiv.py`

**Interfaces:**
- Consumes: `config`, `models.Item`.
- Produces: `fetch(track_key: str, max_results: int = 30) -> list[Item]`. Never raises on network error — returns `[]` and logs.

- [ ] **Step 1: Write implementation** (arXiv returns Atom; parse with feedparser)

```python
# sources/arxiv.py
import logging
from datetime import datetime, UTC
from time import mktime
import feedparser
import requests
from models import Item
import config

API = "http://export.arxiv.org/api/query"
log = logging.getLogger(__name__)


def fetch(track_key: str, max_results: int = 30) -> list[Item]:
    query = config.TRACKS[track_key]["arxiv"]
    params = {"search_query": query, "sortBy": "submittedDate",
              "sortOrder": "descending", "max_results": max_results}
    try:
        resp = requests.get(API, params=params, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as e:
        log.warning("arXiv fetch failed for %s: %s", track_key, e)
        return []
    feed = feedparser.parse(resp.text)
    items = []
    for e in feed.entries:
        arxiv_id = e.id.split("/abs/")[-1]
        published = datetime.fromtimestamp(mktime(e.published_parsed), tz=UTC)
        items.append(Item(
            id=arxiv_id,
            title=e.title.strip().replace("\n", " "),
            authors=[a.name for a in getattr(e, "authors", [])],
            source="arXiv",
            url=e.link,
            published=published,
            text=e.summary.strip().replace("\n", " "),
            track=track_key,
            content_type="paper",
        ))
    return items
```

- [ ] **Step 2: Manual smoke test**

Run: `python -c "import sources.arxiv as a; items=a.fetch('models', 3); print(len(items)); print(items[0].title if items else 'none')"`
Expected: prints a small count and a paper title (or `0`/`none` if arXiv is briefly unavailable — that is acceptable, it must not crash).

- [ ] **Step 3: Commit**

```bash
git add sources/arxiv.py
git commit -m "Add arXiv source"
```

---

### Task 7: Semantic Scholar source

**Files:**
- Create: `sources/semantic_scholar.py`

**Interfaces:**
- Produces: `fetch(track_key: str, limit: int = 20) -> list[Item]`. Never raises — returns `[]` on error.

- [ ] **Step 1: Write implementation**

```python
# sources/semantic_scholar.py
import logging
from datetime import datetime, UTC
import requests
from models import Item
import config

API = "https://api.semanticscholar.org/graph/v1/paper/search"
FIELDS = "title,abstract,authors,url,citationCount,publicationDate,externalIds"
log = logging.getLogger(__name__)


def _parse_date(s: str | None) -> datetime | None:
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m", "%Y"):
        try:
            return datetime.strptime(s, fmt).replace(tzinfo=UTC)
        except ValueError:
            continue
    return None


def fetch(track_key: str, limit: int = 20) -> list[Item]:
    items = []
    for keyword in config.TRACKS[track_key]["s2"]:
        params = {"query": keyword, "limit": limit, "fields": FIELDS, "sort": "publicationDate:desc"}
        try:
            resp = requests.get(API, params=params, timeout=30)
            resp.raise_for_status()
        except requests.RequestException as e:
            log.warning("Semantic Scholar fetch failed for '%s': %s", keyword, e)
            continue
        for p in resp.json().get("data", []):
            published = _parse_date(p.get("publicationDate"))
            if published is None:
                continue
            ext = p.get("externalIds") or {}
            pid = ext.get("DOI") or ext.get("ArXiv") or p.get("paperId")
            items.append(Item(
                id=str(pid),
                title=(p.get("title") or "").strip(),
                authors=[a.get("name", "") for a in (p.get("authors") or [])],
                source="Semantic Scholar",
                url=p.get("url") or "",
                published=published,
                text=(p.get("abstract") or "").strip(),
                track=track_key,
                content_type="paper",
                citation_count=p.get("citationCount"),
            ))
    return items
```

- [ ] **Step 2: Manual smoke test**

Run: `python -c "import sources.semantic_scholar as s; print(len(s.fetch('psychology', 5)))"`
Expected: prints a number without crashing.

- [ ] **Step 3: Commit**

```bash
git add sources/semantic_scholar.py
git commit -m "Add Semantic Scholar source"
```

---

### Task 8: RSS source + feed verification

**Files:**
- Create: `sources/rss.py`, `scripts/verify_feeds.py`

**Interfaces:**
- Produces: `fetch(feed: dict, max_items: int = 15) -> list[Item]` where `feed` is one entry from `config.RSS_FEEDS`. Never raises — returns `[]` on error.

- [ ] **Step 1: Write `sources/rss.py`**

```python
# sources/rss.py
import logging
import re
from datetime import datetime, UTC
from time import mktime
import feedparser
from models import Item

log = logging.getLogger(__name__)


def _clean(html: str) -> str:
    return re.sub(r"<[^>]+>", "", html or "").strip()


def fetch(feed: dict, max_items: int = 15) -> list[Item]:
    try:
        parsed = feedparser.parse(feed["url"])
    except Exception as e:                       # feedparser is defensive but be safe
        log.warning("RSS fetch failed for %s: %s", feed["source"], e)
        return []
    items = []
    for e in parsed.entries[:max_items]:
        tp = getattr(e, "published_parsed", None) or getattr(e, "updated_parsed", None)
        if not tp:
            continue
        published = datetime.fromtimestamp(mktime(tp), tz=UTC)
        summary = _clean(getattr(e, "summary", ""))[:1200]
        items.append(Item(
            id=e.get("id") or e.link,
            title=_clean(e.title),
            authors=[a.get("name", "") for a in getattr(e, "authors", [])] or [feed["source"]],
            source=feed["source"],
            url=e.link,
            published=published,
            text=summary,
            track=feed["track"],
            content_type="article",
        ))
    return items
```

- [ ] **Step 2: Write `scripts/verify_feeds.py`** (run once to prune dead feeds from config)

```python
# scripts/verify_feeds.py
"""Check every feed in config.RSS_FEEDS actually parses. Print OK/DEAD per feed."""
import feedparser
import config

for feed in config.RSS_FEEDS:
    parsed = feedparser.parse(feed["url"])
    ok = bool(parsed.entries) and not parsed.bozo
    print(f"{'OK  ' if ok else 'DEAD'} {feed['source']:24} {feed['url']}")
```

- [ ] **Step 3: Run feed verification and prune**

Run: `python scripts/verify_feeds.py`
Expected: a line per feed. **Remove any `DEAD` feed from `config.RSS_FEEDS`.** (Company blogs sometimes lack a clean feed; that is fine, drop them.)

- [ ] **Step 4: Commit**

```bash
git add sources/rss.py scripts/verify_feeds.py config.py
git commit -m "Add RSS source and feed verification; prune dead feeds"
```

---

### Task 9: Summarize with Claude

**Files:**
- Create: `summarize.py`

**Interfaces:**
- Consumes: `models.Item`, `models.Summary`, `config`.
- Produces: `summarize(item: Item) -> Summary | None`. Returns `None` (and logs) if the call fails so `main` can skip that item.

- [ ] **Step 1: Write implementation** (one call returns both summary beats and the breakdown as JSON)

```python
# summarize.py
import json
import logging
import os
from anthropic import Anthropic
from models import Item, Summary
import config

log = logging.getLogger(__name__)

_PAPER_LABELS = ["What they studied", "Key finding", "Why it matters"]
_ARTICLE_LABELS = ["What it covers", "Key takeaway", "Why it matters"]

_STYLE = ("Short direct sentences. No filler. No em-dashes. No emojis. "
          "No hype adjectives like groundbreaking or revolutionary. "
          "Plain language for someone in tech who is not a researcher. "
          "Include numbers when the source gives them.")


def summarize(item: Item, client: Anthropic | None = None) -> Summary | None:
    client = client or Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    labels = _PAPER_LABELS if item.content_type == "paper" else _ARTICLE_LABELS
    prompt = (
        f"Summarize this {item.content_type} for a weekly AI newsletter.\n"
        f"Style: {_STYLE}\n\n"
        f"Title: {item.title}\nSource: {item.source}\nText: {item.text}\n\n"
        f"Return ONLY JSON with keys 'beats' and 'breakdown'. "
        f"'beats' is an object with exactly these keys in order: "
        f"{labels[0]!r}, {labels[1]!r}, {labels[2]!r}; each value one or two sentences. "
        f"'breakdown' is 4 to 6 sentences of plain-language detail for readers who click to expand."
    )
    try:
        msg = client.messages.create(
            model=config.MODEL_ID,
            max_tokens=900,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = msg.content[0].text.strip()
        raw = raw[raw.find("{"): raw.rfind("}") + 1]     # tolerate stray prose
        data = json.loads(raw)
        beats = {k: data["beats"][k] for k in labels}     # enforce label order
        return Summary(beats=beats, breakdown=data["breakdown"])
    except Exception as e:
        log.warning("Summarize failed for %s: %s", item.title, e)
        return None
```

- [ ] **Step 2: Manual smoke test** (requires `ANTHROPIC_API_KEY` in `.env`)

Run:
```bash
python -c "
from dotenv import load_dotenv; load_dotenv()
from datetime import datetime, UTC
from models import Item
import summarize
it = Item(id='x', title='Chain-of-thought prompting improves reasoning', authors=['A'],
          source='arXiv', url='u', published=datetime.now(UTC),
          text='We show that prompting models to reason step by step improves accuracy on math tasks by 20 percent.',
          track='models', content_type='paper')
s = summarize.summarize(it); print(s.beats); print(s.breakdown)"
```
Expected: prints the three labelled beats and a short breakdown, following the style rules.

- [ ] **Step 3: Commit**

```bash
git add summarize.py
git commit -m "Add Claude summarization (summary + breakdown)"
```

---

### Task 10: Render outputs (markdown, HTML page, index, archive, email)

**Files:**
- Create: `render.py`, `tests/test_render.py`

**Interfaces:**
- Consumes: `models.Item`, `models.Summary`, `config`.
- Produces:
  - `render_markdown(dated, groups, overview, source_errors) -> str`
  - `render_digest_html(dated, groups, overview, source_errors) -> str`
  - `render_email_html(dated, groups, site_base) -> str`
  - `render_index_html(dated) -> str`
  - `render_archive_html(dates: list[str]) -> str`

  where `groups` is `list[tuple[track_name, list[tuple[Item, Summary]]]]`.

- [ ] **Step 1: Write the failing test** (assert structure + style, not exact prose)

```python
# tests/test_render.py
from datetime import datetime, UTC
from models import Item, Summary
import render


def _pair():
    it = Item(id="2401.1", title="Attention Is All You Need", authors=["A", "B"],
              source="arXiv", url="https://arxiv.org/abs/2401.1",
              published=datetime(2026, 7, 7, tzinfo=UTC), text="", track="models",
              content_type="paper")
    s = Summary(beats={"What they studied": "They studied transformers.",
                       "Key finding": "It works well.",
                       "Why it matters": "It changes NLP."},
                breakdown="A longer explanation of the transformer architecture and results.")
    return it, s


def test_html_has_anchor_details_and_no_emdash():
    groups = [("AI models & research", [_pair()])]
    html = render.render_digest_html("2026-07-08", groups, "Overview text.", [])
    assert 'id="item-attention-is-all-you-need"' in html
    assert "<details>" in html                      # expand-on-click
    assert "—" not in html                     # no em-dash anywhere we generate


def test_email_links_to_page_section():
    groups = [("AI models & research", [_pair()])]
    email = render.render_email_html("2026-07-08", groups, "https://ex.github.io/ai-research-digest")
    assert "https://ex.github.io/ai-research-digest/digests/2026-07-08.html#item-attention-is-all-you-need" in email
    assert "read the full breakdown" in email.lower()


def test_archive_lists_dates_newest_first():
    html = render.render_archive_html(["2026-06-28", "2026-07-05"])
    assert html.index("2026-07-05") < html.index("2026-06-28")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_render.py -v`
Expected: FAIL (`ModuleNotFoundError`)

- [ ] **Step 3: Write implementation**

```python
# render.py
import html as _html

_PAGE_CSS = """
body{font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;max-width:720px;
margin:2rem auto;padding:0 1rem;color:#1a1a1a;line-height:1.55}
h1{font-weight:600} .track{margin-top:2.5rem} .item{border:1px solid #e5e5e5;border-radius:12px;
padding:1rem 1.25rem;margin:1rem 0} .beat{margin:.4rem 0} .label{font-weight:600}
.meta{color:#666;font-size:.9rem} details{margin-top:.6rem} summary{cursor:pointer;color:#5E6AD2}
a{color:#5E6AD2} .note{background:#fff6f6;border:1px solid #f3caca;padding:.6rem 1rem;border-radius:8px}
"""


def _esc(s: str) -> str:
    return _html.escape(s or "")


def _authors(item) -> str:
    a = item.authors
    if not a:
        return ""
    shown = ", ".join(a[:3]) + (" et al." if len(a) > 3 else "")
    return shown


def _source_note(source_errors) -> str:
    if not source_errors:
        return ""
    names = ", ".join(source_errors)
    return f'<p class="note">Some sources were unavailable this week: {_esc(names)}.</p>'


def render_digest_html(dated, groups, overview, source_errors) -> str:
    parts = [f"<!-- generated --><h1>AI Research Digest</h1><p class='meta'>{_esc(dated)}</p>",
             _source_note(source_errors)]
    for track_name, pairs in groups:
        parts.append(f'<div class="track"><h2>{_esc(track_name)}</h2>')
        for item, summary in pairs:
            parts.append(f'<div class="item" id="{item.slug()}">')
            parts.append(f'<h3><a href="{_esc(item.url)}">{_esc(item.title)}</a></h3>')
            parts.append(f'<p class="meta">{_esc(_authors(item))} &middot; {_esc(item.source)}</p>')
            for label, text in summary.beats.items():
                parts.append(f'<p class="beat"><span class="label">{_esc(label)}:</span> {_esc(text)}</p>')
            parts.append(f'<details><summary>Read the full breakdown</summary>'
                         f'<p>{_esc(summary.breakdown)}</p></details>')
            parts.append("</div>")
        parts.append("</div>")
    parts.append(f'<div class="track"><h2>This week in short</h2><p>{_esc(overview)}</p></div>')
    return f"<style>{_PAGE_CSS}</style>" + "".join(parts)


def render_email_html(dated, groups, site_base) -> str:
    page = f"{site_base.rstrip('/')}/digests/{dated}.html"
    parts = [f"<h1>AI Research Digest</h1><p>{_esc(dated)}</p>"]
    for track_name, pairs in groups:
        parts.append(f"<h2>{_esc(track_name)}</h2>")
        for item, summary in pairs:
            parts.append(f'<h3>{_esc(item.title)}</h3>')
            parts.append(f'<p style="color:#666">{_esc(_authors(item))} &middot; {_esc(item.source)}</p>')
            for label, text in summary.beats.items():
                parts.append(f"<p><strong>{_esc(label)}:</strong> {_esc(text)}</p>")
            parts.append(f'<p><a href="{page}#{item.slug()}">Read the full breakdown</a></p>')
    return "".join(parts)


def render_markdown(dated, groups, overview, source_errors) -> str:
    lines = [f"# AI Research Digest — {dated}", ""]
    if source_errors:
        lines.append(f"> Some sources were unavailable this week: {', '.join(source_errors)}.")
        lines.append("")
    for track_name, pairs in groups:
        lines.append(f"## {track_name}")
        lines.append("")
        for item, summary in pairs:
            lines.append(f"### {item.title}")
            lines.append(f"*{_authors(item)} · {item.source}* · [{item.url}]({item.url})")
            lines.append("")
            for label, text in summary.beats.items():
                lines.append(f"- **{label}:** {text}")
            lines.append("")
    lines.append("## This week in short")
    lines.append("")
    lines.append(overview)
    lines.append("")
    return "\n".join(lines)


def render_index_html(dated) -> str:
    # Latest digest, plus the Buttondown signup form placeholder.
    return (f"<style>{_PAGE_CSS}</style><h1>AI Research Digest</h1>"
            f'<p>A weekly, plain-language digest of the latest in AI. '
            f'<a href="archive.html">Browse the archive</a>.</p>'
            f'<!-- BUTTONDOWN_SIGNUP_FORM -->'
            f'<p><a href="digests/{_esc(dated)}.html">Read this week\'s digest ({_esc(dated)})</a></p>')


def render_archive_html(dates) -> str:
    items = "".join(
        f'<li><a href="digests/{_esc(d)}.html">{_esc(d)}</a></li>'
        for d in sorted(dates, reverse=True)
    )
    return (f"<style>{_PAGE_CSS}</style><h1>Archive</h1>"
            f'<p><a href="index.html">Back to latest</a></p><ul>{items}</ul>')
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_render.py -v`
Expected: PASS (all 3 tests)

- [ ] **Step 5: Commit**

```bash
git add render.py tests/test_render.py
git commit -m "Add renderers: markdown, HTML page, index, archive, email"
```

---

### Task 11: Buttondown delivery

**Files:**
- Create: `delivery.py`

**Interfaces:**
- Produces: `send(subject: str, body_html: str) -> bool`. Returns `True` on success, `False` on failure (logged). Raises nothing.

- [ ] **Step 1: Write implementation**

```python
# delivery.py
import logging
import os
import requests

log = logging.getLogger(__name__)
API = "https://api.buttondown.email/v1/emails"


def send(subject: str, body_html: str) -> bool:
    key = os.environ.get("BUTTONDOWN_API_KEY")
    if not key:
        log.error("BUTTONDOWN_API_KEY not set")
        return False
    try:
        resp = requests.post(
            API,
            headers={"Authorization": f"Token {key}"},
            json={"subject": subject, "body": body_html, "status": "sent"},
            timeout=30,
        )
        resp.raise_for_status()
        return True
    except requests.RequestException as e:
        log.error("Buttondown send failed: %s", e)
        return False
```

- [ ] **Step 2: Commit** (no live test here — verified end-to-end via the manual workflow run in Task 14)

```bash
git add delivery.py
git commit -m "Add Buttondown delivery"
```

---

### Task 12: Orchestrator (`main.py`)

**Files:**
- Create: `main.py`

**Interfaces:**
- Consumes: every module above.
- Produces: `main(dry_run: bool)`; CLI entry `python -m main [--dry-run]`.

- [ ] **Step 1: Write implementation**

```python
# main.py
import argparse
import logging
import os
from datetime import datetime, UTC
from dotenv import load_dotenv

import config, state, dedupe, filtering, ranking, render, delivery, summarize
from sources import arxiv, semantic_scholar, rss

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("digest")


def collect():
    items, errors = [], []
    for track_key in config.TRACKS:
        a = arxiv.fetch(track_key)
        s = semantic_scholar.fetch(track_key)
        if not a:
            errors.append(f"arXiv ({config.TRACKS[track_key]['name']})")
        items += a + s
    for feed in config.RSS_FEEDS:
        got = rss.fetch(feed)
        if not got:
            errors.append(feed["source"])
        items += got
    # de-duplicate the error labels while preserving order
    seen, uniq = set(), []
    for e in errors:
        if e not in seen:
            seen.add(e); uniq.append(e)
    return items, uniq


def build_groups(top, client):
    by_track: dict[str, list] = {k: [] for k in config.TRACKS}
    for item in top:
        s = summarize.summarize(item, client)
        if s is None:
            continue
        by_track[item.track].append((item, s))
    groups = [(config.TRACKS[k]["name"], pairs) for k, pairs in by_track.items() if pairs]
    return groups


def overview_text(groups) -> str:
    n = sum(len(p) for _, p in groups)
    tracks = ", ".join(name for name, _ in groups)
    return (f"This week we cover {n} items across {len(groups)} tracks: {tracks}. "
            f"Each entry links to its source and expands to a fuller breakdown on the site.")


def main(dry_run: bool = False):
    load_dotenv()
    now = datetime.now(UTC)
    dated = now.strftime("%Y-%m-%d")

    raw, source_errors = collect()
    seen = state.load_seen(config.PROCESSED_IDS_PATH)
    deduped = dedupe.dedupe(raw)
    filtered = filtering.filter_items(deduped, now, seen)
    top = ranking.rank(filtered, now)
    log.info("collected=%d deduped=%d filtered=%d top=%d", len(raw), len(deduped), len(filtered), len(top))
    if not top:
        log.info("Nothing new to publish this week.")
        return

    from anthropic import Anthropic
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    groups = build_groups(top, client)
    overview = overview_text(groups)

    os.makedirs("digests", exist_ok=True)
    os.makedirs("docs/digests", exist_ok=True)

    with open(f"digests/{dated}.md", "w") as f:
        f.write(render.render_markdown(dated, groups, overview, source_errors))
    with open(f"docs/digests/{dated}.html", "w") as f:
        f.write(render.render_digest_html(dated, groups, overview, source_errors))
    with open("docs/index.html", "w") as f:
        f.write(render.render_index_html(dated))
    dates = [n[:-5] for n in os.listdir("docs/digests") if n.endswith(".html")]
    with open("docs/archive.html", "w") as f:
        f.write(render.render_archive_html(dates))

    site_base = os.environ.get("SITE_BASE_URL", "")
    email_html = render.render_email_html(dated, groups, site_base)

    if dry_run:
        log.info("Dry run: skipping email send. Files written.")
    else:
        ok = delivery.send(f"AI Research Digest — {dated}", email_html)
        if not ok:
            raise SystemExit("Email delivery failed; site files were still written.")

    published_ids = {item.id for _, pairs in groups for item, _ in pairs}
    state.save_seen(config.PROCESSED_IDS_PATH, seen | published_ids)
    log.info("Done. Published %d items.", len(published_ids))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="write files but do not send email")
    main(**vars(ap.parse_args()))
```

- [ ] **Step 2: Local dry run** (needs `.env` with `ANTHROPIC_API_KEY`)

Run: `python -m main --dry-run`
Expected: logs the counts, writes `digests/<date>.md` and `docs/...` files, skips the email. Open `docs/digests/<date>.html` in a browser to eyeball it.

- [ ] **Step 3: Commit**

```bash
git add main.py
git commit -m "Add orchestrator with --dry-run"
```

---

### Task 13: GitHub Actions workflow

**Files:**
- Create: `.github/workflows/weekly-digest.yml`

- [ ] **Step 1: Write the workflow**

```yaml
name: Weekly digest
on:
  schedule:
    - cron: "30 3 * * 6"      # 03:30 UTC Saturday = 09:00 IST Saturday
  workflow_dispatch:           # lets you run it by hand from the Actions tab

permissions:
  contents: write              # allows the job to commit generated files

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -r requirements.txt
      - name: Generate and send digest
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          BUTTONDOWN_API_KEY: ${{ secrets.BUTTONDOWN_API_KEY }}
          SITE_BASE_URL: ${{ vars.SITE_BASE_URL }}
        run: python -m main
      - name: Commit published files
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add docs digests processed_ids.json
          git diff --cached --quiet || git commit -m "Digest: $(date -u +%Y-%m-%d)"
          git push
```

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/weekly-digest.yml
git commit -m "Add weekly GitHub Actions workflow"
```

---

### Task 14: README setup walkthrough + full end-to-end test

**Files:**
- Create: `README.md`

- [ ] **Step 1: Write `README.md`** — a first-timer walkthrough covering, step by step with screenshots-in-words:
  1. Get an **Anthropic API key** (console.anthropic.com → API keys → Create key). Note the cost expectation (well under $1/month).
  2. Create a **Buttondown** account, grab the **API key** (Settings → Programming → API), and copy the **signup form embed**; paste it into `render.render_index_html` where `<!-- BUTTONDOWN_SIGNUP_FORM -->` is.
  3. Create a **public GitHub repo** named `ai-research-digest` and push this folder (exact `git remote add` / `git push` commands).
  4. Add repository **secrets** (Settings → Secrets and variables → Actions → New repository secret): `ANTHROPIC_API_KEY`, `BUTTONDOWN_API_KEY`. Add a repository **variable** `SITE_BASE_URL` = `https://<username>.github.io/ai-research-digest`.
  5. Turn on **GitHub Pages** (Settings → Pages → Deploy from a branch → `main` → `/docs`).
  6. **Run it once by hand**: Actions tab → Weekly digest → Run workflow. Confirm the run is green, the email arrives, and the site publishes.
  7. Plain-language note on the schedule (Saturdays 09:00 IST) and how to change it.

- [ ] **Step 2: Full manual end-to-end run** (the real verification)

Run the workflow via **workflow_dispatch** in the Actions tab once all secrets are set.
Expected: green run; `docs/digests/<date>.html`, `docs/index.html`, `docs/archive.html`, `digests/<date>.md`, and `processed_ids.json` committed; the email lands in your inbox; the live Pages URL shows the digest and the archive.

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "Add setup walkthrough README"
```

---

## Notes for the implementer

- Run modules from the project root so bare imports (`import config`) resolve; that is why there is no `src/` package prefix.
- Keep the summary style rules in `summarize.py` verbatim — they are a product requirement, not a suggestion.
- If arXiv or Semantic Scholar is briefly down, the run should still publish whatever it got and note the gap at the top of the digest. Never let one dead source abort the run.
