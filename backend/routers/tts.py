import base64
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from emergentintegrations.llm.openai import OpenAITextToSpeech

from config import EMERGENT_LLM_KEY
from db import db
from log import log
from models import TTSIn

router = APIRouter(prefix="/api", tags=["tts"])


def _tts_voice(lang: str) -> str:
    return "nova" if lang == "it" else "alloy"


async def _synthesize(text: str, lang: str) -> str:
    if not text:
        raise HTTPException(status_code=400, detail="Testo vuoto")
    text = text.strip()[:3800]
    try:
        tts = OpenAITextToSpeech(api_key=EMERGENT_LLM_KEY)
        audio_bytes = await tts.generate_speech(text=text, model="tts-1", voice=_tts_voice(lang), response_format="mp3")
        return base64.b64encode(audio_bytes).decode("ascii")
    except Exception as e:
        msg = str(e).lower()
        if "429" in msg or "rate" in msg or "concurrent" in msg:
            raise HTTPException(status_code=429, detail="Servizio audio momentaneamente sovraccarico. Riprova.")
        log.error(f"TTS error: {e}")
        raise HTTPException(status_code=502, detail="Errore audio.")


@router.post("/tts")
async def tts_endpoint(inp: TTSIn):
    text = inp.text
    lang = inp.language
    briefing_id = inp.briefing_id
    if briefing_id:
        cached = await db.tts_cache.find_one({"briefing_id": briefing_id}, {"_id": 0})
        if cached:
            return {"audio_base64": cached["audio_base64"], "mime": "audio/mpeg"}
        doc = await db.briefings.find_one({"id": briefing_id}, {"_id": 0})
        if not doc:
            raise HTTPException(status_code=404, detail="Notizia non trovata")
        lang = doc.get("language", lang)
        parts = [doc.get("headline", ""), doc.get("summary", "")]
        if doc.get("real_reasons"): parts.append(doc["real_reasons"])
        if doc.get("context"): parts.append(doc["context"])
        text = ". ".join([p for p in parts if p])
    if not text:
        raise HTTPException(status_code=400, detail="Testo mancante")
    audio_b64 = await _synthesize(text, lang)
    if briefing_id:
        await db.tts_cache.update_one(
            {"briefing_id": briefing_id},
            {"$set": {"briefing_id": briefing_id, "audio_base64": audio_b64,
                      "created_at": datetime.now(timezone.utc).isoformat()}},
            upsert=True,
        )
    return {"audio_base64": audio_b64, "mime": "audio/mpeg"}
