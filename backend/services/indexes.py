"""Indici MongoDB creati all'avvio. Idempotente.

Finora nessuna collezione aveva indici: ogni `find_one({"id": ...})` era una scansione
completa. Con `current_user` che cerca l'utente a ogni richiesta autenticata e con
`briefings` che cresce di sei documenti per argomento ogni sei ore, il costo saliva in
proporzione ai dati accumulati. `create_index` non fa nulla se l'indice esiste già,
quindi la funzione può girare a ogni avvio.
"""
from pymongo import ASCENDING, DESCENDING

from db import db
from log import log

# (collezione, chiavi, opzioni)
INDEXES = [
    ("users", [("id", ASCENDING)], {"unique": True, "name": "user_id"}),
    ("users", [("email", ASCENDING)], {"unique": True, "name": "user_email"}),
    ("users", [("digest_enabled", ASCENDING)], {"name": "user_digest"}),

    ("briefings", [("id", ASCENDING)], {"unique": True, "name": "briefing_id"}),
    # la cache dei briefing filtra per argomento+lingua e ordina per data
    ("briefings", [("topic", ASCENDING), ("language", ASCENDING), ("generated_at", DESCENDING)],
     {"name": "briefing_cache"}),
    # elenco dei titoli usciti di recente su tutti gli argomenti: serve a non ripetere
    # la stessa notizia in argomenti vicini
    ("briefings", [("language", ASCENDING), ("generated_at", DESCENDING)],
     {"name": "briefing_recent"}),

    ("saved", [("user_id", ASCENDING), ("briefing_id", ASCENDING)], {"unique": True, "name": "saved_user_item"}),
    ("saved", [("user_id", ASCENDING), ("saved_at", DESCENDING)], {"name": "saved_recent"}),

    ("explanations", [("key", ASCENDING)], {"unique": True, "name": "explanation_key"}),
    ("rss_translations", [("key", ASCENDING)], {"unique": True, "name": "rss_translation_key"}),
    ("topic_translations", [("label_it", ASCENDING)], {"unique": True, "name": "topic_label_it"}),

    ("verifications", [("briefing_id", ASCENDING), ("language", ASCENDING)], {"name": "verify_item_lang"}),
    ("timelines", [("briefing_id", ASCENDING), ("language", ASCENDING)], {"name": "timeline_item_lang"}),
    ("debates", [("briefing_id", ASCENDING), ("language", ASCENDING)], {"name": "debate_item_lang"}),

    ("article_qas", [("briefing_id", ASCENDING), ("created_at", DESCENDING)], {"name": "qa_item_recent"}),
    ("digest_log", [("user_id", ASCENDING), ("sent_at", DESCENDING)], {"name": "digest_user_recent"}),
]


async def ensure_indexes():
    created, failed = 0, 0
    for coll, keys, opts in INDEXES:
        try:
            await db[coll].create_index(keys, **opts)
            created += 1
        except Exception as e:
            # un indice unique può fallire se in archivio ci sono già duplicati:
            # è un dato da ripulire, non un motivo per non far partire l'app
            failed += 1
            log.warning(f"indice {coll}.{opts.get('name')} non creato: {e}")
    log.info(f"Indici verificati: {created} ok, {failed} saltati")
