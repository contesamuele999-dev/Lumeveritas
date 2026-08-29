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
    # dominio reale della fonte (es. "reuters.com"): il grounding di Gemini restituisce
    # URL di redirect tutti uguali (vertexaisearch.cloud.google.com/...), inutili da mostrare.
    domain: Optional[str] = None

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


# -------------------- Storico / Timeline --------------------
class TimelineEvent(BaseModel):
    date: str            # "1991", "marzo 2014", "12 set 2023" — testo libero, non tutte le date sono precise
    title: str
    description: str
    significance: Optional[str] = None

class TimelineOut(BaseModel):
    briefing_id: str
    summary: str                       # il "sunto" che spiega come si è arrivati a oggi
    events: List[TimelineEvent] = []
    turning_points: List[str] = []     # i momenti che hanno cambiato traiettoria
    open_questions: List[str] = []
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


class VerifyScoresIn(BaseModel):
    ids: List[str] = Field(default_factory=list, max_length=50)


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

# Fonti in lingua italiana: quando l'utente ha scelto "it" vengono messe in cima e non
# hanno bisogno di traduzione. I feed che non rispondono vengono ignorati senza errori.
RSS_FEEDS_IT = {
    "mercati": ["https://www.wallstreetitalia.com/feed/", "https://www.milanofinanza.it/rss/mercati"],
    "economia": ["https://www.wallstreetitalia.com/feed/", "https://www.ilfattoquotidiano.it/economia/feed/"],
    "cripto": ["https://it.cointelegraph.com/rss", "https://www.criptovaluta.it/feed"],
    "scienza": ["https://www.lescienze.it/rss/all/rss2.0.xml", "https://www.media.inaf.it/feed/"],
    "tecnologia": ["https://www.wired.it/feed/rss", "https://www.dday.it/rss"],
    "invenzioni": ["https://www.wired.it/feed/rss", "https://www.lescienze.it/rss/all/rss2.0.xml"],
    "salute": ["https://www.quotidianosanita.it/rss/rss.php", "https://www.epicentro.iss.it/rss/rss.xml"],
    "ambiente": ["https://greenreport.it/feed/", "https://www.rinnovabili.it/feed/"],
    "geopolitica": ["https://www.lantidiplomatico.it/rss.xml", "https://www.limesonline.com/feed"],
    "guerre": ["https://www.lantidiplomatico.it/rss.xml", "https://www.limesonline.com/feed"],
    "politica": ["https://www.ilfattoquotidiano.it/politica-palazzo/feed/", "https://www.valigiablu.it/feed/"],
    "leggi": ["https://www.ilfattoquotidiano.it/politica-palazzo/feed/", "https://www.valigiablu.it/feed/"],
    "sondaggi": ["https://www.ilpost.it/feed/", "https://www.valigiablu.it/feed/"],
    "statistiche": ["https://www.istat.it/comunicato-stampa/feed/", "https://www.ilpost.it/feed/"],
    "popolazione": ["https://www.istat.it/comunicato-stampa/feed/", "https://www.internazionale.it/sitemaps/rss.xml"],
    "societa": ["https://www.internazionale.it/sitemaps/rss.xml", "https://www.ilpost.it/feed/"],
    "ia": ["https://www.wired.it/feed/rss", "https://www.dday.it/rss"],
    "scuola": ["https://www.orizzontescuola.it/feed/", "https://www.tecnicadellascuola.it/feed"],
    "curiosita": ["https://www.focus.it/rss/tutti.rss", "https://www.ilpost.it/feed/"],
}

# Confine tematico di ogni argomento. Senza questo, "Geopolitica", "Guerre e veri motivi"
# e "Scelte politiche" producevano le stesse tre notizie riscritte: al modello arrivava
# solo l'etichetta, e per tutte e tre la risposta più ovvia era la crisi internazionale
# del giorno. Ogni voce dice cosa rientra e cosa va lasciato agli argomenti vicini.
TOPIC_SCOPES = {
    "geopolitica": (
        "relazioni fra stati, alleanze, sanzioni, basi militari, rotte commerciali e controllo delle risorse. "
        "Lascia ad altri argomenti la cronaca dei combattimenti e la politica interna di un singolo paese.",
        "relations between states, alliances, sanctions, military bases, trade routes and control of resources. "
        "Leave battlefield reporting and a single country's domestic politics to other topics.",
    ),
    "guerre": (
        "conflitti armati in corso o latenti: andamento sul terreno, forniture di armi, contractor, costi umani "
        "ed economici, interessi materiali dietro la guerra. Non analisi diplomatiche generiche.",
        "ongoing or latent armed conflicts: developments on the ground, arms supplies, contractors, human and "
        "economic costs, material interests behind the war. Not generic diplomatic analysis.",
    ),
    "politica": (
        "decisioni di governi e parlamenti sulla politica interna: nomine, riforme, bilanci, scandali, rapporti "
        "con lobby e gruppi di interesse. Non conflitti armati né relazioni internazionali.",
        "decisions by governments and parliaments on domestic politics: appointments, reforms, budgets, scandals, "
        "ties with lobbies and interest groups. Not armed conflicts or international relations.",
    ),
    "leggi": (
        "singole leggi, decreti, regolamenti e sentenze approvati di recente e i loro effetti concreti su cittadini "
        "e imprese. Cita il nome o il numero dell'atto.",
        "individual laws, decrees, regulations and rulings recently passed and their concrete effects on citizens "
        "and businesses. Name the act or its number.",
    ),
    "mercati": (
        "borse, materie prime, valute, tassi, debito, mosse delle banche centrali e movimenti dei grandi investitori.",
        "stock markets, commodities, currencies, rates, debt, central bank moves and large investors' positions.",
    ),
    "economia": (
        "economia reale: lavoro, salari, prezzi, produzione, commercio, filiere, disuguaglianza. "
        "Non le quotazioni giornaliere dei mercati.",
        "the real economy: jobs, wages, prices, production, trade, supply chains, inequality. "
        "Not daily market quotes.",
    ),
    "cripto": (
        "criptovalute, finanza decentralizzata, pagamenti alternativi, valute digitali di banca centrale e "
        "regolamentazione del settore.",
        "cryptocurrencies, decentralised finance, alternative payments, central bank digital currencies and "
        "regulation of the sector.",
    ),
    "ia": (
        "intelligenza artificiale: modelli, ricerca, usi concreti, incidenti, regole, impatto su lavoro e informazione.",
        "artificial intelligence: models, research, concrete uses, incidents, rules, impact on work and information.",
    ),
    "tecnologia": (
        "tecnologia e industria digitale fuori dall'IA: hardware, reti, software, sicurezza informatica, "
        "piattaforme, telecomunicazioni.",
        "technology and the digital industry beyond AI: hardware, networks, software, cybersecurity, platforms, "
        "telecoms.",
    ),
    "scienza": (
        "risultati di ricerca pubblicati (studi, esperimenti, missioni), citando rivista o istituzione che li ha prodotti.",
        "published research results (studies, experiments, missions), citing the journal or institution behind them.",
    ),
    "invenzioni": (
        "nuove invenzioni, brevetti, prototipi e applicazioni pratiche appena realizzate. "
        "Non studi teorici né annunci di prodotto delle grandi aziende.",
        "new inventions, patents, prototypes and freshly built practical applications. "
        "Not theoretical studies or big-company product announcements.",
    ),
    "scuola": (
        "scuola, università e formazione: programmi, riforme, dati sull'apprendimento, insegnanti, costi e accesso allo studio.",
        "schools, universities and training: curricula, reforms, learning data, teachers, costs and access to study.",
    ),
    "curiosita": (
        "fatti curiosi, insoliti o poco noti, ma verificati e documentati. Non cronaca politica o economica.",
        "curious, unusual or little-known facts, but verified and documented. Not political or economic reporting.",
    ),
    "salute": (
        "salute e medicina: terapie, epidemiologia, sistemi sanitari, farmaci, dati su malattie e prevenzione.",
        "health and medicine: treatments, epidemiology, health systems, drugs, disease and prevention data.",
    ),
    "ambiente": (
        "ambiente e risorse naturali: inquinamento, energia, acqua, suolo, biodiversità, clima, con dati misurati.",
        "environment and natural resources: pollution, energy, water, soil, biodiversity, climate, with measured data.",
    ),
    "societa": (
        "cultura, costumi, religione, media, migrazioni, criminalità e mutamenti sociali documentati.",
        "culture, customs, religion, media, migration, crime and documented social change.",
    ),
    "popolazione": (
        "demografia: natalità, mortalità, invecchiamento, migrazioni, composizione della popolazione, "
        "con serie storiche e proiezioni.",
        "demography: births, deaths, ageing, migration, population composition, with historical series and projections.",
    ),
    "sondaggi": (
        "sondaggi e rilevazioni d'opinione appena pubblicati: chi li ha condotti, campione, domande, percentuali.",
        "opinion polls and surveys just published: who ran them, sample, questions, percentages.",
    ),
    "statistiche": (
        "dati e indicatori appena diffusi da istituti ufficiali o centri di ricerca: cosa misurano e come sono cambiati.",
        "figures and indicators just released by official institutes or research centres: what they measure and how "
        "they changed.",
    ),
}


TOPIC_KEY_BY_LABEL = {t["label_it"].lower(): t["key"] for t in DEFAULT_TOPICS}
TOPIC_KEY_BY_LABEL.update({t["label_en"].lower(): t["key"] for t in DEFAULT_TOPICS})


def slugify(txt: str) -> str:
    import re, unicodedata
    txt = unicodedata.normalize("NFKD", txt).encode("ascii", "ignore").decode()
    txt = re.sub(r"[^a-zA-Z0-9]+", "-", txt).strip("-").lower()
    return txt[:40] or "topic"
