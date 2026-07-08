# AI Research Digest

A weekly, plain-language newsletter about the latest in AI. Every Saturday morning (9:00 AM IST),
a job running on GitHub's servers (no laptop needed) fetches recent papers and articles, keeps the
10 most relevant, summarizes each with Claude, publishes a web page and an archive, and emails the
summaries to your subscribers through Buttondown.

You do not need to understand the code to run this. Follow the setup steps once and it runs itself.

---

## How it works (one paragraph)

The site is hosted free on **GitHub Pages** (the `docs/` folder). The schedule and automation are
handled by **GitHub Actions** (a free robot that runs your script on a timer). The email list,
signup form, and unsubscribe handling are managed by **Buttondown** (a newsletter service). Your
two secret keys (Claude and Buttondown) are stored encrypted in GitHub and are never visible in the
code or the logs.

---

## One-time setup

You will do six things: get a Claude key, set up Buttondown, put this project on GitHub, add the
secret keys, turn on the website, and run it once by hand to confirm it works.

### 1. Get your Anthropic (Claude) API key

1. Go to <https://console.anthropic.com> and sign in.
2. Add a small amount of credit under **Billing** (a few dollars lasts a long time; see Costs below).
3. Open **API keys**, click **Create key**, name it `ai-research-digest`, and copy the key
   (it starts with `sk-ant-`). You will paste it into GitHub in step 4. Keep it private.

### 2. Set up Buttondown (email delivery + subscribers)

1. Create a free account at <https://buttondown.com> (free up to ~100 subscribers).
2. In **Settings → API** (sometimes under "Programming"), copy your **API key**.
3. In **Settings**, find your **embeddable subscribe form** and copy its HTML snippet.
4. Open `render.py`, find the line `<!-- BUTTONDOWN_SIGNUP_FORM -->` inside `render_index_html`,
   and paste your form snippet in place of that comment. This puts a "Subscribe" box on your site.
5. Add yourself (and a few friends) as subscribers in Buttondown so the first email has recipients.

### 3. Put this project on GitHub

1. Create a **new, public** repository at <https://github.com/new>. Name it `ai-research-digest`.
   Do **not** add a README or .gitignore there (this project already has them).
2. In a terminal, from this project folder, connect it and push (replace `YOUR_USERNAME`):

   ```bash
   git remote add origin https://github.com/YOUR_USERNAME/ai-research-digest.git
   git branch -M main
   git push -u origin main
   ```

### 4. Add your secret keys to GitHub

In your repo on GitHub: **Settings → Secrets and variables → Actions**.

- Under **Secrets**, click **New repository secret** twice and add:
  - `ANTHROPIC_API_KEY` = your Claude key from step 1
  - `BUTTONDOWN_API_KEY` = your Buttondown key from step 2
- Switch to the **Variables** tab, click **New repository variable**, and add:
  - `SITE_BASE_URL` = `https://YOUR_USERNAME.github.io/ai-research-digest`
    (this is used to build the "read the full breakdown" links in the email)

Secrets are encrypted. They are never shown in the code or in run logs, even though the repo is public.

### 5. Turn on the website (GitHub Pages)

In your repo: **Settings → Pages**. Under **Build and deployment**, set **Source** to
**Deploy from a branch**, choose branch **main** and folder **/docs**, then **Save**.
Your site will live at `https://YOUR_USERNAME.github.io/ai-research-digest`.

### 6. Run it once by hand to confirm everything works

1. In your repo, open the **Actions** tab. If prompted, click to enable workflows.
2. Select **Weekly digest** on the left, then click **Run workflow → Run workflow**.
3. Wait a minute and refresh. A green check means success. Then confirm:
   - The email arrived in your inbox (and your subscribers').
   - Your site shows the digest, and the archive page lists it.

If the run is red, open it and read the failed step. See Troubleshooting below.

---

## The schedule

The job runs every **Saturday at 09:00 IST** (`cron: "30 3 * * 6"` in
`.github/workflows/weekly-digest.yml`, which is 03:30 UTC). GitHub sometimes starts scheduled jobs
a few minutes late under load; that is normal for a weekly newsletter. To change the time, edit that
`cron` line (it is in UTC) and push the change.

## Costs

- **Claude:** summarizing ~10 items per week costs well under **$1/month** with the Haiku model.
- **GitHub Actions + Pages:** free for public repositories.
- **Buttondown:** free up to ~100 subscribers.

## Testing it on your own laptop (optional)

1. Copy `.env.example` to `.env` and fill in your keys.
2. Create a virtual environment and install dependencies:

   ```bash
   python3 -m venv .venv
   ./.venv/bin/pip install -r requirements.txt
   ```

3. Do a **dry run** (writes the files but does NOT send an email):

   ```bash
   ./.venv/bin/python -m main --dry-run
   ```

   Then open `docs/index.html` or the newest file in `docs/digests/` in your browser.
4. Run the tests: `./.venv/bin/python -m pytest tests/ -v`
5. Check the RSS sources are alive: `./.venv/bin/python scripts/verify_feeds.py`

## Changing what it covers

- **Topics and sources** live in `config.py` (the four tracks, the arXiv queries, and the list of
  RSS feeds). Add or remove a feed by editing `RSS_FEEDS`, then run `scripts/verify_feeds.py` to
  confirm the new feed works.
- **Writing style** for the summaries lives in `summarize.py` (short sentences, no em-dashes,
  no hype). It is a product requirement; keep it as-is unless you want a different voice.
- **How many items** and the **7-day window** are constants at the top of `config.py`.

## Troubleshooting

- **Run is red at "Generate and send digest":** usually a missing or wrong secret. Recheck
  `ANTHROPIC_API_KEY` and `BUTTONDOWN_API_KEY` in Settings → Secrets.
- **Email did not arrive:** confirm you have at least one subscriber in Buttondown and that the
  Buttondown key is correct. The site still publishes even if the email fails.
- **Site shows 404:** Pages can take a couple of minutes after the first run. Confirm Pages is set
  to branch `main`, folder `/docs`.
- **"Nothing new to publish this week" in the logs:** everything found was already sent in a prior
  run. This is normal in a quiet week.
