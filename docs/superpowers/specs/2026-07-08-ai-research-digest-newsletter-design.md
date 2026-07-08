# AI Research Digest — Weekly Newsletter (Design)

Date: 2026-07-08
Owner: Smuruthi Kesavan (product marketer, not an engineer — code changes are explained in plain language; new dependencies are approved before adding)

## Goal

A hands-off weekly newsletter about the latest in AI/tech. Every Saturday morning (IST), a
GitHub Actions job fetches recent papers and articles, filters to what actually matters,
summarizes each in plain language with the Claude API, publishes a web page + archive on
GitHub Pages, and emails the summaries to subscribers via Buttondown. No laptop required.

The real editorial filter: **latest tech / AI, and nothing else.**

## Decisions (locked)

- **Fresh build.** No prior code exists. New folder `~/Documents/Projects/ai-research-digest`,
  its own git repo, published to a **public** GitHub repo.
- **Hosting:** GitHub Pages served from the `/docs` folder on `main`. The weekly job writes
  HTML into `/docs` and commits it, so the archive is real, browsable files that Git versions.
- **Delivery:** **Buttondown** (newsletter service). It owns the subscriber list, unsubscribes,
  compliance, and a signup form we embed on the site. The job POSTs the finished HTML email to
  Buttondown's API. (Gmail SMTP was considered and rejected: send caps, poor deliverability, and
  no legal unsubscribe handling.)
- **Model:** **Google Gemini** `gemini-2.0-flash` via the free-tier REST API (no credit card).
  Chosen to keep the whole newsletter at $0/month while preserving the automated cloud run.
  Called with `requests` (no SDK). Swappable to another Gemini model via one config line.
  (Originally scoped to Claude Haiku 4.5; changed to avoid any Anthropic prepaid credit.)
- **Dependencies (approved):** `requests`, `feedparser`, `python-dotenv`.
  Email/HTTP-to-Buttondown uses `requests`; HTML is built with plain Python (no template engine).

## Tracks and sources

Four tracks. arXiv + Semantic Scholar cover papers; curated RSS feeds add reputable free
publications. Every feed URL is verified to actually work at build time; any that don't are
dropped rather than left fragile.

1. **AI models & research** — LLMs, foundation/reasoning/multimodal.
   arXiv, Semantic Scholar, Google DeepMind, Meta AI, Hugging Face blog, The Batch, Import AI.
2. **AI system design & engineering** — agents, RAG, evals, prompting, infra.
   Simon Willison, Sebastian Raschka (Ahead of AI), Eugene Yan, Chip Huyen, arXiv.
3. **AI & psychology / mental health** — cognition, therapy, wellbeing.
   arXiv, Semantic Scholar, The Gradient, Quanta.
4. **AI & human behavior** — companionship, anthropomorphism, cognitive offloading, trust/reliance.
   arXiv, Semantic Scholar, MIT Technology Review (AI), Ars Technica (AI).

arXiv queries and Semantic Scholar keywords per track are carried over from the original project
instructions (see `config.py`).

## Pipeline (runs every Saturday 09:00 IST)

1. **Fetch** — arXiv API, Semantic Scholar API, and the RSS feeds. Each item is normalized into a
   common shape: `id`, `title`, `authors`, `source`, `url`, `published`, `abstract/excerpt`,
   `track`, `citation_count` (papers only), `content_type` (`paper` | `article`).
2. **Dedupe** — papers by DOI/arXiv ID, articles by canonical URL. Cross-source too.
3. **Skip seen** — anything whose id is in `processed_ids.json` (committed to the repo) is dropped
   so nothing repeats across runs.
4. **Filter** — keep only items published in the last 7 days; require AI/tech relevance; drop pure
   benchmark, dataset-release, and heavy-math-theory papers unless they have obvious real-world
   implications.
5. **Rank** — score by relevance to the tracks + recency; citation count breaks ties where present.
   Apply a per-source cap so one prolific blog can't dominate. Keep the **top 10**.
6. **Summarize** — one Claude call per item returns two things: the three-beat summary and a longer
   "full breakdown" for the expand-on-click. Labels adapt by content type:
   - papers: *What they studied / Key finding / Why it matters*
   - articles: *What it covers / Key takeaway / Why it matters*
   Style rules (from original instructions): short direct sentences, no filler, no em-dashes, no
   emojis, no hype adjectives, plain language over jargon.
7. **Render** outputs (below).
8. **Deliver** — POST the HTML email to Buttondown.
9. **Commit** the new/updated files to the repo, which republishes the site.

## Outputs

- `digests/YYYY-MM-DD.md` — markdown digest (original requirement kept). Grouped by track. Each
  entry: title, authors, source, link, three-beat summary. Ends with a one-paragraph
  "This week in short" overview.
- `docs/digests/YYYY-MM-DD.html` — the web page. Each paper block shows the three-beat summary and
  **expands to the full breakdown on click** using native HTML `<details>`/`<summary>` (no
  JavaScript). Every block has an `id` anchor (`#item-<slug>`).
- `docs/index.html` — shows the latest digest and embeds the Buttondown signup form.
- `docs/archive.html` — lists every past digest (newest first), linking to each dated page. Built
  by listing the files in `docs/digests/`.
- **HTML email** (sent, not saved to repo) — just the summary blocks; each has a
  "read the full breakdown" link to `https://<user>.github.io/<repo>/digests/YYYY-MM-DD.html#item-<slug>`.

## Automation

`.github/workflows/weekly-digest.yml`:
- `on.schedule.cron: '30 3 * * 6'` — 03:30 UTC Saturday = 09:00 IST Saturday. (GitHub may delay
  scheduled runs a few minutes under load; acceptable for weekly.) Also `workflow_dispatch` so the
  job can be run manually from the Actions tab for testing.
- Steps: checkout, set up Python, `pip install -r requirements.txt`, run `python -m main`, commit
  and push any changes under `docs/`, `digests/`, and `processed_ids.json`.
- `permissions: contents: write` so the job can push generated files.

## Secrets (GitHub repo → Settings → Secrets and variables → Actions)

- `GEMINI_API_KEY`
- `BUTTONDOWN_API_KEY`

No Gmail credentials and no recipient list in the repo — Buttondown holds subscribers. Locally,
the same keys live in a `.env` file (git-ignored); `python-dotenv` loads them for test runs.

## Code layout

```
config.py                  tracks, queries, feed URLs, model id, constants
sources/arxiv.py           fetch + parse arXiv (Atom via feedparser)
sources/semantic_scholar.py fetch via API
sources/rss.py             fetch any RSS/Atom feed, tag with its track
dedupe.py                  cross-source dedupe by DOI/arXiv id / URL
state.py                   read/write processed_ids.json
filtering.py               7-day window, AI/tech relevance, skip-rules
ranking.py                 relevance + recency score, citation tiebreak, per-source cap, top 10
summarize.py               Claude call -> {summary, breakdown}
render.py                  build markdown, digest HTML page, index, archive, email HTML
delivery.py                Buttondown API client (small, swappable interface)
main.py                    orchestrates the steps in order
.github/workflows/weekly-digest.yml
```

## Error handling

- A source that fails (network/HTTP) is skipped; a note is added at the **top of the digest**
  listing which sources were unavailable.
- An item Claude can't summarize is skipped and noted; the run continues.
- If Buttondown sending fails, the site still publishes; the error is logged and the run exits
  non-zero so GitHub emails a failed-run notification.
- API keys are read from environment only, never hardcoded.

## Testing

Lightweight unit tests for the pure logic that doesn't touch the network or paid APIs:
dedupe, date/7-day filtering, skip-rules, relevance scoring, ranking + per-source cap, and the
markdown/HTML rendering (given fixed input items). Network and Claude calls are exercised
manually via `workflow_dispatch` and a local dry-run flag.

## Setup walkthrough (delivered with the code, for a first-time GitHub Actions user)

Front of the implementation plan, step by step:
1. Get a free Google Gemini API key (aistudio.google.com, no credit card).
2. Get a Buttondown account + API key, create the signup form.
3. Create the public GitHub repo and push this project.
4. Add the two secrets.
5. Turn on GitHub Pages (Deploy from branch → `main` → `/docs`).
6. Run the workflow manually once from the Actions tab to confirm end to end.

## Out of scope (YAGNI)

- Multiple email providers / provider-switching UI (Buttondown only; delivery module is cleanly
  abstracted but we implement one).
- Custom domain, analytics, comment system.
- Real-time or more-than-weekly runs.
