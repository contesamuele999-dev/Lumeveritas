"""Riconoscimento di notizie ripetute fra argomenti diversi.

Interrogato su "Geopolitica" e su "Guerre e veri motivi" nello stesso giorno, il modello
restituisce spesso gli stessi due o tre fatti riscritti con altre parole: in home si
cambia argomento e la lista sembra la stessa, e nel digest le sezioni si sovrappongono.
Qui i titoli si confrontano per parole significative: se due titoli condividono la
maggior parte dei loro termini è la stessa notizia, anche se le frasi sono diverse.
"""
import re
import unicodedata

# articoli, preposizioni e verbi di servizio: presenti in ogni titolo, non distinguono
# una notizia dall'altra e falserebbero il confronto verso l'alto.
STOPWORDS = {
    # italiano
    "il", "lo", "la", "i", "gli", "le", "un", "uno", "una", "di", "del", "dello", "della",
    "dei", "degli", "delle", "da", "dal", "dalla", "in", "nel", "nella", "nei", "con",
    "su", "sul", "sulla", "per", "tra", "fra", "e", "ed", "o", "ma", "che", "chi", "cui",
    "non", "piu", "come", "anche", "dopo", "prima", "sono", "essere", "stato", "stata",
    "ha", "hanno", "viene", "vengono", "si", "al", "allo", "alla", "ai", "agli", "alle",
    "a", "il", "suo", "sua", "loro", "questo", "questa", "quello", "quella",
    # inglese
    "the", "a", "an", "of", "in", "on", "at", "to", "for", "from", "by", "with", "and",
    "or", "but", "that", "which", "who", "not", "more", "as", "is", "are", "was", "were",
    "be", "been", "has", "have", "had", "its", "their", "this", "these", "those", "it",
    # rumore giornalistico
    "notizia", "notizie", "news", "nuovo", "nuova", "new", "record", "anni", "anno",
    "year", "years", "dopo", "verso", "contro", "senza",
}

MIN_SHARED = 3          # sotto questa soglia due titoli condividono solo parole comuni
DEFAULT_THRESHOLD = 0.6  # quota dei termini del titolo più corto che deve coincidere


# "approva"/"approvata", "europeo"/"europea", "mercato"/"mercati": stesso concetto, parola
# diversa. Tagliare la coda della parola fa coincidere le forme flesse senza bisogno di un
# analizzatore morfologico.
STEM_LEN = 6


def tokens_of(text: str) -> frozenset:
    """Radici delle parole significative di un titolo, senza accenti, punteggiatura né stopword."""
    txt = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode().lower()
    words = re.findall(r"[a-z0-9]+", txt)
    return frozenset(w[:STEM_LEN] for w in words if len(w) > 2 and w not in STOPWORDS)


def is_same_story(a: frozenset, b: frozenset, threshold: float = DEFAULT_THRESHOLD) -> bool:
    if not a or not b:
        return False
    shared = len(a & b)
    if shared < MIN_SHARED:
        return False
    return shared / min(len(a), len(b)) >= threshold


def drop_duplicates(headlines, known=(), threshold: float = DEFAULT_THRESHOLD):
    """Indici dei titoli da tenere: né uguali a quelli già noti, né uguali tra loro."""
    seen = [tokens_of(h) for h in known]
    keep = []
    for idx, headline in enumerate(headlines):
        toks = tokens_of(headline)
        if not toks:
            continue
        if any(is_same_story(toks, s, threshold) for s in seen):
            continue
        seen.append(toks)
        keep.append(idx)
    return keep
