from fastapi import APIRouter, Depends
from db import db
from models import DigestPrefIn
from security import require_user
from services.digest import send_digest_to_user
from routers.news import run_briefing

router = APIRouter(prefix="/api", tags=["digest"])


@router.put("/digest/preferences")
async def digest_prefs(inp: DigestPrefIn, user=Depends(require_user)):
    updates = {}
    if inp.enabled is not None:
        updates["digest_enabled"] = inp.enabled
    if inp.frequency is not None:
        updates["digest_frequency"] = inp.frequency
    if updates:
        await db.users.update_one({"id": user["id"]}, {"$set": updates})
    doc = await db.users.find_one({"id": user["id"]}, {"_id": 0, "digest_enabled": 1, "digest_frequency": 1})
    return {
        "ok": True,
        "digest_enabled": bool((doc or {}).get("digest_enabled", False)),
        "digest_frequency": (doc or {}).get("digest_frequency", "daily"),
    }


@router.post("/digest/send-now")
async def digest_send_now(user=Depends(require_user)):
    ok, err = await send_digest_to_user(user, run_briefing)
    if not ok:
        msg = ("Il servizio email non ha accettato l'invio. "
               "Maileroo richiede un dominio di invio verificato: aggiungi il dominio su "
               "app.maileroo.com → Domains, completa i record DNS (SPF/DKIM) e imposta "
               "SENDER_EMAIL su un indirizzo di quel dominio.")
        return {"ok": False, "error": err or "unknown", "message": msg}
    return {"ok": True, "email": user["email"]}
