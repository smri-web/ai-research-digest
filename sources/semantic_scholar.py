import logging
from datetime import datetime, UTC
import requests
from models import Item
import config

API = "https://api.semanticscholar.org/graph/v1/paper/search"
FIELDS = "title,abstract,authors,url,citationCount,publicationDate,externalIds"
log = logging.getLogger(__name__)


def _parse_date(s: str | None) -> datetime | None:
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m", "%Y"):
        try:
            return datetime.strptime(s, fmt).replace(tzinfo=UTC)
        except ValueError:
            continue
    return None


def fetch(track_key: str, limit: int = 20) -> list[Item]:
    items = []
    for keyword in config.TRACKS[track_key]["s2"]:
        params = {"query": keyword, "limit": limit, "fields": FIELDS, "sort": "publicationDate:desc"}
        try:
            resp = requests.get(API, params=params, timeout=30)
            resp.raise_for_status()
        except requests.RequestException as e:
            log.warning("Semantic Scholar fetch failed for '%s': %s", keyword, e)
            continue
        for p in resp.json().get("data", []):
            published = _parse_date(p.get("publicationDate"))
            if published is None:
                continue
            ext = p.get("externalIds") or {}
            pid = ext.get("DOI") or ext.get("ArXiv") or p.get("paperId")
            items.append(Item(
                id=str(pid),
                title=(p.get("title") or "").strip(),
                authors=[a.get("name", "") for a in (p.get("authors") or [])],
                source="Semantic Scholar",
                url=p.get("url") or "",
                published=published,
                text=(p.get("abstract") or "").strip(),
                track=track_key,
                content_type="paper",
                citation_count=p.get("citationCount"),
            ))
    return items
