import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Request, Depends

from db import db
from models import (BriefingIn, BriefingItem, BriefingListOut, AskIn, AskOut,
                    ExplainIn, ExplainOut, ArticleQAIn, ArticleQA, DebateOut, DebateSide)
from llm import llm_json, llm_text, sys_for, new_session
from security import current_user
from services.ratelimit import check_rate, client_key

router = APIRouter(prefix="/api", tags=["news"])


# ---------- BRIEFINGS ----------
def _focus_prompt(topic: str, kind: str, source: Optional[str], language: str) -> str:
    if language == "en":
        if kind == "person":
            return f'recent news about the public figure "{topic}" — their statements, decisions, context around them.'
        if kind == "telegram":
            src = f' (telegram channel: {source})' if source else ""
            return f'recent news and content in the topic area of the telegram channel "{topic}"{src}. If you cannot access the channel directly, explicitly say you are reporting adjacent-topic news.'
        if kind == "hashtag":
            return f'recent conversations and news around the hashtag "{topic}" (or related topic area). If you cannot access social media in real time, describe the known phenomenon and discussed themes.'
        if kind == "channel":
            src = f' ({source})' if source else ""
            return f'recent news and outputs of the information channel "{topic}"{src}. If you cannot access it directly, report the channel\'s typical editorial area.'
        return f'news about the topic: "{topic}".'
    else:
        if kind == "person":
            return f'notizie recenti che riguardano la persona "{topic}" — sue dichiarazioni pubbliche, decisioni, contesto attorno.'
        if kind == "telegram":
            src = f' (canale telegram: {source})' if source else ""
            return f'notizie e contenuti recenti nell\'ambito del canale telegram "{topic}"{src}. Se non hai accesso diretto al canale, indica esplicitamente che stai riportando notizie affini all\'area tematica.'
        if kind == "hashtag":
            return f'conversazioni e notizie recenti attorno all\'hashtag "{topic}" (o area tematica correlata). Se non hai accesso ai social in tempo reale, descrivi il fenomeno noto e i temi discussi.'
        if kind == "channel":
            src = f' ({source})' if source else ""
            return f'notizie e uscite recenti del canale informativo "{topic}"{src}. Se non hai accesso diretto, riporta l\'area editoriale tipica del canale.'
        return f'notizie sull\'argomento: "{topic}".'


async def generate_briefing(topic: str, language: str, kind: str = "topic", source: Optional[str] = None) -> List[BriefingItem]:
    lang_label = "italiano" if language == "it" else "English"
    focus = _focus_prompt(topic, kind, source, language)
    if language == "en":
        prompt = f"""Generate 5 news briefings: {focus}
Priority: recent news (last 12 months) overlooked by mainstream media, concrete data, inventions, laws, discoveries, polls, real trends.
Answer ONLY in {lang_label}.

Respond STRICTLY with valid JSON:
{{
  "items": [
    {{
      "headline": "short clear title",
      "summary": "2-3 simple sentences (non-technical)",
      "key_facts": ["fact 1 with numbers/dates", "fact 2", "fact 3"],
      "sources_hint": ["source type"]
    }}
  ]
}}
No text outside the JSON. Do not invent specific data if uncertain."""
    else:
        prompt = f"""Genera 5 briefing di notizie: {focus}
Priorità: notizie recenti (ultimi 12 mesi) trascurate dai media mainstream, dati concreti, invenzioni, leggi, scoperte, sondaggi, tendenze reali.
Rispondi SOLO in {lang_label}.

Rispondi ESCLUSIVAMENTE con JSON valido:
{{
  "items": [
    {{
      "headline": "titolo breve e chiaro",
      "summary": "riassunto in 2-3 frasi semplici (adatte a persone non tecniche)",
      "key_facts": ["fatto 1 con numeri/date", "fatto 2", "fatto 3"],
      "sources_hint": ["tipo di fonte"]
    }}
  ]
}}
Nessun testo fuori dal JSON. Non inventare dati specifici se non ne sei sicuro."""
    session_id = new_session("briefing")
    data = await llm_json(session_id, sys_for(language), prompt)
    now = datetime.now(timezone.utc).isoformat()
    items = []
    for it in data.get("items", [])[:6]:
        items.append(BriefingItem(
            id=str(uuid.uuid4()),
            topic=topic,
            headline=it.get("headline", ""),
            summary=it.get("summary", ""),
            key_facts=it.get("key_facts", []) or [],
            sources_hint=it.get("sources_hint", []) or [],
            language=language,
            generated_at=now,
        ))
    return items


async def run_briefing(inp: BriefingIn) -> BriefingListOut:
    if not inp.refresh:
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=6)).isoformat()
        cached = await db.briefings.find({
            "topic": inp.topic, "language": inp.language, "generated_at": {"$gte": cutoff}
        }, {"_id": 0}).sort("generated_at", -1).to_list(6)
        if len(cached) >= 3:
            return BriefingListOut(topic=inp.topic, language=inp.language, items=[BriefingItem(**c) for c in cached[:6]])
    items = await generate_briefing(inp.topic, inp.language, kind=inp.kind or "topic", source=inp.source)
    if items:
        await db.briefings.insert_many([i.model_dump() for i in items])
    return BriefingListOut(topic=inp.topic, language=inp.language, items=items)


@router.post("/news/briefing", response_model=BriefingListOut)
async def news_briefing(inp: BriefingIn):
    return await run_briefing(inp)


@router.get("/news/item/{briefing_id}", response_model=BriefingItem)
async def get_item(briefing_id: str):
    doc = await db.briefings.find_one({"id": briefing_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Non trovato")
    return BriefingItem(**doc)


@router.post("/news/deep-dive/{briefing_id}", response_model=BriefingItem)
async def deep_dive(briefing_id: str):
    doc = await db.briefings.find_one({"id": briefing_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Non trovato")
    if doc.get("real_reasons"):
        return BriefingItem(**doc)
    language = doc.get("language", "it")
    lang_label = "italiano semplice" if language == "it" else "simple English"
    prompt = f"""Fai un approfondimento serio sulla seguente notizia. Rispondi SOLO in {lang_label}, con parole comprensibili a chi non è esperto.

TITOLO: {doc['headline']}
RIASSUNTO: {doc['summary']}
FATTI CHIAVE: {doc.get('key_facts')}

Rispondi con JSON valido:
{{
  "real_reasons": "spiegazione onesta dei veri motivi/interessi in gioco (3-5 frasi). Se non ci sono prove pubbliche, dillo chiaramente.",
  "data_points": ["dato numerico o statistica 1", "dato 2", "dato 3"],
  "context": "contesto storico e politico rilevante in 2-4 frasi semplici",
  "sources_hint": ["tipologia di fonti da consultare per verificare"]
}}
Solo JSON, nessun altro testo."""
    session = new_session(f"deepdive-{briefing_id}")
    data = await llm_json(session, sys_for(language), prompt)
    updates = {
        "real_reasons": data.get("real_reasons"),
        "data_points": data.get("data_points", []) or [],
        "context": data.get("context"),
        "sources_hint": (doc.get("sources_hint") or []) + (data.get("sources_hint", []) or []),
    }
    await db.briefings.update_one({"id": briefing_id}, {"$set": updates})
    doc.update(updates)
    return BriefingItem(**doc)


# ---------- ASK (freeform) ----------
@router.post("/ask", response_model=AskOut)
async def ask(inp: AskIn):
    lang_label = "italiano" if inp.language == "it" else "English"
    prompt = f"""Un utente ti chiede di approfondire questa richiesta/notizia:

"{inp.question}"

Rispondi SOLO in {lang_label}, in modo onesto, chiaro e non tecnico. Distingui fatti da opinioni. Se non hai dati recenti, dillo apertamente.

Rispondi con JSON valido:
{{
  "answer": "risposta completa in 4-8 frasi",
  "key_points": ["punto 1", "punto 2", "punto 3"],
  "caveats": ["limite/incertezza 1 (opzionale)"]
}}
Solo JSON."""
    session = new_session("ask")
    data = await llm_json(session, sys_for(inp.language), prompt)
    return AskOut(
        answer=data.get("answer", ""),
        key_points=data.get("key_points", []) or [],
        caveats=data.get("caveats", []) or [],
    )


# ---------- EXPLAIN WORD ----------
@router.post("/explain", response_model=ExplainOut)
async def explain_word(inp: ExplainIn):
    word = (inp.word or "").strip()
    if not word:
        raise HTTPException(status_code=400, detail="Parola mancante")
    if len(word) > 120:
        raise HTTPException(status_code=400, detail="Selezione troppo lunga")
    key = f"{inp.language}:{word.lower()}"
    cached = await db.explanations.find_one({"key": key}, {"_id": 0})
    if cached:
        return ExplainOut(word=word, explanation=cached["explanation"])
    lang_label = "italiano molto semplice, come parlassi a un anziano" if inp.language == "it" else "very simple English, as if explaining to a child"
    ctx = f"\nContesto in cui appare: \"{inp.context[:400]}\"" if inp.context else ""
    prompt = f"""Spiega in {lang_label} il significato di questa parola o espressione:

PAROLA: "{word}"{ctx}

Rispondi in massimo 2 frasi (max 45 parole totali). Nessuna introduzione, nessuna citazione. Solo la spiegazione chiara."""
    session = new_session("explain")
    txt = await llm_text(session, sys_for(inp.language), prompt)
    explanation = txt.strip().strip('"').strip("'")
    await db.explanations.update_one(
        {"key": key},
        {"$set": {"key": key, "word": word, "language": inp.language, "explanation": explanation}},
        upsert=True,
    )
    return ExplainOut(word=word, explanation=explanation)


# ---------- ARTICLE Q&A ----------
@router.get("/news/{briefing_id}/qa", response_model=List[ArticleQA])
async def list_article_qa(briefing_id: str):
    docs = await db.article_qas.find({"briefing_id": briefing_id}, {"_id": 0}).sort("created_at", -1).to_list(50)
    return [ArticleQA(**d) for d in docs]


@router.post("/news/{briefing_id}/qa", response_model=ArticleQA)
async def add_article_qa(briefing_id: str, inp: ArticleQAIn, request: Request, user=Depends(current_user)):
    ck = client_key(request, user)
    check_rate(f"qa-min:{ck}", max_events=3, window_seconds=60)
    check_rate(f"qa-hour:{ck}", max_events=20, window_seconds=3600)
    doc = await db.briefings.find_one({"id": briefing_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Notizia non trovata")
    language = doc.get("language", "it")
    lang_label = "italiano semplice" if language == "it" else "simple English"
    prompt = f"""L'utente ha una domanda specifica su questa notizia. Rispondi SOLO in {lang_label} in modo chiaro e onesto (max 5 frasi + punti chiave). Se non hai dati sufficienti dillo.

NOTIZIA:
Titolo: {doc.get('headline','')}
Riassunto: {doc.get('summary','')}
Fatti: {doc.get('key_facts',[])}
{'Motivi reali: ' + doc['real_reasons'] if doc.get('real_reasons') else ''}
{'Contesto: ' + doc['context'] if doc.get('context') else ''}

DOMANDA DELL'UTENTE: "{inp.question}"

Rispondi con JSON valido:
{{
  "answer": "risposta diretta, 3-5 frasi",
  "key_points": ["punto 1", "punto 2", "punto 3"]
}}
Solo JSON."""
    session = new_session(f"qa-{briefing_id}")
    data = await llm_json(session, sys_for(language), prompt)
    qa = {
        "id": str(uuid.uuid4()),
        "briefing_id": briefing_id,
        "question": inp.question.strip(),
        "answer": data.get("answer", ""),
        "key_points": data.get("key_points", []) or [],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "author_id": user["id"] if user else None,
        "author_name": (user.get("name") or user["email"].split("@")[0]) if user else None,
    }
    await db.article_qas.insert_one(qa)
    return ArticleQA(**qa)


# ---------- DEBATE ----------
@router.post("/news/{briefing_id}/debate", response_model=DebateOut)
async def debate(briefing_id: str, refresh: bool = False):
    doc = await db.briefings.find_one({"id": briefing_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Notizia non trovata")
    language = doc.get("language", "it")
    if not refresh:
        cached = await db.debates.find_one({"briefing_id": briefing_id, "language": {"$in": [None, language]}}, {"_id": 0})
        if cached:
            return DebateOut(**cached)
    lang_label = "italiano" if language == "it" else "English"
    prompt = f"""Simula un dibattito serio tra 3 punti di vista contrastanti ma competenti sulla seguente notizia. Non fare macchiette: ognuno deve avere una posizione difendibile con argomenti sostanziali.

NOTIZIA:
Titolo: {doc.get('headline','')}
Riassunto: {doc.get('summary','')}
Fatti: {doc.get('key_facts',[])}

Scegli 3 personaggi/ruoli reali e distinti. Rispondi SOLO in {lang_label}.

Rispondi con JSON valido:
{{
  "sides": [
    {{"persona": "Ruolo/tipo di esperto 1", "stance": "tesi sintetica in 1 frase", "arguments": ["arg 1 con dati/logica", "arg 2", "arg 3"]}},
    {{"persona": "Ruolo 2", "stance": "tesi in contrasto", "arguments": ["arg 1", "arg 2", "arg 3"]}},
    {{"persona": "Ruolo 3", "stance": "prospettiva alternativa", "arguments": ["arg 1", "arg 2", "arg 3"]}}
  ],
  "synthesis": "3-4 frasi che evidenziano punti di accordo e disaccordo genuini, senza appiattire"
}}
Solo JSON."""
    session = new_session(f"debate-{briefing_id}")
    data = await llm_json(session, sys_for(language), prompt)
    sides = [DebateSide(**s) for s in data.get("sides", [])[:4]]
    out = DebateOut(
        briefing_id=briefing_id,
        sides=sides,
        synthesis=data.get("synthesis", ""),
        language=language,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )
    await db.debates.update_one({"briefing_id": briefing_id, "language": out.language}, {"$set": out.model_dump()}, upsert=True)
    return out
