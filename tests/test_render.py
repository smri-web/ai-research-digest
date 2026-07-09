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


def test_markdown_has_obsidian_frontmatter():
    groups = [("AI models & research", [_pair()])]
    md = render.render_markdown("2026-07-08", groups, "Overview.", [])
    assert md.startswith("---\ndate: 2026-07-08\n")     # Obsidian properties block
    assert "- ai-digest" in md
    # --print mode asks for no frontmatter
    bare = render.render_markdown("2026-07-08", groups, "Overview.", [], frontmatter=False)
    assert bare.startswith("# AI Research Digest")


def test_archive_lists_dates_newest_first():
    html = render.render_archive_html(["2026-06-28", "2026-07-05"])
    assert html.index("2026-07-05") < html.index("2026-06-28")


def test_pages_carry_share_metadata():
    groups = [("AI models & research", [_pair()])]
    html = render.render_digest_html("2026-07-08", groups, "Overview.", [])
    assert html.startswith("<!DOCTYPE html>")
    assert '<meta property="og:title"' in html
    assert 'og:url" content="https://smri-web.github.io/ai-research-digest/digests/2026-07-08.html"' in html
    assert 'rel="alternate" type="application/rss+xml"' in html


def test_feed_is_valid_rss_newest_first():
    xml = render.render_feed_xml(["2026-06-28", "2026-07-05"])
    assert xml.startswith('<?xml version="1.0"')
    assert "<rss version=\"2.0\">" in xml
    assert xml.index("2026-07-05") < xml.index("2026-06-28")
    assert "Sun, 28 Jun 2026 13:00:00 GMT" in xml     # RFC 822 pubDate
