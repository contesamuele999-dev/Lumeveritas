import asyncio, json, uuid
from urllib.parse import urlparse

import httpx
from fastapi import HTTPException
from google import genai
from google.genai import types
from config import GEMINI_API_KEY, GEMINI_MODEL
from log import log

_client = genai.Client(api_key=GEMINI_API_KEY)

# Gemini restituisce spesso 503 UNAVAILABLE (modello sovraccarico) o 429: sono
# condizioni temporanee, non errori di configurazione. Si riprova con backoff.
RETRY_ATTEMPTS = 3
RETRY_BACKOFF = (1.0, 3.0)  # secondi di attesa dopo il 1° e il 2° fallimento


def _is_transient(err: str) -> bool:
    return any(k in err for k in ("503", "unavailable", "overloaded", "429", "rate", "quota", "resource_exhausted"))

SYSTEM_IT = (
    "Sei Lume Veritas, un analista di notizie serio e non partigiano. Il tuo scopo è "
    "raccogliere e sintetizzare notizie recenti sugli argomenti che i giornalisti mainstream "
    "spesso trascurano o semplificano eccessivamente. Devi: (1) essere fattuale e obiettivo, "
    "(2) distinguere chiaramente fatti verificati, dati e opinioni, (3) indicare quando non "
    "hai dati recenti, (4) esplorare i veri motivi dietro decisioni politiche/conflitti quando "
    "esistono documenti/dichiarazioni pubbliche, (5) evitare sensazionalismo. Rispondi SEMPRE in italiano."
)
SYSTEM_EN = (
    "You are Lume Veritas, a serious non-partisan news analyst. Your goal is to gather and "
    "synthesize recent news on topics mainstream journalism often overlooks or oversimplifies. "
    "You must: (1) be factual and objective, (2) clearly distinguish verified facts, data and "
    "opinions, (3) explicitly say when you lack recent data, (4) explore real reasons behind "
    "political decisions/conflicts when public evidence exists, (5) avoid sensationalism. "
    "Always answer in English."
)


def sys_for(lang: str) -> str:
    return SYSTEM_IT if lang == "it" else SYSTEM_EN


# Il grounding di Gemini non restituisce l'URL della fonte ma un redirect firmato,
# identico per tutte le fonti tranne il token finale: mostrarlo all'utente è inutile.
REDIRECT_HOSTS = ("vertexaisearch.cloud.google.com", "www.google.com", "google.com")


def _domain_of(url: str) -> str:
    try:
        host = (urlparse(url).hostname or "").replace("www.", "", 1)
    except Exception:
        return ""
    return "" if host in REDIRECT_HOSTS else host


def sources_from(resp) -> list:
    """Link reali delle pagine usate da Google Search grounding."""
    out, seen = [], set()
    try:
        chunks = resp.candidates[0].grounding_metadata.grounding_chunks or []
    except Exception:
        return out
    for ch in chunks:
        web = getattr(ch, "web", None)
        uri = getattr(web, "uri", None)
        if uri and uri not in seen:
            seen.add(uri)
            title = (getattr(web, "title", None) or "").strip()
            # spesso il "title" del chunk È già il dominio della fonte (es. "reuters.com")
            domain = _domain_of(uri) or (title if "." in title and " " not in title else "")
            out.append({
                "title": (title or domain or uri)[:120],
                "url": uri,
                "domain": domain or None,
            })
    return out[:12]


async def resolve_sources(sources: list) -> list:
    """Segue i redirect di grounding per ricavare URL e dominio reali della fonte.

    Best-effort: se la rete non risponde entro pochi secondi si tengono i dati originali,
    perché una fonte con etichetta imperfetta è meglio di una risposta lenta.
    """
    todo = [s for s in sources if not s.get("domain")]
    if not todo:
        return sources

    async def one(client, s):
        try:
            r = await client.get(s["url"])
            final = str(r.url)
            dom = _domain_of(final)
            if dom:
                s["url"] = final
                s["domain"] = dom
                if not s.get("title") or s["title"].startswith("http"):
                    s["title"] = dom
        except Exception:
            pass

    try:
        async with httpx.AsyncClient(
            follow_redirects=True, timeout=5.0,
            headers={"User-Agent": "Mozilla/5.0 (compatible; LumeVeritas/1.0)"},
        ) as client:
            await asyncio.wait_for(
                asyncio.gather(*[one(client, s) for s in todo]), timeout=8.0
            )
    except Exception as e:
        log.warning(f"resolve_sources parziale: {e}")
    return sources


async def _generate(system: str, user_text: str, grounded: bool = False):
    # session_id resta nella firma pubblica per compatibilità: ogni chiamata usa già una
    # sessione nuova (new_session), quindi non c'è storico da mantenere.
    cfg = types.GenerateContentConfig(system_instruction=system)
    if grounded:
        cfg.tools = [types.Tool(google_search=types.GoogleSearch())]
    for attempt in range(RETRY_ATTEMPTS):
        try:
            return await _client.aio.models.generate_content(
                model=GEMINI_MODEL, contents=user_text, config=cfg,
            )
        except Exception as e:
            msg = str(e).lower()
            if not _is_transient(msg):
                log.error(f"LLM error: {e}")
                raise HTTPException(status_code=502, detail="Errore dal servizio IA. Riprova.")
            if attempt == RETRY_ATTEMPTS - 1:
                log.error(f"LLM error dopo {RETRY_ATTEMPTS} tentativi: {e}")
                raise HTTPException(status_code=429, detail="Il servizio IA è momentaneamente sovraccarico. Riprova tra qualche secondo.")
            log.warning(f"LLM transient ({attempt + 1}/{RETRY_ATTEMPTS}), riprovo: {e}")
            await asyncio.sleep(RETRY_BACKOFF[attempt])


async def llm_text(session_id: str, system: str, user_text: str) -> str:
    resp = await _generate(system, user_text)
    return resp.text or ""


def _parse_json(text: str) -> dict:
    start = text.find('{')
    end = text.rfind('}')
    if start >= 0 and end > start:
        try:
            return json.loads(text[start:end+1])
        except Exception:
            pass
    s2 = text.find('[')
    e2 = text.rfind(']')
    if s2 >= 0 and e2 > s2:
        try:
            return {"items": json.loads(text[s2:e2+1])}
        except Exception:
            pass
    raise HTTPException(status_code=502, detail="AI parse error")


async def llm_json(session_id: str, system: str, user_text: str) -> dict:
    resp = await _generate(system, user_text)
    return _parse_json(resp.text or "")


async def llm_json_grounded(session_id: str, system: str, user_text: str):
    """JSON + link reali delle fonti (Google Search grounding). -> (dict, [{title,url}])"""
    try:
        resp = await _generate(system, user_text, grounded=True)
    except HTTPException as e:
        if e.status_code != 502:  # sovraccarico/quota: inutile riprovare senza tool
            raise
        log.warning("grounding fallito, riprovo senza fonti")
        return await llm_json(session_id, system, user_text), []
    return _parse_json(resp.text or ""), await resolve_sources(sources_from(resp))


def new_session(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4()}"
