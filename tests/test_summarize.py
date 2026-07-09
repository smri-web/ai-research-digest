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


PAPER_REQUIRED = ["What they studied", "Why they studied it", "Method",
                  "Findings and results", "Benefits and impact"]


def _payload(beats):
    text = json.dumps({"beats": beats, "breakdown": "d"})
    return {"candidates": [{"content": {"parts": [{"text": text}]}}]}


def test_parses_gemini_json_with_future_section(monkeypatch):
    beats = {k: "x" for k in PAPER_REQUIRED}
    beats["What it adds to the future"] = "points toward better agents"
    monkeypatch.setattr(summarize.requests, "post", lambda *a, **k: _Resp(_payload(beats)))
    s = summarize.summarize(_item(), api_key="fake")
    assert list(s.beats.keys()) == PAPER_REQUIRED + ["What it adds to the future"]
    assert s.breakdown == "d"


def test_future_section_is_optional(monkeypatch):
    beats = {k: "x" for k in PAPER_REQUIRED}   # model omitted the future key
    monkeypatch.setattr(summarize.requests, "post", lambda *a, **k: _Resp(_payload(beats)))
    s = summarize.summarize(_item(), api_key="fake")
    assert list(s.beats.keys()) == PAPER_REQUIRED


def test_returns_none_without_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    assert summarize.summarize(_item()) is None
