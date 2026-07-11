# AI Research Digest

A weekly, plain-language digest of the latest in AI. Every Friday evening (6:00 PM IST), a job
running on GitHub's servers (no laptop needed) fetches recent papers and articles, keeps the 10
most relevant, summarizes each with Google Gemini, and publishes a web page with a running archive.
A small companion job on the owner's Mac then delivers each new digest into an Obsidian vault.

- **Live site:** <https://smri-web.github.io/ai-research-digest/>
- **Archive:** <https://smri-web.github.io/ai-research-digest/archive.html>

## How it works (one paragraph)

The site is hosted free on **GitHub Pages** (served from the `docs/` folder). The schedule and
automation are handled by **GitHub Actions** (a free robot that runs the script on a timer:
`30 12 * * 5`, which is 6:00 PM IST Friday). Summaries are written by **Google Gemini's free
tier** (`gemini-2.5-flash`, set in `config.py`); the `GEMINI_API_KEY` secret is stored encrypted
in GitHub and never appears in code or logs. There is no email list: instead, a tiny **launchd**
job on the Mac (`com.smri.aidigest-obsidian`) checks the repo every Friday at 7:00 PM and at
login, and downloads any new digest notes into the Obsidian vault, where iCloud syncs them to
other devices.

## The four tracks

1. **AI models & research** — LLMs, foundation/reasoning/multimodal models.
2. **AI system design & engineering** — agents, RAG, evals, prompting, infra.
3. **AI & psychology / mental health** — cognition, therapy, wellbeing.
4. **AI & human behavior** — companionship, anthropomorphism, cognitive offloading, trust.

Sources: arXiv + Semantic Scholar (papers) and curated RSS feeds (Simon Willison, Ahead of AI,
Hugging Face, Import AI, The Gradient, Quanta, MIT Technology Review, Ars Technica). Tracks,
queries, and feeds all live in `config.py`.

## Outputs per run

- `digests/YYYY-MM-DD.md` — the digest as markdown, with Obsidian frontmatter (date + `ai-digest`
  tag). This is the file the Obsidian sync picks up.
- `docs/digests/YYYY-MM-DD.html` — the web page; each item expands to a fuller breakdown on click.
- `docs/index.html` + `docs/archive.html` — latest issue and the archive listing.

## The Obsidian leg (runs on the Mac, not in the cloud)

- Script: `scripts/sync_to_obsidian.py`, with a runtime copy at
  `~/Library/Application Support/aidigest/sync_to_obsidian.py` (background jobs cannot read
  `~/Documents` on macOS, so the copy lives in an unprotected location). If you edit the script in
  the repo, re-copy it there.
- Schedule: `~/Library/LaunchAgents/com.smri.aidigest-obsidian.plist` — checks Friday 7/9/11 PM,
  Saturday 9:30 AM, Sunday 10 AM, and at every login. Multiple checks because GitHub's cron can
  run hours late (it did on 2026-07-10, so the single 7 PM check missed the digest); the check is
  one cheap request and only downloads notes it does not already have.
  Log: `~/Library/Logs/aidigest-obsidian.log`.
- Destination: the "AI Research Digest" folder inside the "AI Knowledge" vault (iCloud).
- It only ever downloads notes it does not have; it never edits or deletes anything in the vault,
  so your own notes and edits are safe.

## Running it on demand

- The personal Claude Code skill (`~/.claude/skills/ai-research-digest`) generates a fresh digest
  in any Claude session and publishes it the same way the Friday run does: archive page, Obsidian
  note, and the digest shown in chat.
- For a preview that publishes nothing: `./.venv/bin/python -m main --print`.

## Running locally

```bash
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt
cp .env.example .env        # then fill in GEMINI_API_KEY
./.venv/bin/python -m main --print          # fresh digest to the terminal
./.venv/bin/python -m pytest tests/ -v      # unit tests
./.venv/bin/python scripts/verify_feeds.py  # check the RSS sources are alive
```

## Costs

Nothing. Gemini free tier + GitHub Actions/Pages on a public repo + iCloud you already have.

## Troubleshooting

- **Run is red at "Generate and send digest":** usually the `GEMINI_API_KEY` secret is missing or
  rotated. Repo → Settings → Secrets and variables → Actions.
- **A note did not appear in Obsidian:** check `~/Library/Logs/aidigest-obsidian.log`. The job
  also runs at every login, so a missed Friday self-heals.
- **"Nothing new to publish this week" in the Actions log:** everything found was already covered
  in a prior run. Normal in a quiet week.
- **Sources listed as unavailable at the top of a digest:** that source was down or rate-limited
  during the run. Normal; the digest publishes with what it got. An optional free
  `SEMANTIC_SCHOLAR_API_KEY` (see `.env.example`) makes that source much more reliable.
