import json
import logging
import os
import time
import requests
from models import Item, Summary
import config

log = logging.getLogger(__name__)

# The last label in each list is optional: the model includes it only when the source genuinely
# points somewhere, so quiet papers do not get padded with speculation.
_PAPER_LABELS = ["What they studied", "Why they studied it", "Method",
                 "Findings and results", "Benefits and impact", "What it adds to the future"]
_ARTICLE_LABELS = ["What it covers", "Why it matters now", "Key takeaway",
                   "Benefits and impact", "What it adds to the future"]

_STYLE = ("Short direct sentences. No filler. No em-dashes. No emojis. "
          "No hype adjectives like groundbreaking or revolutionary. "
          "Plain language for someone in tech who is not a researcher. "
          "Include numbers when the source gives them.")

_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


def _retry_delay(resp, default: float = 8.0, cap: float = 30.0) -> float:
    """How long Gemini asks us to wait after a 429, bounded so we never hang for long."""
    try:
        for d in resp.json()["error"]["details"]:
            if d.get("@type", "").endswith("RetryInfo"):
                s = d.get("retryDelay", "")
                if s.endswith("s"):
                    return min(float(s[:-1]), cap)
    except Exception:
        pass
    return default


def summarize(item: Item, api_key: str | None = None) -> Summary | None:
    """Summarize one item with Google Gemini (free tier). Returns None on any failure so the
    caller can skip this item and keep going."""
    api_key = api_key or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        log.error("GEMINI_API_KEY not set")
        return None
    labels = _PAPER_LABELS if item.content_type == "paper" else _ARTICLE_LABELS
    required, optional = labels[:-1], labels[-1]
    keys = ", ".join(repr(k) for k in required)
    prompt = (
        f"Summarize this {item.content_type} for a weekly AI newsletter.\n"
        f"Style: {_STYLE}\n\n"
        f"Title: {item.title}\nSource: {item.source}\nText: {item.text}\n\n"
        f"Return ONLY JSON with keys 'beats' and 'breakdown'. "
        f"'beats' is an object with these keys in order: {keys}; each value one or two sentences. "
        f"Base every section only on what the text supports; if the text does not state the "
        f"method or motivation outright, infer conservatively and keep it to one sentence. "
        f"Also include the key {optional!r} ONLY if the work genuinely points at future "
        f"directions or implications; omit it rather than speculate. "
        f"'breakdown' is 4 to 6 sentences of plain-language detail for readers who click to expand."
    )
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "response_mime_type": "application/json",
            "maxOutputTokens": 2000,
            "temperature": 0.3,
            # gemini-2.5 models "think" by default and spend output tokens doing it,
            # which truncates our JSON. Summarizing needs no reasoning budget.
            "thinkingConfig": {"thinkingBudget": 0},
        },
    }
    url = _ENDPOINT.format(model=config.MODEL_ID)
    for attempt in range(3):
        try:
            resp = requests.post(url, params={"key": api_key}, json=body, timeout=60)
            # Free-tier rate limit: wait the suggested time and retry a couple of times.
            if resp.status_code == 429 and attempt < 2:
                wait = _retry_delay(resp)
                log.info("Rate limited; waiting %.0fs then retrying (%s)", wait, item.title[:50])
                time.sleep(wait)
                continue
            resp.raise_for_status()
            raw = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
            data = json.loads(raw)
            # Required sections must all be present (KeyError -> item skipped); the final
            # future-facing section is included only when the model produced it.
            beats = {k: data["beats"][k] for k in required}
            future = (data["beats"].get(optional) or "").strip()
            if future:
                beats[optional] = future
            return Summary(beats=beats, breakdown=data["breakdown"])
        except Exception as e:
            log.warning("Summarize failed for %s: %s", item.title, e)
            return None
    log.warning("Summarize gave up after retries for %s", item.title)
    return None
