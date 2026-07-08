import re
from datetime import datetime, timedelta
from models import Item
import config

# Papers whose title/abstract are dominated by these are skipped unless clearly applied.
_SKIP_MARKERS = ["benchmark", "dataset release", "we release a dataset", "we introduce a dataset",
                 "a new dataset", "purely theoretical"]

# Short, ambiguous tokens that must match as WHOLE words. Otherwise "ai" matches "email" and
# "maintain", "rag" matches "storage", etc., which is what let off-topic items slip through.
_EXACT = {"ai", "ml", "rag", "gpt", "llm", "llms"}


def _term_pattern(term: str) -> str:
    # Exact terms get both boundaries; others get a leading boundary but an open end, so
    # morphological variants still count ("eval" -> "evaluation", "prompt" -> "prompting").
    if term in _EXACT:
        return r"\b" + re.escape(term) + r"\b"
    return r"\b" + re.escape(term)


def _hits(hay: str, terms) -> bool:
    return any(re.search(_term_pattern(t), hay) for t in terms)


def _is_relevant(it: Item) -> bool:
    hay = (it.title + " " + it.text).lower()
    track_kw = config.TRACKS[it.track]["keywords"]
    if it.content_type == "paper":
        # Papers come from targeted arXiv / Semantic Scholar queries, so a broad check is fine.
        return _hits(hay, track_kw) or _hits(hay, config.AI_KEYWORDS)
    # Articles and newsletters are noisier. Require a genuine AI signal or an AI-specific track
    # keyword, so a pollution story in a science newsletter does not qualify just because it
    # contains a word like "maintain".
    return _hits(hay, config.STRONG_AI_KEYWORDS) or _hits(hay, track_kw)


def _is_skippable(it: Item) -> bool:
    if it.content_type != "paper":
        return False
    hay = (it.title + " " + it.text).lower()
    applied = any(w in hay for w in ["deploy", "real-world", "clinical", "users", "practice"])
    return any(m in hay for m in _SKIP_MARKERS) and not applied


def filter_items(items: list[Item], now: datetime, seen_ids: set[str]) -> list[Item]:
    cutoff = now - timedelta(days=config.WINDOW_DAYS)
    out = []
    for it in items:
        if it.id in seen_ids:
            continue
        if it.published < cutoff:
            continue
        if not _is_relevant(it):
            continue
        if _is_skippable(it):
            continue
        out.append(it)
    return out
