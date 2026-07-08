from datetime import datetime, timedelta
from models import Item
import config

# Papers whose title/abstract are dominated by these are skipped unless clearly applied.
_SKIP_MARKERS = ["benchmark", "dataset release", "we release a dataset", "we introduce a dataset",
                 "a new dataset", "purely theoretical"]


def _is_relevant(it: Item) -> bool:
    hay = (it.title + " " + it.text).lower()
    track_kw = config.TRACKS[it.track]["keywords"]
    return any(k in hay for k in track_kw) or any(k in hay for k in config.AI_KEYWORDS)


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
