import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends
from db import db
from models import RegisterIn, LoginIn, UserOut, TokenOut, PreferencesIn, DEFAULT_TOPICS
from security import hash_pw, verify_pw, make_token, require_user

router = APIRouter(prefix="/api", tags=["auth"])


@router.post("/auth/register", response_model=TokenOut)
async def register(inp: RegisterIn):
    existing = await db.users.find_one({"email": inp.email.lower()})
    if existing:
        raise HTTPException(status_code=400, detail="Email già registrata")
    uid = str(uuid.uuid4())
    doc = {
        "id": uid,
        "email": inp.email.lower(),
        "name": inp.name or inp.email.split("@")[0],
        "password_hash": hash_pw(inp.password),
        "preferred_topics": [t["key"] for t in DEFAULT_TOPICS[:6]],
        "language": "it",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.users.insert_one(doc)
    token = make_token(uid)
    return TokenOut(token=token, user=UserOut(id=uid, email=doc["email"], name=doc["name"], preferred_topics=doc["preferred_topics"], language=doc["language"]))


@router.post("/auth/login", response_model=TokenOut)
async def login(inp: LoginIn):
    doc = await db.users.find_one({"email": inp.email.lower()})
    if not doc or not verify_pw(inp.password, doc.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Credenziali non valide")
    token = make_token(doc["id"])
    return TokenOut(token=token, user=UserOut(
        id=doc["id"], email=doc["email"], name=doc.get("name"),
        preferred_topics=doc.get("preferred_topics", []), language=doc.get("language", "it")))


@router.get("/auth/me", response_model=UserOut)
async def me(user=Depends(require_user)):
    return UserOut(id=user["id"], email=user["email"], name=user.get("name"),
                   preferred_topics=user.get("preferred_topics", []),
                   language=user.get("language", "it"))


@router.get("/auth/me/full")
async def me_full(user=Depends(require_user)):
    return {
        "id": user["id"], "email": user["email"], "name": user.get("name"),
        "preferred_topics": user.get("preferred_topics", []),
        "language": user.get("language", "it"),
        "digest_enabled": bool(user.get("digest_enabled", False)),
        "digest_frequency": user.get("digest_frequency", "daily"),
        "custom_topics": user.get("custom_topics", []),
    }


@router.put("/auth/preferences", response_model=UserOut)
async def update_prefs(inp: PreferencesIn, user=Depends(require_user)):
    updates = {}
    if inp.preferred_topics is not None:
        updates["preferred_topics"] = inp.preferred_topics
    if inp.language is not None:
        updates["language"] = inp.language
    if updates:
        await db.users.update_one({"id": user["id"]}, {"$set": updates})
    doc = await db.users.find_one({"id": user["id"]}, {"_id": 0, "password_hash": 0})
    return UserOut(id=doc["id"], email=doc["email"], name=doc.get("name"),
                   preferred_topics=doc.get("preferred_topics", []),
                   language=doc.get("language", "it"))
