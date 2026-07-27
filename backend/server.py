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
from emergentintegrations.llm.openai import OpenAITextToSpeech
import base64, resend, feedparser, io
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from PIL import Image, ImageDraw, ImageFont
from fastapi.responses import Response

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

MONGO_URL = os.environ['MONGO_URL']
DB_NAME = os.environ['DB_NAME']
EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY', '')
JWT_SECRET = os.environ.get('JWT_SECRET', 'dev-secret')
JWT_ALG = 'HS256'
JWT_EXPIRE_DAYS = 30
RESEND_API_KEY = os.environ.get('RESEND_API_KEY', '')
SENDER_EMAIL = os.environ.get('SENDER_EMAIL', 'Lume Veritas <onboarding@resend.dev>')
PUBLIC_APP_URL = os.environ.get('PUBLIC_APP_URL', '')
if RESEND_API_KEY:
    resend.api_key = RESEND_API_KEY

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
    views: int = 0

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

class CustomTopicIn(BaseModel):
    label: str = Field(min_length=2, max_length=48)

class CustomTopic(BaseModel):
    key: str
    label_it: str
    label_en: str
    custom: bool = True

class DigestPrefIn(BaseModel):
    enabled: bool

class TTSIn(BaseModel):
    text: Optional[str] = None
    briefing_id: Optional[str] = None
    language: Literal["it", "en"] = "it"

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

def _slugify(txt: str) -> str:
    import re, unicodedata
    txt = unicodedata.normalize("NFKD", txt).encode("ascii", "ignore").decode()
    txt = re.sub(r"[^a-zA-Z0-9]+", "-", txt).strip("-").lower()
    return txt[:40] or "topic"

@api.get("/topics/mine", response_model=List[CustomTopic])
async def get_my_topics(user = Depends(require_user)):
    doc = await db.users.find_one({"id": user["id"]}, {"_id": 0, "custom_topics": 1})
    return [CustomTopic(**t) for t in (doc or {}).get("custom_topics", [])]

@api.post("/topics/custom", response_model=CustomTopic)
async def add_custom_topic(inp: CustomTopicIn, user = Depends(require_user)):
    label = inp.label.strip()
    if len(label) < 2:
        raise HTTPException(status_code=400, detail="Etichetta troppo corta")
    key = f"custom-{_slugify(label)}"
    doc = await db.users.find_one({"id": user["id"]}, {"_id": 0, "custom_topics": 1, "preferred_topics": 1})
    existing = (doc or {}).get("custom_topics", [])
    if len(existing) >= 30:
        raise HTTPException(status_code=400, detail="Hai raggiunto il limite di 30 argomenti personalizzati")
    # dedupe by key
    if any(t.get("key") == key for t in existing):
        for t in existing:
            if t.get("key") == key:
                return CustomTopic(**t)
    # ask LLM for EN translation (small call). If it fails, keep the same label.
    label_en = label
    try:
        session = f"topic-tr-{uuid.uuid4()}"
        prompt = f'Translate this news topic to English (max 4 words, return only the translation, no quotes): "{label}"'
        tx = await llm_text(session, "You translate short topic names.", prompt)
        cand = tx.strip().strip('"').strip("'").split("\n")[0]
        if 2 <= len(cand) <= 60:
            label_en = cand
    except Exception:
        pass
    new_topic = {"key": key, "label_it": label, "label_en": label_en, "custom": True}
    new_list = existing + [new_topic]
    # auto-add to preferred_topics
    new_prefs = list(dict.fromkeys((doc or {}).get("preferred_topics", []) + [key]))
    await db.users.update_one({"id": user["id"]}, {"$set": {"custom_topics": new_list, "preferred_topics": new_prefs}})
    return CustomTopic(**new_topic)

@api.delete("/topics/custom/{topic_key}")
async def remove_custom_topic(topic_key: str, user = Depends(require_user)):
    doc = await db.users.find_one({"id": user["id"]}, {"_id": 0, "custom_topics": 1, "preferred_topics": 1})
    existing = (doc or {}).get("custom_topics", [])
    new_list = [t for t in existing if t.get("key") != topic_key]
    new_prefs = [k for k in (doc or {}).get("preferred_topics", []) if k != topic_key]
    await db.users.update_one({"id": user["id"]}, {"$set": {"custom_topics": new_list, "preferred_topics": new_prefs}})
    return {"ok": True}

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

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== RSS ====================
RSS_FEEDS = {
    "mercati": [
        "https://www.zerohedge.com/fullrss2.xml",
        "https://feeds.marketwatch.com/marketwatch/topstories/",
    ],
    "economia": [
        "https://www.zerohedge.com/fullrss2.xml",
        "https://feeds.marketwatch.com/marketwatch/topstories/",
    ],
    "cripto": [
        "https://cointelegraph.com/rss",
        "https://bitcoinmagazine.com/.rss/full/",
    ],
    "scienza": [
        "https://www.sciencedaily.com/rss/all.xml",
        "https://phys.org/rss-feed/",
    ],
    "tecnologia": [
        "https://feeds.arstechnica.com/arstechnica/index/",
        "https://www.theregister.com/headlines.atom",
    ],
    "invenzioni": [
        "https://phys.org/rss-feed/technology-news/",
        "https://feeds.arstechnica.com/arstechnica/science/",
    ],
    "salute": [
        "https://feeds.feedburner.com/naturalnews/Health",
        "https://www.who.int/rss-feeds/news-english.xml",
    ],
    "ambiente": [
        "https://feeds.feedburner.com/climatedepot",
        "https://phys.org/rss-feed/earth-news/",
    ],
    "geopolitica": [
        "https://www.consortiumnews.com/feed/",
        "https://caitlinjohnstone.com/feed/",
        "https://moonofalabama.org/index.rdf",
    ],
    "guerre": [
        "https://www.consortiumnews.com/feed/",
        "https://moonofalabama.org/index.rdf",
        "https://caitlinjohnstone.com/feed/",
    ],
    "politica": [
        "https://www.commondreams.org/rss.xml",
        "https://truthout.org/feed/?withoutcomments=1",
    ],
    "leggi": [
        "https://www.commondreams.org/rss.xml",
        "https://truthout.org/feed/?withoutcomments=1",
    ],
    "sondaggi": [
        "https://news.gallup.com/rss/RSS.aspx?e=politics",
        "https://www.pewresearch.org/feed/",
    ],
    "statistiche": [
        "https://ourworldindata.org/atom.xml",
        "https://www.pewresearch.org/feed/",
    ],
    "popolazione": [
        "https://ourworldindata.org/atom.xml",
        "https://www.pewresearch.org/feed/",
    ],
    "societa": [
        "https://www.commondreams.org/rss.xml",
        "https://www.pewresearch.org/feed/",
    ],
}

TOPIC_KEY_BY_LABEL = {t["label_it"].lower(): t["key"] for t in DEFAULT_TOPICS}
TOPIC_KEY_BY_LABEL.update({t["label_en"].lower(): t["key"] for t in DEFAULT_TOPICS})

def _clean_summary(s: str, limit: int = 320) -> str:
    if not s:
        return ""
    import re
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

@api.get("/rss/feed")
async def rss_feed(topic: str, limit: int = 10):
    key = TOPIC_KEY_BY_LABEL.get(topic.lower(), topic.lower())
    urls = RSS_FEEDS.get(key, [])
    if not urls:
        return {"topic": topic, "items": []}
    results = await asyncio.gather(*[_fetch_feed(u) for u in urls])
    merged = []
    for r in results:
        merged.extend(r)
    # dedup by title
    seen, out = set(), []
    for item in merged:
        t = item["title"].lower()
        if t and t not in seen:
            seen.add(t)
            out.append(item)
    return {"topic": topic, "items": out[:limit]}

# ==================== TTS ====================
def _tts_voice(lang: str) -> str:
    return "nova" if lang == "it" else "alloy"

async def _synthesize(text: str, lang: str) -> str:
    """Return base64 mp3."""
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

@api.post("/tts")
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
            {"$set": {"briefing_id": briefing_id, "audio_base64": audio_b64, "created_at": datetime.now(timezone.utc).isoformat()}},
            upsert=True,
        )
    return {"audio_base64": audio_b64, "mime": "audio/mpeg"}

# ==================== PUBLIC SHARE ====================
@api.get("/public/{briefing_id}", response_model=BriefingItem)
async def public_briefing(briefing_id: str):
    doc = await db.briefings.find_one({"id": briefing_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Notizia non trovata")
    # ensure deep-dive fields exist for public sharing — generate on demand
    if not doc.get("real_reasons"):
        try:
            await deep_dive(briefing_id)
            doc = await db.briefings.find_one({"id": briefing_id}, {"_id": 0})
        except Exception as e:
            log.warning(f"public deep-dive skipped: {e}")
    # increment view counter (fire-and-forget)
    try:
        await db.briefings.update_one({"id": briefing_id}, {"$inc": {"views": 1}})
        doc["views"] = int(doc.get("views", 0)) + 1
    except Exception:
        pass
    return BriefingItem(**doc)

@api.get("/public/{briefing_id}/views")
async def public_briefing_views(briefing_id: str):
    doc = await db.briefings.find_one({"id": briefing_id}, {"_id": 0, "views": 1})
    if not doc:
        raise HTTPException(status_code=404, detail="Non trovato")
    return {"views": int(doc.get("views", 0))}

# ==================== OG IMAGE ====================
_OG_FONT_SERIF = "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf"
_OG_FONT_SANS = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
_OG_FONT_MONO = "/usr/share/fonts/truetype/liberation/LiberationMono-Bold.ttf"

def _wrap_text(draw, text, font, max_width):
    words = text.split()
    lines, cur = [], ""
    for w in words:
        test = (cur + " " + w).strip()
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] > max_width and cur:
            lines.append(cur)
            cur = w
        else:
            cur = test
    if cur:
        lines.append(cur)
    return lines

def _render_og_image(topic: str, headline: str, published_iso: Optional[str] = None) -> bytes:
    W, H = 1200, 630
    bg = (249, 249, 246)
    fg = (17, 17, 17)
    accent = (217, 56, 30)
    muted = (110, 110, 100)
    img = Image.new("RGB", (W, H), bg)
    draw = ImageDraw.Draw(img)
    # subtle grain via a few random-ish specks
    for i in range(300):
        x = (i * 37) % W
        y = (i * 91) % H
        draw.point((x, y), fill=(230, 230, 220))
    # border
    pad = 48
    draw.rectangle([pad, pad, W - pad, H - pad], outline=fg, width=2)
    # top row: brand + topic
    try:
        f_mono = ImageFont.truetype(_OG_FONT_MONO, 22)
        f_title = ImageFont.truetype(_OG_FONT_SERIF, 64)
        f_kicker = ImageFont.truetype(_OG_FONT_SANS, 20)
    except Exception:
        f_mono = ImageFont.load_default()
        f_title = ImageFont.load_default()
        f_kicker = ImageFont.load_default()
    # Brand mark
    box = 64
    draw.rectangle([pad + 40, pad + 40, pad + 40 + box, pad + 40 + box], fill=fg)
    draw.text((pad + 40 + 22, pad + 40 + 10), "L", font=f_title, fill=bg)
    draw.text((pad + 40 + box + 20, pad + 48), "LUME VERITAS", font=f_mono, fill=fg)
    draw.text((pad + 40 + box + 20, pad + 78), "le notizie che i giornali trascurano", font=f_kicker, fill=muted)
    # topic pill (top-right)
    topic_up = (topic or "").upper()[:36]
    tw = draw.textbbox((0, 0), topic_up, font=f_mono)
    pill_w = tw[2] - tw[0] + 32
    px1 = W - pad - 40 - pill_w
    py1 = pad + 46
    draw.rectangle([px1, py1, W - pad - 40, py1 + 40], fill=accent)
    draw.text((px1 + 16, py1 + 8), topic_up, font=f_mono, fill=(255, 255, 255))
    # headline
    max_w = W - 2 * (pad + 40)
    lines = _wrap_text(draw, headline, f_title, max_w)[:5]
    y = pad + 200
    for ln in lines:
        draw.text((pad + 40, y), ln, font=f_title, fill=fg)
        y += 78
    # bottom rule + CTA
    draw.line([(pad + 40, H - pad - 90), (W - pad - 40, H - pad - 90)], fill=fg, width=2)
    draw.text((pad + 40, H - pad - 70), "APPROFONDISCI SU LUME.VERITAS", font=f_mono, fill=fg)
    if published_iso:
        try:
            ts = datetime.fromisoformat(published_iso.replace("Z", "+00:00")).strftime("%d.%m.%Y").upper()
        except Exception:
            ts = datetime.now(timezone.utc).strftime("%d.%m.%Y").upper()
    else:
        ts = datetime.now(timezone.utc).strftime("%d.%m.%Y").upper()
    tsw = draw.textbbox((0, 0), ts, font=f_mono)
    draw.text((W - pad - 40 - (tsw[2] - tsw[0]), H - pad - 70), ts, font=f_mono, fill=muted)
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()

@api.get("/og/{briefing_id}.png")
async def og_image(briefing_id: str):
    doc = await db.briefings.find_one({"id": briefing_id}, {"_id": 0, "topic": 1, "headline": 1, "generated_at": 1})
    if not doc:
        png = _render_og_image("LUME VERITAS", "Le notizie che i giornali trascurano.")
    else:
        png = _render_og_image(doc.get("topic", ""), doc.get("headline", ""), doc.get("generated_at"))
    return Response(content=png, media_type="image/png", headers={"Cache-Control": "public, max-age=86400"})

# ==================== EMAIL DIGEST ====================
def _digest_html(user_name: str, lang: str, sections: list) -> str:
    lbl_hello = "Ciao" if lang == "it" else "Hi"
    lbl_title = "Il tuo digest quotidiano" if lang == "it" else "Your daily digest"
    lbl_open = "Apri l'app" if lang == "it" else "Open the app"
    lbl_footer = ("Ricevi questa email perché hai attivato il digest su Lume Veritas. "
                  "Per disattivarlo, vai su Profilo → Digest.") if lang == "it" else \
                 ("You get this because you enabled digest on Lume Veritas. Disable it in Profile → Digest.")
    blocks = []
    for sec in sections:
        items_html = "".join(
            f"""<tr><td style="padding:12px 0;border-bottom:1px solid #e2e2d9;">
                <div style="font-family:Georgia,serif;font-size:20px;line-height:1.25;color:#111;margin-bottom:6px;">{it['headline']}</div>
                <div style="font-family:Arial,sans-serif;font-size:14px;color:#444;line-height:1.5;">{it['summary']}</div>
            </td></tr>"""
            for it in sec["items"][:3]
        )
        blocks.append(f"""
        <tr><td style="padding:24px 0 8px;">
            <div style="font-family:Arial,sans-serif;font-size:11px;letter-spacing:0.15em;text-transform:uppercase;color:#D9381E;">{sec['topic']}</div>
        </td></tr>
        {items_html}
        """)
    return f"""<!doctype html>
<html><body style="margin:0;padding:0;background:#f9f9f6;">
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#f9f9f6;padding:32px 0;">
<tr><td align="center">
<table role="presentation" width="600" cellspacing="0" cellpadding="0" style="background:#ffffff;border:1px solid #e2e2d9;">
<tr><td style="padding:32px 32px 8px;">
<div style="font-family:Arial,sans-serif;font-size:11px;letter-spacing:0.15em;text-transform:uppercase;color:#D9381E;">LUME VERITAS</div>
<div style="font-family:Georgia,serif;font-size:28px;line-height:1.15;color:#111;margin-top:8px;">{lbl_title}</div>
<div style="font-family:Arial,sans-serif;font-size:14px;color:#666;margin-top:6px;">{lbl_hello} {user_name},</div>
</td></tr>
<tr><td style="padding:0 32px 24px;">
<table role="presentation" width="100%" cellspacing="0" cellpadding="0">{''.join(blocks)}</table>
<div style="padding:24px 0 8px;">
<a href="{PUBLIC_APP_URL}" style="display:inline-block;background:#111;color:#fff;text-decoration:none;padding:14px 22px;font-family:Arial,sans-serif;font-size:12px;letter-spacing:0.15em;text-transform:uppercase;">{lbl_open}</a>
</div>
</td></tr>
<tr><td style="padding:16px 32px 32px;border-top:1px solid #e2e2d9;">
<div style="font-family:Arial,sans-serif;font-size:11px;color:#999;line-height:1.5;">{lbl_footer}</div>
</td></tr>
</table>
</td></tr>
</table>
</body></html>"""

async def build_digest_for_user(user_doc: dict) -> Optional[dict]:
    lang = user_doc.get("language", "it")
    topic_keys = user_doc.get("preferred_topics") or [t["key"] for t in DEFAULT_TOPICS[:4]]
    topic_keys = topic_keys[:4]
    sections = []
    for k in topic_keys:
        topic_meta = next((t for t in DEFAULT_TOPICS if t["key"] == k), None)
        if not topic_meta: continue
        label = topic_meta["label_it"] if lang == "it" else topic_meta["label_en"]
        try:
            res = await news_briefing(BriefingIn(topic=label, language=lang, refresh=False))
            if res.items:
                sections.append({"topic": label, "items": [i.model_dump() for i in res.items[:3]]})
        except Exception as e:
            log.warning(f"digest section failed {k}: {e}")
    if not sections:
        return None
    return {"lang": lang, "html": _digest_html(user_doc.get("name") or user_doc["email"].split("@")[0], lang, sections)}

async def send_digest_to_user(user_doc: dict) -> tuple[bool, Optional[str]]:
    if not RESEND_API_KEY:
        return False, "resend_key_missing"
    payload = await build_digest_for_user(user_doc)
    if not payload:
        return False, "no_content"
    subject = "Lume Veritas — Il tuo digest quotidiano" if payload["lang"] == "it" else "Lume Veritas — Your daily digest"
    params = {
        "from": SENDER_EMAIL,
        "to": [user_doc["email"]],
        "subject": subject,
        "html": payload["html"],
    }
    try:
        r = await asyncio.to_thread(resend.Emails.send, params)
        await db.digest_log.insert_one({
            "user_id": user_doc["id"], "email": user_doc["email"],
            "sent_at": datetime.now(timezone.utc).isoformat(),
            "resend_id": (r or {}).get("id"),
        })
        return True, None
    except Exception as e:
        msg = str(e)
        log.error(f"Resend send failed to {user_doc['email']}: {msg}")
        return False, msg[:220]

async def run_daily_digest():
    log.info("Running daily digest job")
    cursor = db.users.find({"digest_enabled": True}, {"_id": 0, "password_hash": 0})
    users = await cursor.to_list(1000)
    log.info(f"Digest recipients: {len(users)}")
    for u in users:
        try:
            await send_digest_to_user(u)
            await asyncio.sleep(2)
        except Exception as e:
            log.error(f"digest error for {u.get('email')}: {e}")

@api.put("/digest/preferences")
async def digest_prefs(inp: DigestPrefIn, user = Depends(require_user)):
    await db.users.update_one({"id": user["id"]}, {"$set": {"digest_enabled": inp.enabled}})
    return {"ok": True, "digest_enabled": inp.enabled}

@api.post("/digest/send-now")
async def digest_send_now(user = Depends(require_user)):
    ok, err = await send_digest_to_user(user)
    if not ok:
        # Return 200 with ok:false so the JSON body reaches the client
        # (ingress strips bodies on >=502 responses).
        msg = ("Il servizio email non ha accettato l'invio. "
               "In modalità test Resend può inviare solo alla mail del proprietario dell'account: "
               "verifica un dominio su resend.com/domains per inviare a chiunque.")
        return {"ok": False, "error": err or "unknown", "message": msg}
    return {"ok": True, "email": user["email"]}

# --- extend UserOut to include digest flag ---
@api.get("/auth/me/full")
async def me_full(user = Depends(require_user)):
    return {
        "id": user["id"], "email": user["email"], "name": user.get("name"),
        "preferred_topics": user.get("preferred_topics", []),
        "language": user.get("language", "it"),
        "digest_enabled": bool(user.get("digest_enabled", False)),
        "custom_topics": user.get("custom_topics", []),
    }

# ==================== SCHEDULER ====================
scheduler: Optional[AsyncIOScheduler] = None

@app.on_event("startup")
async def _startup():
    global scheduler
    scheduler = AsyncIOScheduler(timezone="Europe/Rome")
    scheduler.add_job(run_daily_digest, "cron", hour=8, minute=0, id="daily_digest")
    scheduler.start()
    log.info("Scheduler started (daily digest at 08:00 Europe/Rome)")

app.include_router(api)

@app.on_event("shutdown")
async def _shutdown():
    global scheduler
    if scheduler:
        scheduler.shutdown(wait=False)
    client.close()
