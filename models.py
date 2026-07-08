from dataclasses import dataclass
from datetime import datetime


@dataclass
class Item:
    id: str                      # arXiv id, DOI, or canonical URL
    title: str
    authors: list[str]
    source: str                  # "arXiv", "Semantic Scholar", "Simon Willison", ...
    url: str
    published: datetime          # timezone-aware, UTC
    text: str                    # abstract (papers) or excerpt (articles)
    track: str                   # a key from config.TRACKS
    content_type: str            # "paper" | "article"
    citation_count: int | None = None

    def slug(self) -> str:
        """URL-safe anchor id for this item, e.g. 'item-attention-is-all-you-need'."""
        import re
        base = re.sub(r"[^a-z0-9]+", "-", self.title.lower()).strip("-")
        return "item-" + base[:60].strip("-")


@dataclass
class Summary:
    beats: dict[str, str]        # ordered 3-part summary, label -> text
    breakdown: str               # longer plain-language explanation
