"""Digest builder + sender + scheduled jobs."""
import asyncio
from datetime import date, datetime, timezone
from html import escape
from typing import Optional
from maileroo import MailerooClient, EmailAddress

from config import MAILEROO_API_KEY, SENDER_EMAIL, SENDER_NAME, PUBLIC_APP_URL
from db import db
from log import log
from models import BriefingIn, DEFAULT_TOPICS
from services.digest_rules import DIGEST_HOUR, is_due, rome_tz

TZ = rome_tz()
MAX_TOPICS_PER_DIGEST = 6

mailer = MailerooClient(MAILEROO_API_KEY) if MAILEROO_API_KEY else None


def _article_url(briefing_id: str) -> str:
    return f"{PUBLIC_APP_URL.rstrip('/')}/s/{briefing_id}"


def _digest_html(user_name: str, lang: str, sections: list) -> str:
    lbl_hello = "Ciao" if lang == "it" else "Hi"
    lbl_title = "Il tuo digest quotidiano" if lang == "it" else "Your daily digest"
    lbl_open = "Apri l'app" if lang == "it" else "Open the app"
    lbl_footer = ("Ricevi questa email perché hai attivato il digest su Lume Veritas. "
                  "Per disattivarlo, vai su Profilo → Digest.") if lang == "it" else \
                 ("You get this because you enabled digest on Lume Veritas. Disable it in Profile → Digest.")
    lbl_more = "Approfondisci →" if lang == "it" else "Read the deep dive →"
    blocks = []
    for sec in sections:
        # titolo cliccabile: porta alla pagina di approfondimento della singola notizia
        items_html = "".join(
            f"""<tr><td style="padding:12px 0;border-bottom:1px solid #e2e2d9;">
                <a href="{_article_url(it['id'])}" style="text-decoration:none;">
                  <div style="font-family:Georgia,serif;font-size:20px;line-height:1.25;color:#111;margin-bottom:6px;">{escape(it['headline'])}</div>
                </a>
                <div style="font-family:Arial,sans-serif;font-size:14px;color:#444;line-height:1.5;">{escape(it['summary'])}</div>
                <a href="{_article_url(it['id'])}" style="font-family:Arial,sans-serif;font-size:11px;letter-spacing:0.12em;text-transform:uppercase;color:#D9381E;text-decoration:none;display:inline-block;margin-top:8px;">{lbl_more}</a>
            </td></tr>"""
            for it in sec["items"][:3]
        )
        blocks.append(f"""
        <tr><td style="padding:24px 0 8px;">
            <div style="font-family:Arial,sans-serif;font-size:11px;letter-spacing:0.15em;text-transform:uppercase;color:#D9381E;">{escape(sec['topic'])}</div>
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


def _digest_topic_keys(user_doc: dict) -> list:
    """Argomenti del digest: prima TUTTI i personalizzati dell'utente, poi i preferiti
    standard. I custom sono il motivo per cui uno si iscrive: non devono mai cadere fuori
    dal taglio."""
    custom_keys = [t["key"] for t in (user_doc.get("custom_topics") or [])]
    preferred = user_doc.get("preferred_topics") or [t["key"] for t in DEFAULT_TOPICS[:4]]
    keys = custom_keys + [k for k in preferred if k not in custom_keys]
    return keys[:MAX_TOPICS_PER_DIGEST]


async def build_digest_for_user(user_doc: dict, run_briefing_fn) -> Optional[dict]:
    lang = user_doc.get("language", "it")
    topic_keys = _digest_topic_keys(user_doc)
    all_topics = list(DEFAULT_TOPICS) + list(user_doc.get("custom_topics") or [])
    by_key = {t["key"]: t for t in all_topics}
    sections = []
    for k in topic_keys:
        topic_meta = by_key.get(k)
        if not topic_meta:
            continue
        label = topic_meta["label_it"] if lang == "it" else topic_meta["label_en"]
        try:
            res = await run_briefing_fn(BriefingIn(
                topic=label, language=lang, refresh=False,
                kind=topic_meta.get("kind") or "topic",
                source=topic_meta.get("source"),
            ))
            if res.items:
                sections.append({"topic": label, "items": [i.model_dump() for i in res.items[:3]]})
        except Exception as e:
            log.warning(f"digest section failed {k}: {e}")
    if not sections:
        return None
    return {"lang": lang, "html": _digest_html(user_doc.get("name") or user_doc["email"].split("@")[0], lang, sections)}


async def _log_attempt(user_doc: dict, kind: str, ok: bool, error: Optional[str] = None, ref=None):
    await db.digest_log.insert_one({
        "user_id": user_doc["id"], "email": user_doc["email"],
        "kind": kind, "ok": ok, "error": error, "maileroo_ref": ref,
        "day": datetime.now(TZ).date().isoformat(),
        "sent_at": datetime.now(timezone.utc).isoformat(),
    })


async def send_digest_to_user(user_doc: dict, run_briefing_fn, kind: str = "manual") -> tuple[bool, Optional[str]]:
    if not mailer:
        log.error("digest: MAILEROO_API_KEY mancante, nessuna email può partire")
        await _log_attempt(user_doc, kind, False, "maileroo_key_missing")
        return False, "maileroo_key_missing"
    payload = await build_digest_for_user(user_doc, run_briefing_fn)
    if not payload:
        await _log_attempt(user_doc, kind, False, "no_content")
        return False, "no_content"
    freq = user_doc.get("digest_frequency", "daily")
    if freq == "weekly":
        subject = "Lume Veritas — Il tuo digest settimanale" if payload["lang"] == "it" else "Lume Veritas — Your weekly digest"
    else:
        subject = "Lume Veritas — Il tuo digest quotidiano" if payload["lang"] == "it" else "Lume Veritas — Your daily digest"
    params = {
        "from": EmailAddress(SENDER_EMAIL, SENDER_NAME),
        "to": [EmailAddress(user_doc["email"], user_doc.get("name") or user_doc["email"].split("@")[0])],
        "subject": subject,
        "html": payload["html"],
    }
    try:
        ref = await asyncio.to_thread(mailer.send_basic_email, params)
        await _log_attempt(user_doc, kind, True, ref=ref)
        return True, None
    except Exception as e:
        msg = str(e)
        log.error(f"Maileroo send failed to {user_doc['email']}: {msg}")
        await _log_attempt(user_doc, kind, False, msg[:220])
        return False, msg[:220]


async def digest_state(user_id: str) -> dict:
    """Ultimo invio automatico riuscito + tentativi di oggi. Serve al job e a /digest/status."""
    today = datetime.now(TZ).date().isoformat()
    last_ok = await db.digest_log.find_one(
        {"user_id": user_id, "kind": "auto", "ok": True}, {"_id": 0}, sort=[("sent_at", -1)]
    )
    attempts = await db.digest_log.count_documents({"user_id": user_id, "kind": "auto", "day": today})
    last_any = await db.digest_log.find_one({"user_id": user_id}, {"_id": 0}, sort=[("sent_at", -1)])
    return {"last_ok": last_ok, "attempts_today": attempts, "last_any": last_any}


def make_digest_job(run_briefing_fn):
    """Un solo job, eseguito a intervalli: manda a chi è "in ritardo" per oggi.

    Sostituisce i due cron alle 06:00: su Render free l'istanza dorme e un cron a orario
    fisso salta silenziosamente la giornata. Qui, appena il processo è vivo dopo le 06:00,
    il digest parte; il marker per giorno impedisce doppi invii.
    """
    async def run_due_digests():
        now = datetime.now(TZ)
        if now.hour < DIGEST_HOUR:
            return
        cursor = db.users.find({"digest_enabled": True}, {"_id": 0, "password_hash": 0})
        users = await cursor.to_list(1000)
        sent = 0
        for u in users:
            try:
                state = await digest_state(u["id"])
                last_ok = state["last_ok"]
                last_ok_day = date.fromisoformat(last_ok["day"]) if last_ok and last_ok.get("day") else None
                if not is_due(now, u.get("digest_frequency", "daily"), last_ok_day, state["attempts_today"]):
                    continue
                ok, err = await send_digest_to_user(u, run_briefing_fn, kind="auto")
                if ok:
                    sent += 1
                else:
                    log.error(f"digest non inviato a {u.get('email')}: {err}")
                await asyncio.sleep(2)
            except Exception as e:
                log.error(f"digest error for {u.get('email')}: {e}")
        if sent:
            log.info(f"Digest inviati: {sent}")

    return run_due_digests
