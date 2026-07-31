from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import Response
from db import db
from log import log
from models import BriefingItem
from services.og import render_og_image
from routers.news import deep_dive

router = APIRouter(prefix="/api", tags=["public"])


async def _deep_dive_bg(briefing_id: str):
    try:
        await deep_dive(briefing_id)
    except Exception as e:
        log.warning(f"public deep-dive in background fallito: {e}")


@router.get("/public/{briefing_id}", response_model=BriefingItem)
async def public_briefing(briefing_id: str, background: BackgroundTasks):
    doc = await db.briefings.find_one({"id": briefing_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Notizia non trovata")
    # L'approfondimento è una chiamata LLM da decine di secondi: farlo qui significava
    # far scadere la richiesta (o il cold start di Render) e mostrare "Not found" a chi
    # arriva dal link dell'email. Si risponde subito e si genera in background.
    if not doc.get("real_reasons"):
        background.add_task(_deep_dive_bg, briefing_id)
    try:
        await db.briefings.update_one({"id": briefing_id}, {"$inc": {"views": 1}})
        doc["views"] = int(doc.get("views", 0)) + 1
    except Exception:
        pass
    return BriefingItem(**doc)


@router.get("/public/{briefing_id}/views")
async def public_briefing_views(briefing_id: str):
    doc = await db.briefings.find_one({"id": briefing_id}, {"_id": 0, "views": 1})
    if not doc:
        raise HTTPException(status_code=404, detail="Non trovato")
    return {"views": int(doc.get("views", 0))}


@router.get("/og/{briefing_id}.png")
async def og_image(briefing_id: str):
    doc = await db.briefings.find_one({"id": briefing_id}, {"_id": 0, "topic": 1, "headline": 1, "generated_at": 1})
    if not doc:
        png = render_og_image("LUME VERITAS", "Le notizie che i giornali trascurano.")
    else:
        png = render_og_image(doc.get("topic", ""), doc.get("headline", ""), doc.get("generated_at"))
    return Response(content=png, media_type="image/png", headers={"Cache-Control": "public, max-age=86400"})
