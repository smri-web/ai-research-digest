from datetime import datetime
from models import Item
import config


def _score(it: Item, now: datetime) -> tuple:
    hay = (it.title + " " + it.text).lower()
    relevance = sum(1 for k in config.TRACKS[it.track]["keywords"] if k in hay)
    age_days = max((now - it.published).days, 0)
    recency = max(config.WINDOW_DAYS - age_days, 0)
    cites = it.citation_count or 0
    # Sort key: relevance, then recency, then citations (all descending).
    return (relevance, recency, cites)


def rank(items: list[Item], now: datetime) -> list[Item]:
    ordered = sorted(items, key=lambda it: _score(it, now), reverse=True)
    per_source: dict[str, int] = {}
    capped: list[Item] = []
    for it in ordered:
        n = per_source.get(it.source, 0)
        if n >= config.PER_SOURCE_CAP:
            continue
        per_source[it.source] = n + 1
        capped.append(it)
    return capped[: config.MAX_ITEMS]
