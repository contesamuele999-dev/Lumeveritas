from fastapi import FastAPI, APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os, logging, uuid, json, asyncio
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Literal
from datetime import datetime, timezone, timedelta
import bcrypt, jwt

from emergentintegrations.llm.chat import LlmChat, UserMessage

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

MONGO_URL = os.environ['MONGO_URL']
DB_NAME = os.environ['DB_NAME']
EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY', '')
JWT_SECRET = os.environ.get('JWT_SECRET', 'dev-secret')
JWT_ALG = 'HS256'
JWT_EXPIRE_DAYS = 30

client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

app = FastAPI(title="Lume Veritas API")
api = APIRouter(prefix="/api")
security = HTTPBearer(auto_error=False)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log = logging.getLogger("lume")

# ------------------ MODELS ------------------
class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    name: Optional[str] = None

class LoginIn(BaseModel):
    email: EmailStr
    password: str

class UserOut(BaseModel):
    id: str
    email: str
    name: Optional[str] = None
    preferred_topics: List[str] = []
    language: str = "it"

class TokenOut(BaseModel):
    token: str
    user: UserOut

class PreferencesIn(BaseModel):
    preferred_topics: Optional[List[str]] = None
    language: Optional[Literal["it", "en"]] = None

class BriefingIn(BaseModel):
    topic: str
    language: Literal["it", "en"] = "it"
    depth: Literal["short", "deep"] = "short"
    refresh: bool = False

class BriefingItem(BaseModel):
    id: str
    topic: str
    headline: str
    summary: str
    key_facts: List[str] = []
    sources_hint: List[str] = []
    real_reasons: Optional[str] = None
    data_points: List[str] = []
    context: Optional[str] = None
    language: str
    generated_at: str

class BriefingListOut(BaseModel):
    topic: str
    language: str
    items: List[BriefingItem]

class AskIn(BaseModel):
    question: str
    language: Literal["it", "en"] = "it"

class AskOut(BaseModel):
    answer: str
    key_points: List[str] = []
    caveats: List[str] = []

class SaveItemIn(BaseModel):
    briefing_id: str

class ExplainIn(BaseModel):
    word: str
    context: Optional[str] = None
    language: Literal["it", "en"] = "it"

class ExplainOut(BaseModel):
    word: str
    explanation: str

# ------------------ AUTH HELPERS ------------------
def hash_pw(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()

def verify_pw(pw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(pw.encode(), hashed.encode())
    except Exception:
        return False

def make_token(user_id: str) -> str:
    payload = {"sub": user_id, "exp": datetime.now(timezone.utc) + timedelta(days=JWT_EXPIRE_DAYS)}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)

async def current_user(creds: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    if not creds:
        return None
    try:
        payload = jwt.decode(creds.credentials, JWT_SECRET, algorithms=[JWT_ALG])
        uid = payload.get("sub")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")
    doc = await db.users.find_one({"id": uid}, {"_id": 0, "password_hash": 0})
    if not doc:
        raise HTTPException(status_code=401, detail="User not found")
    return doc

async def require_user(user = Depends(current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Auth required")
    return user

# ------------------ TOPICS ------------------
DEFAULT_TOPICS = [
    {"key": "mercati", "label_it": "Mercati", "label_en": "Markets"},
    {"key": "popolazione", "label_it": "Tendenze popolazione", "label_en": "Population Trends"},
    {"key": "sondaggi", "label_it": "Sondaggi", "label_en": "Polls & Surveys"},
    {"key": "statistiche", "label_it": "Statistiche", "label_en": "Statistics"},
    {"key": "invenzioni", "label_it": "Invenzioni", "label_en": "Inventions"},
    {"key": "leggi", "label_it": "Leggi approvate", "label_en": "Laws Passed"},
    {"key": "scienza", "label_it": "Scoperte scientifiche", "label_en": "Scientific Discoveries"},
    {"key": "politica", "label_it": "Scelte politiche", "label_en": "Political Choices"},
    {"key": "guerre", "label_it": "Guerre e veri motivi", "label_en": "Wars & Real Reasons"},
    {"key": "salute", "label_it": "Salute", "label_en": "Health"},
    {"key": "tecnologia", "label_it": "Tecnologia", "label_en": "Technology"},
    {"key": "ambiente", "label_it": "Ambiente", "label_en": "Environment"},
    {"key": "economia", "label_it": "Economia", "label_en": "Economy"},
    {"key": "geopolitica", "label_it": "Geopolitica", "label_en": "Geopolitics"},
    {"key": "societa", "label_it": "Cultura & Società", "label_en": "Culture & Society"},
    {"key": "cripto", "label_it": "Cripto & Finanza Alt.", "label_en": "Crypto & Alt Finance"},
]

# ------------------ LLM ------------------
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
    chat = LlmChat(api_key=EMERGENT_LLM_KEY, session_id=session_id, system_message=system).with_model("gemini", "gemini-3-flash-preview")
    try:
        resp = await chat.send_message(UserMessage(text=user_text))
    except Exception as e:
        msg = str(e).lower()
        if "429" in msg or "rate" in msg or "concurrent" in msg or "limit" in msg:
            raise HTTPException(status_code=429, detail="Il servizio IA è momentaneamente sovraccarico. Riprova tra qualche secondo.")
        log.error(f"LLM error: {e}")
        raise HTTPException(status_code=502, detail="Errore dal servizio IA. Riprova.")
    return resp if isinstance(resp, str) else str(resp)

async def llm_json(session_id: str, system: str, user_text: str) -> dict:
    text = await llm_text(session_id, system, user_text)
    # try to extract JSON
    start = text.find('{')
    end = text.rfind('}')
    if start >= 0 and end > start:
        try:
            return json.loads(text[start:end+1])
        except Exception:
            pass
    # try to extract array
    s2 = text.find('[')
    e2 = text.rfind(']')
    if s2 >= 0 and e2 > s2:
        try:
            return {"items": json.loads(text[s2:e2+1])}
        except Exception:
            pass
    raise HTTPException(status_code=502, detail="AI parse error")

# ------------------ ROUTES ------------------
@api.get("/")
async def root():
    return {"ok": True, "app": "Lume Veritas"}

@api.get("/topics")
async def get_topics():
    return DEFAULT_TOPICS

# --- AUTH ---
@api.post("/auth/register", response_model=TokenOut)
async def register(inp: RegisterIn):
    existing = await db.users.find_one({"email": inp.email.lower()})
    if existing:
        raise HTTPException(status_code=400, detail="Email già registrata")
    uid = str(uuid.uuid4())
    doc = {
        "id": uid,
        "email": inp.email.lower(),
        "name": inp.name or inp.email.split("@")[0],
        "password_hash": hash_pw(inp.password),
        "preferred_topics": [t["key"] for t in DEFAULT_TOPICS[:6]],
        "language": "it",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.users.insert_one(doc)
    token = make_token(uid)
    return TokenOut(token=token, user=UserOut(id=uid, email=doc["email"], name=doc["name"], preferred_topics=doc["preferred_topics"], language=doc["language"]))

@api.post("/auth/login", response_model=TokenOut)
async def login(inp: LoginIn):
    doc = await db.users.find_one({"email": inp.email.lower()})
    if not doc or not verify_pw(inp.password, doc.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Credenziali non valide")
    token = make_token(doc["id"])
    return TokenOut(token=token, user=UserOut(
        id=doc["id"], email=doc["email"], name=doc.get("name"),
        preferred_topics=doc.get("preferred_topics", []), language=doc.get("language", "it")))

@api.get("/auth/me", response_model=UserOut)
async def me(user = Depends(require_user)):
    return UserOut(id=user["id"], email=user["email"], name=user.get("name"),
                   preferred_topics=user.get("preferred_topics", []),
                   language=user.get("language", "it"))

@api.put("/auth/preferences", response_model=UserOut)
async def update_prefs(inp: PreferencesIn, user = Depends(require_user)):
    updates = {}
    if inp.preferred_topics is not None:
        updates["preferred_topics"] = inp.preferred_topics
    if inp.language is not None:
        updates["language"] = inp.language
    if updates:
        await db.users.update_one({"id": user["id"]}, {"$set": updates})
    doc = await db.users.find_one({"id": user["id"]}, {"_id": 0, "password_hash": 0})
    return UserOut(id=doc["id"], email=doc["email"], name=doc.get("name"),
                   preferred_topics=doc.get("preferred_topics", []),
                   language=doc.get("language", "it"))

# --- NEWS / BRIEFINGS ---
async def generate_briefing(topic: str, language: str) -> List[BriefingItem]:
    lang_label = "italiano" if language == "it" else "English"
    prompt = f"""Genera 5 briefing di notizie sull'argomento: "{topic}".
Priorità: notizie recenti (ultimi 12 mesi) trascurate dai media mainstream, dati concreti, invenzioni, leggi, scoperte, sondaggi, tendenze reali.
Rispondi SOLO in {lang_label}.

Rispondi ESCLUSIVAMENTE con JSON valido in questa forma esatta:
{{
  "items": [
    {{
      "headline": "titolo breve e chiaro",
      "summary": "riassunto in 2-3 frasi semplici (adatte a persone non tecniche)",
      "key_facts": ["fatto 1 con numeri/date", "fatto 2", "fatto 3"],
      "sources_hint": ["tipo di fonte (es: rapporto ONU 2024, studio Lancet, dati Eurostat)"]
    }}
  ]
}}
Non inserire testo fuori dal JSON. Non inventare dati specifici se non ne sei sicuro: in tal caso ometti il campo."""
    session_id = f"briefing-{uuid.uuid4()}"
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

@api.post("/news/briefing", response_model=BriefingListOut)
async def news_briefing(inp: BriefingIn):
    # cache: 6 hours
    if not inp.refresh:
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=6)).isoformat()
        cached = await db.briefings.find({
            "topic": inp.topic, "language": inp.language, "generated_at": {"$gte": cutoff}
        }, {"_id": 0}).sort("generated_at", -1).to_list(6)
        if len(cached) >= 3:
            return BriefingListOut(topic=inp.topic, language=inp.language, items=[BriefingItem(**c) for c in cached[:6]])
    items = await generate_briefing(inp.topic, inp.language)
    if items:
        await db.briefings.insert_many([i.model_dump() for i in items])
    return BriefingListOut(topic=inp.topic, language=inp.language, items=items)

@api.get("/news/item/{briefing_id}", response_model=BriefingItem)
async def get_item(briefing_id: str):
    doc = await db.briefings.find_one({"id": briefing_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Non trovato")
    return BriefingItem(**doc)

@api.post("/news/deep-dive/{briefing_id}", response_model=BriefingItem)
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
    session = f"deepdive-{briefing_id}"
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

@api.post("/ask", response_model=AskOut)
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
    session = f"ask-{uuid.uuid4()}"
    data = await llm_json(session, sys_for(inp.language), prompt)
    return AskOut(
        answer=data.get("answer", ""),
        key_points=data.get("key_points", []) or [],
        caveats=data.get("caveats", []) or [],
    )

# --- WORD / TERM EXPLAIN ---
@api.post("/explain", response_model=ExplainOut)
async def explain_word(inp: ExplainIn):
    word = (inp.word or "").strip()
    if not word:
        raise HTTPException(status_code=400, detail="Parola mancante")
    if len(word) > 120:
        raise HTTPException(status_code=400, detail="Selezione troppo lunga")
    # cache 30 days
    key = f"{inp.language}:{word.lower()}"
    cached = await db.explanations.find_one({"key": key}, {"_id": 0})
    if cached:
        return ExplainOut(word=word, explanation=cached["explanation"])
    lang_label = "italiano molto semplice, come parlassi a un anziano" if inp.language == "it" else "very simple English, as if explaining to a child"
    ctx = f"\nContesto in cui appare: \"{inp.context[:400]}\"" if inp.context else ""
    prompt = f"""Spiega in {lang_label} il significato di questa parola o espressione:

PAROLA: "{word}"{ctx}

Rispondi in massimo 2 frasi (max 45 parole totali). Nessuna introduzione, nessuna citazione. Solo la spiegazione chiara."""
    session = f"explain-{uuid.uuid4()}"
    txt = await llm_text(session, sys_for(inp.language), prompt)
    explanation = txt.strip().strip('"').strip("'")
    await db.explanations.update_one(
        {"key": key},
        {"$set": {"key": key, "word": word, "language": inp.language, "explanation": explanation}},
        upsert=True,
    )
    return ExplainOut(word=word, explanation=explanation)

# --- SAVED ---
@api.post("/saved/add")
async def save_item(inp: SaveItemIn, user = Depends(require_user)):
    b = await db.briefings.find_one({"id": inp.briefing_id}, {"_id": 0})
    if not b:
        raise HTTPException(status_code=404, detail="Notizia non trovata")
    await db.saved.update_one(
        {"user_id": user["id"], "briefing_id": inp.briefing_id},
        {"$set": {"user_id": user["id"], "briefing_id": inp.briefing_id, "saved_at": datetime.now(timezone.utc).isoformat()}},
        upsert=True,
    )
    return {"ok": True}

@api.delete("/saved/{briefing_id}")
async def unsave(briefing_id: str, user = Depends(require_user)):
    await db.saved.delete_one({"user_id": user["id"], "briefing_id": briefing_id})
    return {"ok": True}

@api.get("/saved", response_model=List[BriefingItem])
async def list_saved(user = Depends(require_user)):
    saved = await db.saved.find({"user_id": user["id"]}, {"_id": 0}).sort("saved_at", -1).to_list(200)
    ids = [s["briefing_id"] for s in saved]
    if not ids:
        return []
    docs = await db.briefings.find({"id": {"$in": ids}}, {"_id": 0}).to_list(200)
    by_id = {d["id"]: d for d in docs}
    return [BriefingItem(**by_id[i]) for i in ids if i in by_id]

app.include_router(api)
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def _shutdown():
    client.close()
