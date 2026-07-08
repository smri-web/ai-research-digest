import logging
import re
from datetime import datetime, UTC
from time import mktime
import feedparser
import requests
from models import Item

log = logging.getLogger(__name__)

# A browser-like UA; some publishers block the default urllib/requests agent.
_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; AIResearchDigest/1.0)"}


def _clean(html: str) -> str:
    return re.sub(r"<[^>]+>", "", html or "").strip()


def fetch(feed: dict, max_items: int = 15) -> list[Item]:
    # Fetch with requests (bundled SSL certs via certifi), then let feedparser parse the
    # bytes. Letting feedparser fetch the URL itself can fail SSL verification on some hosts.
    try:
        resp = requests.get(feed["url"], headers=_HEADERS, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as e:
        log.warning("RSS fetch failed for %s: %s", feed["source"], e)
        return []
    parsed = feedparser.parse(resp.content)
    items = []
    for e in parsed.entries[:max_items]:
        tp = getattr(e, "published_parsed", None) or getattr(e, "updated_parsed", None)
        if not tp:
            continue
        published = datetime.fromtimestamp(mktime(tp), tz=UTC)
        summary = _clean(getattr(e, "summary", ""))[:1200]
        items.append(Item(
            id=e.get("id") or e.link,
            title=_clean(e.title),
            authors=[a.get("name", "") for a in getattr(e, "authors", [])] or [feed["source"]],
            source=feed["source"],
            url=e.link,
            published=published,
            text=summary,
            track=feed["track"],
            content_type="article",
        ))
    return items
