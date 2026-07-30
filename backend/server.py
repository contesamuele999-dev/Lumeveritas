import logging
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo
from fastapi import FastAPI, APIRouter
from starlette.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import CORS_ORIGINS
from db import close_db
from log import log
from services.digest import make_digest_job
from services.migrations import run_startup_migrations
from routers import auth, topics, news, saved, rss, public, digest as digest_router
from routers.news import run_briefing

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

app = FastAPI(title="Lume Veritas API")

# Root API health
root = APIRouter(prefix="/api")


@root.get("/")
async def root_ping():
    return {"ok": True, "app": "Lume Veritas"}


app.include_router(root)
app.include_router(auth.router)
app.include_router(topics.router)
app.include_router(news.router)
app.include_router(saved.router)
app.include_router(rss.router)
app.include_router(public.router)
app.include_router(digest_router.router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

scheduler: Optional[AsyncIOScheduler] = None


@app.on_event("startup")
async def _startup():
    global scheduler
    await run_startup_migrations()
    run_due = make_digest_job(run_briefing)
    scheduler = AsyncIOScheduler(timezone="Europe/Rome")
    # ogni 10 minuti, non alle 06:00 in punto: se l'istanza dormiva, recupera al risveglio
    scheduler.add_job(run_due, "interval", minutes=10, id="digest_due",
                      next_run_time=datetime.now(ZoneInfo("Europe/Rome")), coalesce=True, max_instances=1)
    scheduler.start()
    log.info("Scheduler started (digest dalle 06:00 Europe/Rome, controllo ogni 10 min)")


@app.on_event("shutdown")
async def _shutdown():
    global scheduler
    if scheduler:
        scheduler.shutdown(wait=False)
    await close_db()
