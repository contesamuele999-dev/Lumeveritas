from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Literal


# -------------------- User / Auth --------------------
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


# -------------------- Briefings --------------------
class BriefingIn(BaseModel):
    topic: str
    language: Literal["it", "en"] = "it"
    depth: Literal["short", "deep"] = "short"
    refresh: bool = False
    kind: Optional[Literal["topic", "person", "telegram", "hashtag", "channel"]] = "topic"
    source: Optional[str] = None

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


# -------------------- Ask / Explain / Q&A / Debate --------------------
class AskIn(BaseModel):
    question: str
    language: Literal["it", "en"] = "it"

class AskOut(BaseModel):
    answer: str
    key_points: List[str] = []
    caveats: List[str] = []

class ExplainIn(BaseModel):
    word: str
    context: Optional[str] = None
    language: Literal["it", "en"] = "it"

class ExplainOut(BaseModel):
    word: str
    explanation: str

class ArticleQAIn(BaseModel):
    question: str = Field(min_length=3, max_length=500)

class ArticleQA(BaseModel):
    id: str
    briefing_id: str
    question: str
    answer: str
    key_points: List[str] = []
    created_at: str
    author_name: Optional[str] = None

class DebateSide(BaseModel):
    persona: str
    stance: str
    arguments: List[str] = []

class DebateOut(BaseModel):
    briefing_id: str
    sides: List[DebateSide]
    synthesis: str
    language: str
    generated_at: str


# -------------------- Saved --------------------
class SaveItemIn(BaseModel):
    briefing_id: str


# -------------------- Custom Topics --------------------
class CustomTopicIn(BaseModel):
    label: str = Field(min_length=2, max_length=80)
    kind: Literal["topic", "person", "telegram", "hashtag", "channel"] = "topic"
    source: Optional[str] = Field(default=None, max_length=200)

class CustomTopic(BaseModel):
    key: str
    label_it: str
    label_en: str
    kind: str = "topic"
    source: Optional[str] = None
    custom: bool = True


# -------------------- Digest / TTS --------------------
class DigestPrefIn(BaseModel):
    enabled: Optional[bool] = None
    frequency: Optional[Literal["daily", "weekly"]] = None

class TTSIn(BaseModel):
    text: Optional[str] = None
    briefing_id: Optional[str] = None
    language: Literal["it", "en"] = "it"


# -------------------- Static topic catalog --------------------
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

RSS_FEEDS = {
    "mercati": ["https://www.zerohedge.com/fullrss2.xml", "https://feeds.marketwatch.com/marketwatch/topstories/"],
    "economia": ["https://www.zerohedge.com/fullrss2.xml", "https://feeds.marketwatch.com/marketwatch/topstories/"],
    "cripto": ["https://cointelegraph.com/rss", "https://bitcoinmagazine.com/.rss/full/"],
    "scienza": ["https://www.sciencedaily.com/rss/all.xml", "https://phys.org/rss-feed/"],
    "tecnologia": ["https://feeds.arstechnica.com/arstechnica/index/", "https://www.theregister.com/headlines.atom"],
    "invenzioni": ["https://phys.org/rss-feed/technology-news/", "https://feeds.arstechnica.com/arstechnica/science/"],
    "salute": ["https://feeds.feedburner.com/naturalnews/Health", "https://www.who.int/rss-feeds/news-english.xml"],
    "ambiente": ["https://feeds.feedburner.com/climatedepot", "https://phys.org/rss-feed/earth-news/"],
    "geopolitica": ["https://www.consortiumnews.com/feed/", "https://caitlinjohnstone.com/feed/", "https://moonofalabama.org/index.rdf"],
    "guerre": ["https://www.consortiumnews.com/feed/", "https://moonofalabama.org/index.rdf", "https://caitlinjohnstone.com/feed/"],
    "politica": ["https://www.commondreams.org/rss.xml", "https://truthout.org/feed/?withoutcomments=1"],
    "leggi": ["https://www.commondreams.org/rss.xml", "https://truthout.org/feed/?withoutcomments=1"],
    "sondaggi": ["https://news.gallup.com/rss/RSS.aspx?e=politics", "https://www.pewresearch.org/feed/"],
    "statistiche": ["https://ourworldindata.org/atom.xml", "https://www.pewresearch.org/feed/"],
    "popolazione": ["https://ourworldindata.org/atom.xml", "https://www.pewresearch.org/feed/"],
    "societa": ["https://www.commondreams.org/rss.xml", "https://www.pewresearch.org/feed/"],
}

TOPIC_KEY_BY_LABEL = {t["label_it"].lower(): t["key"] for t in DEFAULT_TOPICS}
TOPIC_KEY_BY_LABEL.update({t["label_en"].lower(): t["key"] for t in DEFAULT_TOPICS})


def slugify(txt: str) -> str:
    import re, unicodedata
    txt = unicodedata.normalize("NFKD", txt).encode("ascii", "ignore").decode()
    txt = re.sub(r"[^a-zA-Z0-9]+", "-", txt).strip("-").lower()
    return txt[:40] or "topic"
