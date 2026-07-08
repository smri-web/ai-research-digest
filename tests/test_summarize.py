import json
from datetime import datetime, UTC
from models import Item
import summarize


class _Resp:
    def __init__(self, payload, status_code=200):
        self._p = payload
        self.status_code = status_code

    def raise_for_status(self):
        pass

    def json(self):
        return self._p


def _item():
    return Item(id="x", title="T", authors=[], source="arXiv", url="u",
                published=datetime(2026, 7, 1, tzinfo=UTC), text="about llm",
                track="models", content_type="paper")


def test_parses_gemini_json(monkeypatch):
    gemini_text = json.dumps({
        "beats": {"What they studied": "a", "Key finding": "b", "Why it matters": "c"},
        "breakdown": "d",
    })
    payload = {"candidates": [{"content": {"parts": [{"text": gemini_text}]}}]}
    monkeypatch.setattr(summarize.requests, "post", lambda *a, **k: _Resp(payload))
    s = summarize.summarize(_item(), api_key="fake")
    assert list(s.beats.keys()) == ["What they studied", "Key finding", "Why it matters"]
    assert s.breakdown == "d"


def test_returns_none_without_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    assert summarize.summarize(_item()) is None
