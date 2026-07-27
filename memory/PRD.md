# Lume Veritas - PRD

## Problem Statement
User wants a fast, functional web app that collects the newest, verified, deeply-analyzed news on topics mainstream journalists overlook (markets, population trends, polls, statistics, inventions, laws passed, scientific discoveries, political choices, wars & real reasons). User should be able to pick favorite topics, request deep-dives, and query any topic freely. Must be usable by tech-illiterate users. IT + EN.

## Stack
- Backend: FastAPI + MongoDB + Motor
- Auth: JWT + bcrypt (email/password)
- AI: Gemini 3 Flash preview via emergentintegrations (EMERGENT_LLM_KEY)
- Frontend: React 19 + Tailwind + Shadcn + Framer Motion + sonner + react-router

## Implemented (Feb 2026)
- JWT auth, topic catalog (16 default), user preferences
- **Custom topics**: users can add up to 30 personalized topics; auto-translated EN label via Gemini; appears in home pills with dashed border + accent dot. Backend: POST/GET/DELETE `/api/topics/custom`, `/api/topics/mine`, exposed via `/api/auth/me/full.custom_topics`.
- AI briefings (5/topic, 6h cache) via Gemini 3 Flash; deep-dive; free-form Ask
- Save / unsave briefings
- Click-a-word explain (Popover + cache)
- Daily email digest via Resend (APScheduler cron 08:00 Europe/Rome) + manual send-now
- RSS live feeds from 20+ independent sources per topic
- Audio TTS (OpenAI tts-1, nova/alloy) with Mongo mp3 cache
- Public shareable URLs `/s/:id` with **views counter** + **dynamic OG image** (1200x630 PNG via Pillow) + full Open Graph + Twitter Card via react-helmet-async
- Full IT/EN i18n, Light/Dark theme, editorial Newsreader + Manrope + JetBrains Mono
- Graceful 429/502 handling for Gemini + Resend + TTS

## User Personas
- Curious non-technical adult wanting alternative news
- Analyst / researcher who wants deep-dives with data

## Backlog
- P1: real-time news via web-scraping / RSS integration to complement AI
- P1: email digest of preferred topics
- P2: audio mode (TTS) for accessibility
- P2: source citation links (real URLs)
- P2: share briefing via URL
