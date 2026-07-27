import asyncio
import re
from fastapi import APIRouter
import feedparser
from log import log
from models import RSS_FEEDS, TOPIC_KEY_BY_LABEL

router = APIRouter(prefix="/api", tags=["rss"])


def _clean_summary(s: str, limit: int = 320) -> str:
    if not s:
        return ""
    txt = re.sub(r"<[^>]+>", " ", s)
    txt = re.sub(r"\s+", " ", txt).strip()
    return txt[:limit]


async def _fetch_feed(url: str, timeout: int = 8) -> list:
    try:
        parsed = await asyncio.wait_for(asyncio.to_thread(feedparser.parse, url), timeout=timeout)
        entries = []
        for e in parsed.entries[:8]:
            entries.append({
                "title": getattr(e, "title", "").strip(),
                "link": getattr(e, "link", ""),
                "summary": _clean_summary(getattr(e, "summary", "") or getattr(e, "description", "")),
                "source": parsed.feed.get("title", url) if hasattr(parsed, "feed") else url,
                "published": getattr(e, "published", "") or getattr(e, "updated", ""),
            })
        return entries
    except Exception as ex:
        log.warning(f"RSS fetch failed {url}: {ex}")
        return []


@router.get("/rss/feed")
async def rss_feed(topic: str, limit: int = 10):
    key = TOPIC_KEY_BY_LABEL.get(topic.lower(), topic.lower())
    urls = RSS_FEEDS.get(key, [])
    if not urls:
        return {"topic": topic, "items": []}
    results = await asyncio.gather(*[_fetch_feed(u) for u in urls])
    merged = []
    for r in results:
        merged.extend(r)
    seen, out = set(), []
    for item in merged:
        t = item["title"].lower()
        if t and t not in seen:
            seen.add(t)
            out.append(item)
    return {"topic": topic, "items": out[:limit]}
