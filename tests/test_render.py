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
