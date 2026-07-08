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
