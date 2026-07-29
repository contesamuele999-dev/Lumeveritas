# Deploy Lume Veritas — tutto gratis

Stack: **Render** (backend Docker + frontend statico) + **MongoDB Atlas M0** + **Gemini API** + **Resend**.
Costo: 0 €.

---

## 1. MongoDB Atlas (database)

1. https://www.mongodb.com/cloud/atlas → registrati.
2. Crea cluster **M0 Free** (regione Frankfurt o Ireland).
3. **Database Access** → crea utente + password (segnale).
4. **Network Access** → Add IP Address → `0.0.0.0/0` (Render non ha IP fisso sul piano free).
5. **Connect → Drivers** → copia la stringa `mongodb+srv://...`, sostituisci `<password>`.

Questa è la tua `MONGO_URL`.

## 2. Gemini API key

1. https://aistudio.google.com/apikey → **Create API key**.
2. Copia. Questa è `GEMINI_API_KEY`. Il tier gratuito basta per uso personale.

## 3. Resend (email digest, opzionale)

1. https://resend.com → API Keys → crea key = `RESEND_API_KEY`.
2. Senza dominio verificato Resend invia **solo alla tua email**. Per inviare a chiunque:
   Domains → verifica un dominio → poi cambia `SENDER_EMAIL`.

## 4. Repo GitHub

```bash
cd "Lume Veritas App"
git init
git add .
git commit -m "chore: deploy setup"
git branch -M main
git remote add origin https://github.com/TUO-UTENTE/lume-veritas.git
git push -u origin main
```

## 5. Render

1. https://render.com → registrati con GitHub.
2. **New → Blueprint** → seleziona il repo. Render legge `render.yaml` e crea 2 servizi.
3. Ti chiede le variabili `sync: false`. Compila:

   **lume-veritas-api**
   | Variabile | Valore |
   |---|---|
   | `MONGO_URL` | stringa Atlas del punto 1 |
   | `GEMINI_API_KEY` | key del punto 2 |
   | `RESEND_API_KEY` | key del punto 3 (o vuoto) |
   | `PUBLIC_APP_URL` | lascia vuoto per ora |
   | `CORS_ORIGINS` | lascia vuoto per ora |

   **lume-veritas**
   | Variabile | Valore |
   |---|---|
   | `REACT_APP_BACKEND_URL` | lascia vuoto per ora |

4. Apply. Al termine hai due URL, tipo:
   - backend `https://lume-veritas-api.onrender.com`
   - frontend `https://lume-veritas.onrender.com`

5. **Ora riempi i buchi** (Settings → Environment di ciascun servizio):
   - api: `PUBLIC_APP_URL` e `CORS_ORIGINS` = URL del **frontend**
   - frontend: `REACT_APP_BACKEND_URL` = URL del **backend**
   - Salva → Render ri-deploya da solo. Il frontend **va rebuildato** perché
     `REACT_APP_*` viene incorporata a build time (Manual Deploy → Clear cache & deploy).

## 6. Tenere sveglio il backend (importante)

Il piano free di Render mette il servizio in standby dopo 15 minuti di inattività:
il primo caricamento successivo impiega ~50 secondi, e **lo scheduler dei digest
(08:00 Europe/Rome) non parte se il servizio dorme**.

Fix gratis: https://uptimerobot.com → Add New Monitor → HTTP(s) →
URL `https://lume-veritas-api.onrender.com/api/` → intervallo 5 minuti.

## 7. Sviluppo locale

```bash
cd backend && cp .env.example .env   # compila i valori
pip install -r requirements.txt
uvicorn server:app --reload --port 8000
```

```bash
cd frontend && cp .env.example .env
yarn install && yarn start
```

---

## Cosa è cambiato rispetto a Emergent

| Prima | Ora |
|---|---|
| `emergentintegrations` + `EMERGENT_LLM_KEY` | `google-genai` + `GEMINI_API_KEY` diretta |
| TTS OpenAI (a pagamento) via `/api/tts` | Web Speech API del browser, zero backend, zero costi |
| Mongo gestito da Emergent | MongoDB Atlas M0 |
| Script `emergent-main.js` + PostHog in `index.html` | rimossi |
| `@emergentbase/visual-edits` | rimosso |

**Nota sulla voce**: la Web Speech API usa le voci del sistema operativo — su
Windows/Android/iOS la voce italiana c'è ed è decente, ma non è la voce OpenAI.
Se un giorno vuoi tornare a quella, serve una API key OpenAI a pagamento
(~$0,015 ogni 1000 caratteri).

## GitHub Pages invece di Render per il frontend?

Si può, ma serve `homepage` in `package.json`, `basename` sul router e il trucco
del `404.html` per il routing SPA. Render Static Site fa la stessa cosa gratis
con zero configurazione extra e sta nello stesso repo/blueprint del backend.
