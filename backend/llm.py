import asyncio, json, uuid
from datetime import datetime, timezone
from urllib.parse import urlparse

import httpx
from fastapi import HTTPException
from google import genai
from google.genai import types
from config import (GEMINI_API_KEY, GEMINI_MODEL,
                    GROQ_API_KEY, GROQ_MODEL, GROQ_MODEL_FALLBACK)
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

# Senza questa nota il modello scambia l'anno del proprio addestramento per il presente e
# scrive cose come "dal punto di vista attuale (2024)". La data va iniettata a ogni chiamata.
_MONTHS_IT = ("gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio",
              "agosto", "settembre", "ottobre", "novembre", "dicembre")


def today_note(lang: str) -> str:
    now = datetime.now(timezone.utc)
    if lang == "it":
        return (
            f"\n\nDATA ODIERNA: {now.day} {_MONTHS_IT[now.month - 1]} {now.year} "
            f"(ISO {now.date().isoformat()}). "
            f"«Oggi», «attualmente», «l'anno in corso» significano SEMPRE {now.year}. "
            "Non scrivere mai che l'anno corrente è quello del tuo addestramento e non "
            f"aggiungere fra parentesi anni diversi da {now.year} per indicare il presente. "
            "Se le tue conoscenze si fermano prima di questa data, dillo esplicitamente "
            "indicando fino a quando arrivano, invece di presentare dati vecchi come attuali."
        )
    return (
        f"\n\nTODAY'S DATE: {now.date().isoformat()}. "
        f"\"Today\", \"currently\" and \"this year\" always mean {now.year}. "
        "Never state that the current year is your training cutoff year, and never put a "
        f"parenthetical year other than {now.year} to mean the present. "
        "If your knowledge stops earlier, say so explicitly and state how far it goes, "
        "instead of presenting stale data as current."
    )


def sys_for(lang: str) -> str:
    base = SYSTEM_IT if lang == "it" else SYSTEM_EN
    return base + today_note(lang)


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


# ---------------------------------------------------------------- fallback Groq
# Quando Gemini è sovraccarico l'utente vedeva un errore secco. Groq ha un tier gratuito
# rapido e compatibile con l'API OpenAI: basta per Q&A, dibattito, storico e traduzioni.
# Non ha grounding web, quindi le risposte generate dal fallback arrivano senza fonti.
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"


class _FallbackResp:
    """Sagoma minima della risposta Gemini: i chiamanti usano solo `.text`."""

    def __init__(self, text: str):
        self.text = text
        self.candidates = []


async def _groq_generate(system: str, user_text: str, json_mode: bool = False):
    if not GROQ_API_KEY:
        return None
    payload_base = {
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user_text},
        ],
        "temperature": 0.6,
        "max_tokens": 4096,
    }
    if json_mode:
        payload_base["response_format"] = {"type": "json_object"}
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            for model in (GROQ_MODEL, GROQ_MODEL_FALLBACK):
                if not model:
                    continue
                try:
                    r = await client.post(GROQ_URL, headers=headers, json={**payload_base, "model": model})
                    if r.status_code >= 400:
                        log.warning(f"Groq {model} -> {r.status_code}: {r.text[:200]}")
                        continue
                    txt = r.json()["choices"][0]["message"]["content"] or ""
                    if txt.strip():
                        log.info(f"Risposta servita dal fallback Groq ({model})")
                        return _FallbackResp(txt)
                except Exception as e:
                    log.warning(f"Groq {model} fallito: {e}")
    except Exception as e:
        log.warning(f"Groq non raggiungibile: {e}")
    return None


async def _generate(system: str, user_text: str, grounded: bool = False, json_mode: bool = False):
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
                alt = await _groq_generate(system, user_text, json_mode)
                if alt:
                    return alt
                raise HTTPException(status_code=502, detail="Errore dal servizio IA. Riprova.")
            if attempt == RETRY_ATTEMPTS - 1:
                log.error(f"LLM error dopo {RETRY_ATTEMPTS} tentativi: {e}")
                alt = await _groq_generate(system, user_text, json_mode)
                if alt:
                    return alt
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
    resp = await _generate(system, user_text, json_mode=True)
    return _parse_json(resp.text or "")


async def llm_json_grounded(session_id: str, system: str, user_text: str):
    """JSON + link reali delle fonti (Google Search grounding). -> (dict, [{title,url}])"""
    try:
        resp = await _generate(system, user_text, grounded=True, json_mode=True)
    except HTTPException as e:
        if e.status_code != 502:  # sovraccarico/quota: inutile riprovare senza tool
            raise
        log.warning("grounding fallito, riprovo senza fonti")
        return await llm_json(session_id, system, user_text), []
    return _parse_json(resp.text or ""), await resolve_sources(sources_from(resp))


def new_session(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4()}"
