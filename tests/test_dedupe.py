from datetime import datetime, UTC
from models import Item
import dedupe


def _item(id, url, source="arXiv"):
    return Item(id=id, title="t", authors=[], source=source, url=url,
                published=datetime(2026, 7, 1, tzinfo=UTC), text="", track="models",
                content_type="paper")


def test_dedupe_by_id_and_url():
    a = _item("2401.001", "https://arxiv.org/abs/2401.001")
    a_dup = _item("2401.001", "https://arxiv.org/abs/2401.001", source="Semantic Scholar")
    b = _item("2401.002", "https://arxiv.org/abs/2401.001/")   # same URL, trailing slash
    c = _item("2401.003", "https://example.com/x")
    out = dedupe.dedupe([a, a_dup, b, c])
    assert [i.id for i in out] == ["2401.001", "2401.003"]
