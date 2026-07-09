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


def test_articles_need_a_real_ai_signal():
    # A genuine AI article stays; a science-newsletter roundup whose only "ai" is inside words
    # like "maintain"/"available" is dropped (this is the class of leak we are fixing).
    legit = _item(id="legit", content_type="article", track="systems",
                  title="New LLM agent framework", text="a new approach to building AI agents")
    roundup = _item(id="roundup", content_type="article", track="behavior",
                    title="The Download: worms fight pollution",
                    text="A dairy farmer uses worms to maintain cleaner water. Available now.")
    out = filtering.filter_items([legit, roundup], NOW, set())
    assert [i.id for i in out] == ["legit"]


def test_backdated_window_excludes_newer_items():
    # When generating a digest for a past week, items published after that week must not leak in.
    in_window = _item(id="in", published=NOW - timedelta(days=2))
    newer = _item(id="newer", published=NOW + timedelta(days=3))
    out = filtering.filter_items([in_window, newer], NOW, set())
    assert [i.id for i in out] == ["in"]


def test_word_boundary_not_substring():
    # "storage pipeline for email" must NOT count as relevant via 'rag' inside 'storage' or
    # 'ai' inside 'email'. With no real AI term, this article is dropped.
    art = _item(id="sub", content_type="article", track="systems",
                title="Cloud storage tips", text="managing storage and email retention")
    assert filtering.filter_items([art], NOW, set()) == []


def test_drops_old_seen_offtopic_and_benchmark():
    fresh = _item(id="fresh")
    old = _item(id="old", published=NOW - timedelta(days=10))
    seen = _item(id="seen")
    offtopic = _item(id="off", title="Gardening tips", text="how to grow tomatoes")
    benchmark = _item(id="bench", title="A new benchmark dataset for X",
                      text="we release a benchmark dataset")
    out = filtering.filter_items([fresh, old, seen, offtopic, benchmark], NOW, {"seen"})
    assert [i.id for i in out] == ["fresh"]
