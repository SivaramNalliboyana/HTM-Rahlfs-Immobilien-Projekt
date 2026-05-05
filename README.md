# Rahlfs Assistant — Telegram Bot + Cockpit Dashboard

End-to-end MVP for a German property manager (Hausverwaltung):

- **Telegram bot** — tenant reports a defect (Mangelmeldung) in chat. Claude asks the five mandatory questions (Art, Ort, Ausmaß, Seit, Ursache), photos are uploaded, the user clicks **Fertig**.
- **Backend API (FastAPI)** — reads the bot's session store, asks Claude to triage every case (Dringlichkeit + Handlungsempfehlungen), and exposes everything as JSON for the dashboard.
- **React cockpit** — live-polled dashboard with a Vorgang-Detail view, a "Handwerker zuweisen" modal that picks from a recommended list, and a one-click PDF export.
- **Bot ↔ admin loop** — when the admin assigns a Handwerker in the dashboard, the API sends 4 timing buttons to the user via Telegram. The user taps one — the chosen Termin shows up in the dashboard.

---

## Architecture

```
┌──────────────────┐     ┌─────────────────────┐     ┌──────────────────────┐
│  Telegram user   │◄───►│   bot.py (polling)  │     │  api.py (FastAPI)    │
└──────────────────┘     │  - intake (Claude)  │     │  - /api/cases        │
                         │  - photo upload     │     │  - triage (Claude)   │
                         │  - Fertig button    │     │  - /api/handwerker   │
                         │  - timing buttons   │◄────│  - assign → Telegram │
                         └──────────┬──────────┘     └──────────┬───────────┘
                                    │                            │
                                    ▼  read / write              ▼  read
                              ┌────────────────────────────────────┐
                              │  data/sessions.json                │
                              │  data/tenants.json                 │
                              │  data/photos/<chat_id>/*.jpg       │
                              └────────────────────────────────────┘
                                              ▲
                                              │  GET /api/cases (poll 4 s)
                                              │
                                ┌─────────────┴────────────┐
                                │  frontend (Vite + React) │
                                │  http://localhost:5173   │
                                │  - Dashboard             │
                                │  - Vorgang Detailansicht │
                                │  - Handwerker-Modal      │
                                │  - PDF Export            │
                                └──────────────────────────┘
```

Three independent processes — bot, API, frontend dev server — start each in its own terminal.

---

## Prerequisites

| Tool        | Version tested | Notes |
|-------------|----------------|-------|
| Python      | 3.11 – 3.13    | 3.13.3 used for development |
| Node.js     | 18+            | 22.x used for development |
| npm         | bundled with Node | yarn / pnpm also fine |
| Telegram    | any account    | needed to chat with the bot |
| Anthropic API key | any tier with `claude-opus-4-7` access | |

You also need:

- A **Telegram Bot token** — provided in the shared Google Drive folder alongside this submission.
- An **Anthropic API key** — please reach out to the devs and we'll share one.

---

## 1. Clone & enter the project

```powershell
git clone <repo-url> "HTM hack"
cd "HTM hack"
```

(Or unzip the submission and `cd` into it.)

---

## 2. Configure environment variables

Create a file named `.env` in the project root (same folder as `bot.py` / `api.py`):

```ini
TELEGRAM_BOT_TOKEN=123456789:AA-your-bot-token-from-BotFather
ANTHROPIC_API_KEY=sk-ant-api03-your-key-here
```

Both `bot.py` and `api.py` load this file via `python-dotenv`. The frontend does **not** need any env variables — it talks to the API through the Vite dev-server proxy.

---

## 3. Install Python dependencies

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1          # PowerShell
# or:  source .venv/bin/activate      # macOS / Linux / WSL
pip install -r requirements.txt
```

`requirements.txt` pins:

- `python-telegram-bot==21.6` — Telegram API client
- `anthropic==0.69.0` — Claude SDK
- `fastapi==0.115.0` + `uvicorn[standard]==0.30.6` — backend
- `python-dotenv==1.0.1` — env loader

---

## 4. Install frontend dependencies

In a **second terminal** (keep the venv terminal for Python):

```powershell
cd frontend
npm install
```

---

## 5. Start the three processes

You need **three terminals running at the same time**. Order doesn't strictly matter, but the bot and API both need the venv activated.

### Terminal A — Backend API (port 8000)

```powershell
.\.venv\Scripts\Activate.ps1
uvicorn api:app --reload --port 8000
```

### Terminal B — Telegram bot

```powershell
.\.venv\Scripts\Activate.ps1
python bot.py
```

You should see `Starting bot...` in the log. Now open Telegram, find your bot by the username you set in BotFather, send `/start`, and walk through the conversation.

### Terminal C — Frontend dashboard (port 5173)

```powershell
cd frontend
npm run dev
```

Open <http://localhost:5173>. Vite proxies `/api/*` and `/photos/*` to the FastAPI backend, so the React app behaves as if everything were on one origin.

---

## End-to-end test path (5 minutes)

This is the path the jury should walk:

1. **Tenant intake (Telegram).**
   - Send `/start` to the bot.
   - Choose **Privater Mieter**.
   - Answer the 5 Stammdaten questions (Name, Straße, Hausnummer, Etage, Telefon).
   - Describe a defect, e.g. *"Wasser tropft von der Decke im Wohnzimmer."*
   - Answer the bot's follow-ups until you receive the photo prompt.
   - Send 1–3 photos.
   - Tap the **✅ Fertig** inline button (it appears after every photo).
2. **Manager triage (Dashboard).**
   - Within ~4 seconds, the new case appears in the **Recent Cases** table at <http://localhost:5173>.
   - The KI-Empfehlung column shows `KI bewertet…` while Claude triages, then fills in `kritisch / hoch / mittel / niedrig`.
   - Click the row → **Vorgang Detail** opens with the AI summary, suggested actions with deadlines, and the photo gallery.
3. **Assign Handwerker.**
   - Click **Handwerker zuweisen** (top right).
   - The modal lists the top-4 mocked Handwerker; the best gewerk-match shows a **Bestmatch** badge.
   - Pick one → **Beauftragen & Termine senden**.
4. **Tenant picks a Termin (Telegram).**
   - The bot sends a follow-up message with **4 inline buttons** for next-week slots.
   - Tap one.
5. **Confirmation in dashboard.**
   - The detail page now shows a **Zugewiesener Handwerker** card with the chosen Termin.
6. **PDF export.**
   - Click **PDF generieren** → preview modal → **Als PDF speichern** → `Rahlfs_Vorgang_<id>.pdf` is generated client-side via `html2pdf.js`.

---

## Component cheat-sheet

| Path | What it is |
|------|------------|
| `bot.py` | Telegram bot. `ConversationHandler` runs intake → Stammdaten → Mangel-Dialog (Claude) → photo upload. Global `CallbackQueryHandler` handles the timing buttons sent by the API. |
| `api.py` | FastAPI app. Reads `sessions.json`, generates triage with Claude, exposes cases. New endpoints: `GET /api/cases/{id}/handwerker`, `POST /api/cases/{id}/assign_handwerker`. Sends Telegram messages directly via `telegram.Bot` when a Handwerker is assigned. |
| `frontend/src/pages/Dashboard.jsx` | Operational overview, polls every 4 s. |
| `frontend/src/pages/VorgangDetail.jsx` | Single-case view with triage card, Handwerker modal, status card, PDF preview. |
| `frontend/src/components/PdfPreview.jsx` | A4 layout + `html2pdf.js` export. |
| `pitch.html` / `pitch.pptx` | Pitch deck (HTML for live presenting, PPTX for handout). |
| `build_pitch_pptx.py` | Regenerates `pitch.pptx` from the HTML structure. |

---

## Tech stack summary

- **Python 3.13**, `python-telegram-bot` v21 (async), FastAPI, Pydantic, `python-dotenv`.
- **Anthropic Claude `claude-opus-4-7`** for both the in-chat Mangel interview and the manager-side triage. Two distinct prompts (`MANGEL_PROMPT` in `bot.py`, `TRIAGE_PROMPT` in `api.py`).
- **React 18 + Vite + Tailwind**, Material Symbols icons, `html2pdf.js` for client-side PDF.
- **Storage:** plain JSON + JPEG on disk under `data/`. No database. Deliberately simple so the loop stays tight during the hackathon.
