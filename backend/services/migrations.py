"""Startup migrations. Idempotent."""
from log import log
from db import db


async def migrate_custom_topic_keys():
    """Old keys `custom-{slug}` → new keys `custom-topic-{slug}` (kind default).
    Also updates preferred_topics accordingly. Idempotent.
    """
    cursor = db.users.find({"custom_topics": {"$exists": True, "$ne": []}}, {"_id": 0, "id": 1, "custom_topics": 1, "preferred_topics": 1})
    users = await cursor.to_list(5000)
    migrated = 0
    for u in users:
        changed = False
        remap = {}
        new_topics = []
        for t in u.get("custom_topics", []):
            key = t.get("key", "")
            if key.startswith("custom-") and not any(key.startswith(f"custom-{k}-") for k in ("topic", "person", "telegram", "hashtag", "channel")):
                new_key = f"custom-topic-{key[len('custom-'):]}"
                remap[key] = new_key
                t = {**t, "key": new_key, "kind": t.get("kind") or "topic"}
                changed = True
            elif "kind" not in t:
                t = {**t, "kind": "topic"}
                changed = True
            new_topics.append(t)
        new_prefs = [remap.get(k, k) for k in (u.get("preferred_topics") or [])]
        if changed or new_prefs != u.get("preferred_topics"):
            await db.users.update_one({"id": u["id"]}, {"$set": {"custom_topics": new_topics, "preferred_topics": new_prefs}})
            migrated += 1
    if migrated:
        log.info(f"Migrated custom-topic keys for {migrated} user(s)")
    else:
        log.info("No custom-topic key migrations needed")


async def run_startup_migrations():
    try:
        await migrate_custom_topic_keys()
    except Exception as e:
        log.error(f"migration error: {e}")
