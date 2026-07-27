import uuid
from typing import List
from fastapi import APIRouter, HTTPException, Depends
from db import db
from models import DEFAULT_TOPICS, CustomTopicIn, CustomTopic, slugify
from security import require_user
from llm import llm_text, new_session

router = APIRouter(prefix="/api", tags=["topics"])


@router.get("/topics")
async def get_topics():
    return DEFAULT_TOPICS


@router.get("/topics/mine", response_model=List[CustomTopic])
async def get_my_topics(user=Depends(require_user)):
    doc = await db.users.find_one({"id": user["id"]}, {"_id": 0, "custom_topics": 1})
    return [CustomTopic(**t) for t in (doc or {}).get("custom_topics", [])]


async def _translate_label(label: str) -> str:
    """Shared cache: same label → same translation across all users."""
    cache = await db.topic_translations.find_one({"label_it": label}, {"_id": 0, "label_en": 1})
    if cache and cache.get("label_en"):
        return cache["label_en"]
    label_en = label
    try:
        session = new_session("topic-tr")
        prompt = f'Translate this news topic to English (max 5 words, return only the translation, no quotes): "{label}"'
        tx = await llm_text(session, "You translate short topic names.", prompt)
        cand = tx.strip().strip('"').strip("'").split("\n")[0]
        if 2 <= len(cand) <= 80:
            label_en = cand
    except Exception:
        pass
    await db.topic_translations.update_one(
        {"label_it": label},
        {"$set": {"label_it": label, "label_en": label_en}},
        upsert=True,
    )
    return label_en


@router.post("/topics/custom", response_model=CustomTopic)
async def add_custom_topic(inp: CustomTopicIn, user=Depends(require_user)):
    label = inp.label.strip()
    if len(label) < 2:
        raise HTTPException(status_code=400, detail="Etichetta troppo corta")
    source = (inp.source or "").strip() or None
    slug_seed = label if not source else f"{label}-{source}"
    key = f"custom-{inp.kind}-{slugify(slug_seed)}"
    doc = await db.users.find_one({"id": user["id"]}, {"_id": 0, "custom_topics": 1, "preferred_topics": 1})
    existing = (doc or {}).get("custom_topics", [])
    if len(existing) >= 30:
        raise HTTPException(status_code=400, detail="Hai raggiunto il limite di 30 argomenti personalizzati")
    for t in existing:
        if t.get("key") == key:
            return CustomTopic(**t)
    label_en = await _translate_label(label)
    new_topic = {"key": key, "label_it": label, "label_en": label_en, "kind": inp.kind, "source": source, "custom": True}
    new_list = existing + [new_topic]
    new_prefs = list(dict.fromkeys((doc or {}).get("preferred_topics", []) + [key]))
    await db.users.update_one({"id": user["id"]}, {"$set": {"custom_topics": new_list, "preferred_topics": new_prefs}})
    return CustomTopic(**new_topic)


@router.delete("/topics/custom/{topic_key}")
async def remove_custom_topic(topic_key: str, user=Depends(require_user)):
    doc = await db.users.find_one({"id": user["id"]}, {"_id": 0, "custom_topics": 1, "preferred_topics": 1})
    existing = (doc or {}).get("custom_topics", [])
    new_list = [t for t in existing if t.get("key") != topic_key]
    new_prefs = [k for k in (doc or {}).get("preferred_topics", []) if k != topic_key]
    await db.users.update_one({"id": user["id"]}, {"$set": {"custom_topics": new_list, "preferred_topics": new_prefs}})
    return {"ok": True}
