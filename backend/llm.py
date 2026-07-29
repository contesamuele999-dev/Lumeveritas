import asyncio, json, uuid
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


async def llm_text(session_id: str, system: str, user_text: str) -> str:
    # session_id resta nella firma per compatibilità: ogni chiamata usa già una sessione
    # nuova (new_session), quindi non c'è storico da mantenere.
    for attempt in range(RETRY_ATTEMPTS):
        try:
            resp = await _client.aio.models.generate_content(
                model=GEMINI_MODEL,
                contents=user_text,
                config=types.GenerateContentConfig(system_instruction=system),
            )
            return resp.text or ""
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


async def llm_json(session_id: str, system: str, user_text: str) -> dict:
    text = await llm_text(session_id, system, user_text)
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


def new_session(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4()}"
