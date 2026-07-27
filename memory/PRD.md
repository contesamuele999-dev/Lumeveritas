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
- **Custom topics with kind**: users can add up to 30 personalized channels — Argomento, Persona, Telegram, Hashtag, Altro canale. Each stores kind + optional source. Briefing prompt adapts based on kind.
- AI briefings (5/topic, 6h cache) via Gemini 3 Flash; deep-dive; free-form Ask
- **Article-specific Q&A** (`POST /api/news/{id}/qa`) — chat-like follow-ups inside the Deep Dive sheet, stored in article_qas
- **Virtual expert debate** (`POST /api/news/{id}/debate`) — 3 personas with contrasting views + synthesis, cached per (briefing_id, language)
- **Deep Dive Sheet with tabs**: Approfondisci · Domande · Dibattito
- Save / unsave briefings
- Click-a-word explain
- **Digest email** via Resend with frequency picker (daily 08:00 / weekly Monday 08:00 Europe/Rome) + manual send-now
- RSS live feeds (20+ independent sources)
- Audio TTS (OpenAI tts-1) with mp3 cache
- Public shareable URLs `/s/:id` with views counter + dynamic OG image
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
