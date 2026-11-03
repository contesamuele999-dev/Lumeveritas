import logging
from datetime import datetime
from typing import Optional
import httpx
from fastapi import FastAPI, APIRouter
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import CORS_ORIGINS, RENDER_EXTERNAL_URL
from db import close_db
from log import log
from services.digest import make_digest_job
from services.digest_rules import rome_tz
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

# I briefing sono JSON di testo: compressi viaggiano a circa un quarto della dimensione.
# Va registrato prima del CORS, così l'header di compressione non salta le preflight.
app.add_middleware(GZipMiddleware, minimum_size=1000)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

scheduler: Optional[AsyncIOScheduler] = None


async def _keep_awake():
    """Render free addormenta il servizio dopo 15 min senza richieste in ingresso: niente
    digest e ~50 s di attesa al primo caricamento. Una richiesta al proprio URL pubblico
    passa dal proxy di Render e conta come traffico, quindi il servizio resta sveglio."""
    async with httpx.AsyncClient(timeout=30) as client:
        await client.get(f"{RENDER_EXTERNAL_URL}/api/")


@app.on_event("startup")
async def _startup():
    global scheduler
    await run_startup_migrations()
    run_due = make_digest_job(run_briefing)
    scheduler = AsyncIOScheduler(timezone=rome_tz())
    # ogni 10 minuti, non alle 06:00 in punto: se l'istanza dormiva, recupera al risveglio
    scheduler.add_job(run_due, "interval", minutes=10, id="digest_due",
                      next_run_time=datetime.now(rome_tz()), coalesce=True, max_instances=1)
    if RENDER_EXTERNAL_URL:
        scheduler.add_job(_keep_awake, "interval", minutes=10, id="keep_awake", coalesce=True, max_instances=1)
    scheduler.start()
    log.info("Scheduler started (digest dalle 06:00 Europe/Rome, controllo ogni 10 min)")


@app.on_event("shutdown")
async def _shutdown():
    global scheduler
    if scheduler:
        scheduler.shutdown(wait=False)
    await close_db()
