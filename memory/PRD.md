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
- Frontend: Home feed + featured article + topic pills, Ask page, Login/Register, Saved list, Profile with preferences + language + logout
- Design: Editorial Truth (Newsreader serif + Manrope + JetBrains Mono, warm paper light theme, dark archive theme, accent red, cardless 1px borders, grain overlay, big tap targets ≥48px)
- Full IT/EN i18n
- Mobile bottom nav + desktop tab-bar
- data-testid on all interactive elements

## User Personas
- Curious non-technical adult wanting alternative news
- Analyst / researcher who wants deep-dives with data

## Backlog
- P1: real-time news via web-scraping / RSS integration to complement AI
- P1: email digest of preferred topics
- P2: audio mode (TTS) for accessibility
- P2: source citation links (real URLs)
- P2: share briefing via URL
