import html as _html
from datetime import datetime, timezone

SITE_BASE = "https://smri-web.github.io/ai-research-digest"
SITE_NAME = "AI Research Digest"
SITE_DESC = ("A weekly, plain-language digest of the latest AI research: models, system design, "
             "psychology, and human behavior. New issue every Friday evening.")

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


def _page(title: str, description: str, path: str, body: str) -> str:
    """Wrap body in a full HTML document with the meta tags that make shared links unfurl as a
    rich card on LinkedIn, WhatsApp, Slack, and X."""
    url = f"{SITE_BASE}/{path}" if path else SITE_BASE + "/"
    t, d = _esc(title), _esc(description)
    return (
        "<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n"
        "<meta charset=\"utf-8\">\n"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
        f"<title>{t}</title>\n"
        f"<meta name=\"description\" content=\"{d}\">\n"
        f"<meta property=\"og:title\" content=\"{t}\">\n"
        f"<meta property=\"og:description\" content=\"{d}\">\n"
        f"<meta property=\"og:type\" content=\"website\">\n"
        f"<meta property=\"og:url\" content=\"{url}\">\n"
        f"<meta property=\"og:site_name\" content=\"{_esc(SITE_NAME)}\">\n"
        f"<meta property=\"og:image\" content=\"{SITE_BASE}/og.png\">\n"
        "<meta name=\"twitter:card\" content=\"summary_large_image\">\n"
        f"<link rel=\"alternate\" type=\"application/rss+xml\" title=\"{_esc(SITE_NAME)}\" "
        f"href=\"{SITE_BASE}/feed.xml\">\n"
        f"<style>{_PAGE_CSS}</style>\n"
        "</head>\n<body>\n" + body + "\n</body>\n</html>\n"
    )


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
    n = sum(len(p) for _, p in groups)
    return _page(f"{SITE_NAME}: {dated}",
                 f"{n} plain-language summaries of this week's AI research. {overview[:150]}",
                 f"digests/{dated}.html", "".join(parts))


def render_markdown(dated, groups, overview, source_errors, frontmatter: bool = True) -> str:
    lines = []
    if frontmatter:
        # YAML properties block that Obsidian reads natively: shows the date as a property and
        # makes every digest findable via the #ai-digest tag or a tag search.
        lines += ["---", f"date: {dated}", "tags:", "  - ai-digest", "---", ""]
    lines += [f"# AI Research Digest: {dated}", ""]
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
    body = (f"<h1>{_esc(SITE_NAME)}</h1>"
            f'<p>{_esc(SITE_DESC)}</p>'
            f'<p><a href="digests/{_esc(dated)}.html">Read this week\'s digest ({_esc(dated)})</a>'
            f' &middot; <a href="archive.html">Archive</a>'
            f' &middot; <a href="feed.xml">RSS</a></p>')
    return _page(SITE_NAME, SITE_DESC, "", body)


def render_archive_html(dates) -> str:
    items = "".join(
        f'<li><a href="digests/{_esc(d)}.html">{_esc(d)}</a></li>'
        for d in sorted(dates, reverse=True)
    )
    body = (f"<h1>Archive</h1>"
            f'<p><a href="index.html">Back to latest</a> &middot; '
            f'<a href="feed.xml">Subscribe via RSS</a></p><ul>{items}</ul>')
    return _page(f"Archive · {SITE_NAME}", SITE_DESC, "archive.html", body)


def render_feed_xml(dates) -> str:
    """RSS feed with one entry per issue, newest first, so anyone can follow the digest in a
    feed reader. Entries link to the published page rather than embedding full content."""
    entries = []
    for d in sorted(dates, reverse=True):
        url = f"{SITE_BASE}/digests/{d}.html"
        # RSS requires RFC 822 dates ("Fri, 10 Jul 2026 13:00:00 GMT").
        pub = datetime.strptime(d, "%Y-%m-%d").replace(hour=13, tzinfo=timezone.utc)
        entries.append(
            f"<item><title>{_esc(SITE_NAME)}: {_esc(d)}</title>"
            f"<link>{url}</link><guid isPermaLink=\"true\">{url}</guid>"
            f"<pubDate>{pub.strftime('%a, %d %b %Y %H:%M:%S GMT')}</pubDate>"
            f"<description>Plain-language summaries of this week's AI research.</description>"
            f"</item>"
        )
    return (
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
        "<rss version=\"2.0\"><channel>"
        f"<title>{_esc(SITE_NAME)}</title>"
        f"<link>{SITE_BASE}/</link>"
        f"<description>{_esc(SITE_DESC)}</description>"
        + "".join(entries) + "</channel></rss>"
    )
