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
    return (f"<style>{_PAGE_CSS}</style><h1>AI Research Digest</h1>"
            f'<p>A weekly, plain-language digest of the latest in AI. '
            f'<a href="archive.html">Browse the archive</a>.</p>'
            f'<p><a href="digests/{_esc(dated)}.html">Read this week\'s digest ({_esc(dated)})</a></p>')


def render_archive_html(dates) -> str:
    items = "".join(
        f'<li><a href="digests/{_esc(d)}.html">{_esc(d)}</a></li>'
        for d in sorted(dates, reverse=True)
    )
    return (f"<style>{_PAGE_CSS}</style><h1>Archive</h1>"
            f'<p><a href="index.html">Back to latest</a></p><ul>{items}</ul>')
