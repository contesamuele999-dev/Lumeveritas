import logging
from typing import Optional
from fastapi import FastAPI, APIRouter
from starlette.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import CORS_ORIGINS
from db import close_db
from log import log
from services.digest import make_digest_jobs
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
    run_daily, run_weekly = make_digest_jobs(run_briefing)
    scheduler = AsyncIOScheduler(timezone="Europe/Rome")
    scheduler.add_job(run_daily, "cron", hour=8, minute=0, id="daily_digest")
    scheduler.add_job(run_weekly, "cron", day_of_week="mon", hour=8, minute=0, id="weekly_digest")
    scheduler.start()
    log.info("Scheduler started (daily 08:00, weekly Mon 08:00 Europe/Rome)")


@app.on_event("shutdown")
async def _shutdown():
    global scheduler
    if scheduler:
        scheduler.shutdown(wait=False)
    await close_db()
