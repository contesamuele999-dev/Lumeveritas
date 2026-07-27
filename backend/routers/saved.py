from typing import List
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends
from db import db
from models import SaveItemIn, BriefingItem
from security import require_user

router = APIRouter(prefix="/api", tags=["saved"])


@router.post("/saved/add")
async def save_item(inp: SaveItemIn, user=Depends(require_user)):
    b = await db.briefings.find_one({"id": inp.briefing_id}, {"_id": 0})
    if not b:
        raise HTTPException(status_code=404, detail="Notizia non trovata")
    await db.saved.update_one(
        {"user_id": user["id"], "briefing_id": inp.briefing_id},
        {"$set": {"user_id": user["id"], "briefing_id": inp.briefing_id, "saved_at": datetime.now(timezone.utc).isoformat()}},
        upsert=True,
    )
    return {"ok": True}


@router.delete("/saved/{briefing_id}")
async def unsave(briefing_id: str, user=Depends(require_user)):
    await db.saved.delete_one({"user_id": user["id"], "briefing_id": briefing_id})
    return {"ok": True}


@router.get("/saved", response_model=List[BriefingItem])
async def list_saved(user=Depends(require_user)):
    saved = await db.saved.find({"user_id": user["id"]}, {"_id": 0}).sort("saved_at", -1).to_list(200)
    ids = [s["briefing_id"] for s in saved]
    if not ids:
        return []
    docs = await db.briefings.find({"id": {"$in": ids}}, {"_id": 0}).to_list(200)
    by_id = {d["id"]: d for d in docs}
    return [BriefingItem(**by_id[i]) for i in ids if i in by_id]
