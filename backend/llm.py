import json, uuid
from fastapi import HTTPException
from google import genai
from google.genai import types
from config import GEMINI_API_KEY, GEMINI_MODEL
from log import log

_client = genai.Client(api_key=GEMINI_API_KEY)

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
    try:
        resp = await _client.aio.models.generate_content(
            model=GEMINI_MODEL,
            contents=user_text,
            config=types.GenerateContentConfig(system_instruction=system),
        )
    except Exception as e:
        msg = str(e).lower()
        if "429" in msg or "rate" in msg or "quota" in msg or "resource_exhausted" in msg:
            raise HTTPException(status_code=429, detail="Il servizio IA è momentaneamente sovraccarico. Riprova tra qualche secondo.")
        log.error(f"LLM error: {e}")
        raise HTTPException(status_code=502, detail="Errore dal servizio IA. Riprova.")
    return resp.text or ""


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
