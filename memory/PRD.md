# Lume Veritas - PRD

## Problem Statement
User wants a fast, functional web app that collects the newest, verified, deeply-analyzed news on topics mainstream journalists overlook (markets, population trends, polls, statistics, inventions, laws passed, scientific discoveries, political choices, wars & real reasons). User should be able to pick favorite topics, request deep-dives, and query any topic freely. Must be usable by tech-illiterate users. IT + EN.

## Stack
- Backend: FastAPI + MongoDB + Motor
- Auth: JWT + bcrypt (email/password)
- AI: Gemini 3 Flash preview via emergentintegrations (EMERGENT_LLM_KEY)
- Frontend: React 19 + Tailwind + Shadcn + Framer Motion + sonner + react-router

## Implemented (Feb 2026)
- JWT auth: register, login, /auth/me, update preferences
- Topic catalog (16 topics, IT + EN labels)
- AI news briefings (5 items per topic), cached 6h in Mongo
- Deep-dive endpoint (real reasons, data points, context)
- Free-form Ask endpoint (structured JSON answer)
- Save / unsave briefings per user
- Click-a-word to explain (Popover + cache)
- **Daily email digest** via Resend, APScheduler cron 08:00 Europe/Rome. Manual "Send now" from profile. Graceful ok:false JSON on Resend failure so client sees a real actionable message (free-tier limitation).
- **RSS live feed** from 20+ curated alternative/independent sources per topic (ScienceDaily, Consortium News, MoonOfAlabama, Common Dreams, Cointelegraph, Ars Technica, OurWorldInData, Pew Research, Gallup, etc.)
- **Audio TTS** with OpenAI TTS (tts-1, voices nova/alloy) for briefings; cached mp3 per briefing in Mongo. Player state machine (idle/loading/playing/paused).
- **Public shareable URLs** `/s/:id` — no auth required, auto-triggers deep-dive if missing, includes ClickableText + AudioButton + ShareButton.
- Graceful 429 handling for Gemini + Retry button in AskPage
- SheetDescription sr-only for a11y
- Full IT/EN i18n, Light/Dark theme, editorial Newsreader + Manrope + JetBrains Mono

## User Personas
- Curious non-technical adult wanting alternative news
- Analyst / researcher who wants deep-dives with data

## Backlog
- P1: real-time news via web-scraping / RSS integration to complement AI
- P1: email digest of preferred topics
- P2: audio mode (TTS) for accessibility
- P2: source citation links (real URLs)
- P2: share briefing via URL
