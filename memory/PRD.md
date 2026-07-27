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
- **Click-a-word to explain**: POST /api/explain returns short plain-language explanation; `<ClickableText>` component wraps significant words in Popover triggers inside headlines, summaries, deep-dive real_reasons/data_points/context and ask answers. Cached in Mongo `explanations` collection per language.
- Graceful 429 handling for Gemini concurrency limits (`llm_text`) + Retry button in AskPage
- SheetDescription sr-only added to DeepDiveSheet for a11y compliance
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
