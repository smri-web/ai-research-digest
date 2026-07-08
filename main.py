import argparse
import logging
import os
from datetime import datetime, UTC
from dotenv import load_dotenv

import config, state, dedupe, filtering, ranking, render, delivery, summarize
from selftest import send_via_gmail
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


def main(dry_run: bool = False, selftest: bool = False):
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

    if selftest:
        to = os.environ.get("TEST_RECIPIENT") or os.environ.get("GMAIL_ADDRESS", "")
        ok = send_via_gmail(f"[TEST] AI Research Digest: {dated}", email_html, to)
        log.info("Self-test email to %s: %s", to, "sent" if ok else "FAILED (check .env)")
        log.info("Self-test: files written; processed_ids NOT saved, safe to re-run.")
        return

    if dry_run:
        log.info("Dry run: skipping email send. Files written.")
    else:
        ok = delivery.send(f"AI Research Digest: {dated}", email_html)
        if not ok:
            raise SystemExit("Email delivery failed; site files were still written.")

    published_ids = {item.id for _, pairs in groups for item, _ in pairs}
    state.save_seen(config.PROCESSED_IDS_PATH, seen | published_ids)
    log.info("Done. Published %d items.", len(published_ids))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="write files but do not send email")
    ap.add_argument("--selftest", action="store_true",
                    help="email one preview to yourself via Gmail; skips Buttondown and does not save processed_ids")
    main(**vars(ap.parse_args()))
