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

class SourceLink(BaseModel):
    title: str
    url: str

class BriefingItem(BaseModel):
    id: str
    topic: str
    headline: str
    summary: str
    key_facts: List[str] = []
    sources_hint: List[str] = []
    sources: List[SourceLink] = []
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
    sources: List[SourceLink] = []

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


# -------------------- Verification --------------------
class VerifyCriterion(BaseModel):
    key: str
    score: int  # 0..100
    rationale: str

class VerifyOut(BaseModel):
    briefing_id: str
    overall_score: int  # 0..100
    verdict: str  # short label
    criteria: List[VerifyCriterion]
    flagged_claims: List[str] = []
    corroborating_sources: List[str] = []
    contradicting_sources: List[str] = []
    method_notes: str
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
# section = raggruppamento mostrato nella home. Le etichette viaggiano col topic così il
# frontend raggruppa senza una seconda tabella da tenere allineata.
_SECTIONS = {
    "mondo": ("Mondo & Potere", "World & Power"),
    "soldi": ("Soldi", "Money"),
    "sapere": ("Sapere & Tecnologia", "Knowledge & Tech"),
    "vita": ("Vita quotidiana", "Everyday life"),
}

def _topic(key, it, en, section):
    s_it, s_en = _SECTIONS[section]
    return {"key": key, "label_it": it, "label_en": en,
            "section": section, "section_it": s_it, "section_en": s_en}

DEFAULT_TOPICS = [
    _topic("geopolitica", "Geopolitica", "Geopolitics", "mondo"),
    _topic("guerre", "Guerre e veri motivi", "Wars & Real Reasons", "mondo"),
    _topic("politica", "Scelte politiche", "Political Choices", "mondo"),
    _topic("leggi", "Leggi approvate", "Laws Passed", "mondo"),

    _topic("mercati", "Mercati", "Markets", "soldi"),
    _topic("economia", "Economia", "Economy", "soldi"),
    _topic("cripto", "Cripto & Finanza Alt.", "Crypto & Alt Finance", "soldi"),

    _topic("ia", "Intelligenza artificiale", "Artificial Intelligence", "sapere"),
    _topic("tecnologia", "Tecnologia", "Technology", "sapere"),
    _topic("scienza", "Scoperte scientifiche", "Scientific Discoveries", "sapere"),
    _topic("invenzioni", "Invenzioni", "Inventions", "sapere"),
    _topic("scuola", "Scuola", "School & Education", "sapere"),

    _topic("curiosita", "Curiosità", "Curiosities", "vita"),
    _topic("salute", "Salute", "Health", "vita"),
    _topic("ambiente", "Ambiente", "Environment", "vita"),
    _topic("societa", "Cultura & Società", "Culture & Society", "vita"),
    _topic("popolazione", "Tendenze popolazione", "Population Trends", "vita"),
    _topic("sondaggi", "Sondaggi", "Polls & Surveys", "vita"),
    _topic("statistiche", "Statistiche", "Statistics", "vita"),
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
    "ia": ["https://feeds.arstechnica.com/arstechnica/technology-lab/", "https://www.theregister.com/software/ai_ml/headlines.atom"],
    "scuola": ["https://www.edsurge.com/articles_rss", "https://hechingerreport.org/feed/"],
    "curiosita": ["https://www.atlasobscura.com/feeds/latest", "https://phys.org/rss-feed/"],
}

TOPIC_KEY_BY_LABEL = {t["label_it"].lower(): t["key"] for t in DEFAULT_TOPICS}
TOPIC_KEY_BY_LABEL.update({t["label_en"].lower(): t["key"] for t in DEFAULT_TOPICS})


def slugify(txt: str) -> str:
    import re, unicodedata
    txt = unicodedata.normalize("NFKD", txt).encode("ascii", "ignore").decode()
    txt = re.sub(r"[^a-zA-Z0-9]+", "-", txt).strip("-").lower()
    return txt[:40] or "topic"
