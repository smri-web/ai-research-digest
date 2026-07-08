"""Check every feed in config.RSS_FEEDS actually parses. Print OK/DEAD per feed."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import feedparser
import requests
import config

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; AIResearchDigest/1.0)"}

for feed in config.RSS_FEEDS:
    try:
        resp = requests.get(feed["url"], headers=HEADERS, timeout=30)
        resp.raise_for_status()
        parsed = feedparser.parse(resp.content)
        ok = bool(parsed.entries)
        n = len(parsed.entries)
    except requests.RequestException as e:
        ok, n = False, 0
        print(f"DEAD {feed['source']:24} {feed['url']}  ({e})")
        continue
    print(f"{'OK  ' if ok else 'DEAD'} {feed['source']:24} entries={n:<3} {feed['url']}")
