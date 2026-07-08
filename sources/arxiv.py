import logging
from datetime import datetime, UTC
from time import mktime
import feedparser
import requests
from models import Item
import config

API = "http://export.arxiv.org/api/query"
log = logging.getLogger(__name__)


def fetch(track_key: str, max_results: int = 30) -> list[Item]:
    query = config.TRACKS[track_key]["arxiv"]
    params = {"search_query": query, "sortBy": "submittedDate",
              "sortOrder": "descending", "max_results": max_results}
    try:
        resp = requests.get(API, params=params, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as e:
        log.warning("arXiv fetch failed for %s: %s", track_key, e)
        return []
    feed = feedparser.parse(resp.text)
    items = []
    for e in feed.entries:
        arxiv_id = e.id.split("/abs/")[-1]
        published = datetime.fromtimestamp(mktime(e.published_parsed), tz=UTC)
        items.append(Item(
            id=arxiv_id,
            title=e.title.strip().replace("\n", " "),
            authors=[a.name for a in getattr(e, "authors", [])],
            source="arXiv",
            url=e.link,
            published=published,
            text=e.summary.strip().replace("\n", " "),
            track=track_key,
            content_type="paper",
        ))
    return items
