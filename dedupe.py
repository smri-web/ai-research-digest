from models import Item


def _norm_url(url: str) -> str:
    return url.strip().rstrip("/").lower()


def dedupe(items: list[Item]) -> list[Item]:
    seen_ids: set[str] = set()
    seen_urls: set[str] = set()
    out: list[Item] = []
    for it in items:
        u = _norm_url(it.url)
        if it.id in seen_ids or u in seen_urls:
            continue
        seen_ids.add(it.id)
        seen_urls.add(u)
        out.append(it)
    return out
