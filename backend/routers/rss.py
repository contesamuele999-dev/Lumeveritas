import asyncio
import hashlib
import re
from fastapi import APIRouter
import feedparser
from pymongo import UpdateOne

from db import db
from llm import llm_json, new_session
from log import log
from models import RSS_FEEDS, RSS_FEEDS_IT, TOPIC_KEY_BY_LABEL

router = APIRouter(prefix="/api", tags=["rss"])


def _clean_summary(s: str, limit: int = 320) -> str:
    if not s:
        return ""
    txt = re.sub(r"<[^>]+>", " ", s)
    txt = re.sub(r"\s+", " ", txt).strip()
    return txt[:limit]


async def _fetch_feed(url: str, feed_lang: str, timeout: int = 8) -> list:
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
                "lang": feed_lang,
            })
        return entries
    except Exception as ex:
        log.warning(f"RSS fetch failed {url}: {ex}")
        return []


# ---------------------------------------------------------------- traduzione
# Titoli e sommari vengono tradotti una sola volta e conservati: un articolo RSS non
# cambia testo, quindi ripagare la traduzione a ogni apertura sarebbe solo spreco.
def _cache_key(text: str, target: str) -> str:
    return f"{target}:" + hashlib.sha1(text.encode("utf-8", "ignore")).hexdigest()


async def _cached_translations(keys: list) -> dict:
    if not keys:
        return {}
    docs = await db.rss_translations.find({"key": {"$in": keys}}, {"_id": 0}).to_list(len(keys))
    return {d["key"]: d["text"] for d in docs}


async def _translate_batch(texts: list, target: str) -> dict:
    """texts -> {originale: tradotto}. In caso di errore restituisce {} (si tiene l'originale)."""
    if not texts:
        return {}
    lang_label = "italiano" if target == "it" else "English"
    numbered = "\n".join(f"{i}. {t}" for i, t in enumerate(texts))
    prompt = f"""Traduci in {lang_label} ognuna delle seguenti righe di testo giornalistico.
Mantieni i nomi propri, le sigle e i numeri invariati. Non riassumere, non aggiungere commenti.

{numbered}

Rispondi ESCLUSIVAMENTE con JSON valido nel formato:
{{"translations": {{"0": "traduzione riga 0", "1": "traduzione riga 1", ...}}}}
Una voce per ogni riga ricevuta, stessi indici. Nessun testo fuori dal JSON."""
    try:
        data = await asyncio.wait_for(
            llm_json(new_session("rss-translate"), "Sei un traduttore professionista. Rispondi solo con JSON.", prompt),
            timeout=45,
        )
    except Exception as e:
        log.warning(f"traduzione RSS fallita: {e}")
        return {}
    raw = data.get("translations") or data
    out = {}
    for i, original in enumerate(texts):
        val = raw.get(str(i)) if isinstance(raw, dict) else None
        if isinstance(val, str) and val.strip():
            out[original] = val.strip()
    return out


async def _translate_items(items: list, target: str) -> list:
    """Traduce titolo e sommario degli item la cui lingua non è quella richiesta."""
    todo = [it for it in items if it.get("lang") != target]
    if not todo:
        return items

    fields = []
    for it in todo:
        for f in ("title", "summary"):
            if it.get(f):
                fields.append(it[f])
    fields = list(dict.fromkeys(fields))  # dedup mantenendo l'ordine
    if not fields:
        return items

    keys = {txt: _cache_key(txt, target) for txt in fields}
    cached = await _cached_translations(list(keys.values()))
    missing = [txt for txt in fields if keys[txt] not in cached]

    fresh = {}
    if missing:
        # blocchi piccoli: una richiesta gigante ha più probabilità di tornare JSON rotto
        chunks = [missing[i:i + 16] for i in range(0, len(missing), 16)]
        results = await asyncio.gather(*[_translate_batch(c, target) for c in chunks])
        for r in results:
            fresh.update(r)
        if fresh:
            try:
                await db.rss_translations.bulk_write([
                    UpdateOne(
                        {"key": keys[src]},
                        {"$set": {"key": keys[src], "lang": target, "text": dst}},
                        upsert=True,
                    ) for src, dst in fresh.items() if src in keys
                ], ordered=False)
            except Exception as e:
                log.warning(f"cache traduzioni non salvata: {e}")

    def tr(txt):
        if not txt:
            return txt
        return fresh.get(txt) or cached.get(keys.get(txt, ""), txt)

    for it in todo:
        it["title"] = tr(it.get("title"))
        it["summary"] = tr(it.get("summary"))
        it["translated"] = True
    return items


@router.get("/rss/feed")
async def rss_feed(topic: str, limit: int = 10, lang: str = "it", translate: bool = True):
    key = TOPIC_KEY_BY_LABEL.get(topic.lower(), topic.lower())
    lang = "it" if lang not in ("it", "en") else lang

    it_urls = RSS_FEEDS_IT.get(key, [])
    en_urls = RSS_FEEDS.get(key, [])
    # le fonti nella lingua dell'utente vanno per prime: niente traduzione, niente attesa
    ordered = ([(u, "it") for u in it_urls] + [(u, "en") for u in en_urls]) if lang == "it" \
        else ([(u, "en") for u in en_urls] + [(u, "it") for u in it_urls])
    if not ordered:
        return {"topic": topic, "items": []}

    results = await asyncio.gather(*[_fetch_feed(u, fl) for u, fl in ordered])
    merged = []
    for r in results:
        merged.extend(r)

    seen, out = set(), []
    for item in merged:
        t = item["title"].lower()
        if t and t not in seen:
            seen.add(t)
            out.append(item)
    out = out[:limit]

    if translate:
        out = await _translate_items(out, lang)
    return {"topic": topic, "language": lang, "items": out}
