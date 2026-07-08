from datetime import datetime, timedelta, UTC
from models import Item
import ranking

NOW = datetime(2026, 7, 8, tzinfo=UTC)


def _item(id, source, days_old, cites=None, kw="large language model reasoning"):
    return Item(id=id, title=kw, authors=[], source=source, url=id,
                published=NOW - timedelta(days=days_old), text=kw, track="models",
                content_type="paper", citation_count=cites)


def test_per_source_cap_and_recency():
    # Five items from one blog should be capped to PER_SOURCE_CAP (3).
    blog = [_item(f"b{i}", "Import AI", days_old=i) for i in range(5)]
    out = ranking.rank(blog, NOW)
    assert sum(1 for i in out if i.source == "Import AI") == 3


def test_citation_tiebreak():
    a = _item("a", "arXiv", days_old=1, cites=5)
    b = _item("b", "arXiv", days_old=1, cites=50)
    out = ranking.rank([a, b], NOW)
    assert out[0].id == "b"
