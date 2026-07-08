import json
import logging
import os
import requests
from models import Item, Summary
import config

log = logging.getLogger(__name__)

_PAPER_LABELS = ["What they studied", "Key finding", "Why it matters"]
_ARTICLE_LABELS = ["What it covers", "Key takeaway", "Why it matters"]

_STYLE = ("Short direct sentences. No filler. No em-dashes. No emojis. "
          "No hype adjectives like groundbreaking or revolutionary. "
          "Plain language for someone in tech who is not a researcher. "
          "Include numbers when the source gives them.")

_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


def summarize(item: Item, api_key: str | None = None) -> Summary | None:
    """Summarize one item with Google Gemini (free tier). Returns None on any failure so the
    caller can skip this item and keep going."""
    api_key = api_key or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        log.error("GEMINI_API_KEY not set")
        return None
    labels = _PAPER_LABELS if item.content_type == "paper" else _ARTICLE_LABELS
    prompt = (
        f"Summarize this {item.content_type} for a weekly AI newsletter.\n"
        f"Style: {_STYLE}\n\n"
        f"Title: {item.title}\nSource: {item.source}\nText: {item.text}\n\n"
        f"Return ONLY JSON with keys 'beats' and 'breakdown'. "
        f"'beats' is an object with exactly these keys in order: "
        f"{labels[0]!r}, {labels[1]!r}, {labels[2]!r}; each value one or two sentences. "
        f"'breakdown' is 4 to 6 sentences of plain-language detail for readers who click to expand."
    )
    try:
        resp = requests.post(
            _ENDPOINT.format(model=config.MODEL_ID),
            params={"key": api_key},
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "response_mime_type": "application/json",
                    "maxOutputTokens": 1200,
                    "temperature": 0.3,
                    # gemini-2.5 models "think" by default and spend output tokens doing it,
                    # which truncates our JSON. Summarizing needs no reasoning budget.
                    "thinkingConfig": {"thinkingBudget": 0},
                },
            },
            timeout=60,
        )
        resp.raise_for_status()
        raw = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
        data = json.loads(raw)
        beats = {k: data["beats"][k] for k in labels}     # enforce label order
        return Summary(beats=beats, breakdown=data["breakdown"])
    except Exception as e:
        log.warning("Summarize failed for %s: %s", item.title, e)
        return None
