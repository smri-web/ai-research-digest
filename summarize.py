import json
import logging
import os
from anthropic import Anthropic
from models import Item, Summary
import config

log = logging.getLogger(__name__)

_PAPER_LABELS = ["What they studied", "Key finding", "Why it matters"]
_ARTICLE_LABELS = ["What it covers", "Key takeaway", "Why it matters"]

_STYLE = ("Short direct sentences. No filler. No em-dashes. No emojis. "
          "No hype adjectives like groundbreaking or revolutionary. "
          "Plain language for someone in tech who is not a researcher. "
          "Include numbers when the source gives them.")


def summarize(item: Item, client: Anthropic | None = None) -> Summary | None:
    client = client or Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
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
        msg = client.messages.create(
            model=config.MODEL_ID,
            max_tokens=900,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = msg.content[0].text.strip()
        raw = raw[raw.find("{"): raw.rfind("}") + 1]     # tolerate stray prose
        data = json.loads(raw)
        beats = {k: data["beats"][k] for k in labels}     # enforce label order
        return Summary(beats=beats, breakdown=data["breakdown"])
    except Exception as e:
        log.warning("Summarize failed for %s: %s", item.title, e)
        return None
