"""Read-only API exposing the chatbot's state to the React dashboard.

Schema written by bot.py (data/sessions.json, dict keyed by session_id).
This API additionally generates an AI triage record per case (urgency level
+ suggested actions for the facility manager) and persists it back to
sessions.json so each session is generated once.

Run: uvicorn api:app --reload --port 8000
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import anthropic
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATA_DIR = Path("data")
SESSIONS_FILE = DATA_DIR / "sessions.json"
PHOTOS_DIR = DATA_DIR / "photos"
PHOTOS_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Rahlfs Cockpit API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/photos", StaticFiles(directory=str(PHOTOS_DIR)), name="photos")

claude: anthropic.AsyncAnthropic | None = None
if os.getenv("ANTHROPIC_API_KEY"):
    claude = anthropic.AsyncAnthropic()
else:
    logger.warning("ANTHROPIC_API_KEY not set — triage generation disabled")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
_telegram_bot: Bot | None = None


def _get_telegram_bot() -> Bot | None:
    global _telegram_bot
    if _telegram_bot is None and TELEGRAM_TOKEN:
        _telegram_bot = Bot(token=TELEGRAM_TOKEN)
    return _telegram_bot


MOCK_HANDWERKER = [
    {
        "id": "hw1",
        "name": "Sanitär Müller GmbH",
        "gewerk": "Wasser & Sanitär",
        "rating": 4.8,
        "stundensatz": 75,
        "distance_km": 2.4,
        "verfuegbar": True,
        "telefon": "+49 30 12345678",
        "beschreibung": "Spezialist für Rohrbrüche, Lecks und Sanitärinstallationen. Schnelle Reaktionszeit.",
    },
    {
        "id": "hw2",
        "name": "Aquaprofis Berlin",
        "gewerk": "Wasser & Sanitär",
        "rating": 4.6,
        "stundensatz": 68,
        "distance_km": 5.1,
        "verfuegbar": True,
        "telefon": "+49 30 23456789",
        "beschreibung": "24/7 Notdienst. Erfahrener Partner bei Wasserschäden.",
    },
    {
        "id": "hw3",
        "name": "Heizung Schmidt & Söhne",
        "gewerk": "Heizung",
        "rating": 4.9,
        "stundensatz": 82,
        "distance_km": 3.7,
        "verfuegbar": True,
        "telefon": "+49 30 34567890",
        "beschreibung": "Heizungswartung, Reparatur und Modernisierung.",
    },
    {
        "id": "hw4",
        "name": "Elektro Wagner",
        "gewerk": "Elektrik",
        "rating": 4.7,
        "stundensatz": 78,
        "distance_km": 1.9,
        "verfuegbar": True,
        "telefon": "+49 30 45678901",
        "beschreibung": "Elektroinstallation, Steckdosen, Beleuchtung — Meisterbetrieb.",
    },
    {
        "id": "hw5",
        "name": "Schlüsseldienst Becker",
        "gewerk": "Schließanlage",
        "rating": 4.5,
        "stundensatz": 70,
        "distance_km": 2.8,
        "verfuegbar": True,
        "telefon": "+49 30 56789012",
        "beschreibung": "Schloss- und Türreparaturen, Notöffnung, Fensterservice.",
    },
    {
        "id": "hw6",
        "name": "Hausmeister Service Pro",
        "gewerk": "Allgemein",
        "rating": 4.3,
        "stundensatz": 55,
        "distance_km": 1.2,
        "verfuegbar": True,
        "telefon": "+49 30 67890123",
        "beschreibung": "Allgemeine Reparaturen rund ums Haus, Klein- und Sammelaufträge.",
    },
]


def _recommend_handwerker(category: str) -> list[dict]:
    matches = sorted(
        (h for h in MOCK_HANDWERKER if h["gewerk"] == category),
        key=lambda h: (-h["rating"], h["distance_km"]),
    )
    others = sorted(
        (h for h in MOCK_HANDWERKER if h["gewerk"] != category),
        key=lambda h: (-h["rating"], h["distance_km"]),
    )
    return (matches + others)[:4]


WEEKDAYS_DE = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]


def _next_week_timings() -> list[dict]:
    today = datetime.now().date()
    days_until_monday = (7 - today.weekday()) % 7 or 7
    monday = today + timedelta(days=days_until_monday)
    slots = [(0, "09:00"), (1, "14:00"), (2, "10:00"), (3, "16:00")]
    out = []
    for i, (offset, time) in enumerate(slots):
        date = monday + timedelta(days=offset)
        out.append(
            {
                "id": f"slot_{i}",
                "label": f"{WEEKDAYS_DE[date.weekday()]}, {date.strftime('%d.%m.%Y')} um {time}",
                "datum": date.isoformat(),
                "uhrzeit": time,
            }
        )
    return out


TRIAGE_PROMPT = """Du bist ein erfahrener Facility Manager bei einer deutschen Hausverwaltung. Du erhältst eine erfasste Mangelmeldung und musst sie für den Verwalter triagieren.

Liefere:
1. Dringlichkeitsstufe — basierend auf:
   - Sicherheit (Gas, Strom, Brand, akute Wassergefahr) → kritisch
   - Bewohnbarkeit eingeschränkt (kein Wasser, keine Heizung im Winter, kein Strom) → hoch
   - Beeinträchtigung, aber Wohnung nutzbar (Wasserschaden begrenzt, Heizung schwach) → mittel
   - Kosmetisch oder geringfügig → niedrig
2. Kurze Begründung warum diese Stufe (1-2 Sätze)
3. 2-4 konkrete Handlungsempfehlungen für den Hausverwalter, jeweils mit Frist
4. Ein-Satz-Zusammenfassung als Empfehlung

Gib NUR diesen JSON-Block aus, sonst nichts:

{
  "urgency": "kritisch | hoch | mittel | niedrig",
  "urgency_reason": "Begründung",
  "actions": [
    {"label": "Konkrete Handlung", "deadline": "sofort | 24h | diese Woche | nächste Woche"}
  ],
  "summary": "Empfehlung in einem Satz"
}

Regeln:
- Antworte ausschließlich auf Deutsch
- Empfehlungen müssen konkret und umsetzbar sein (welcher Gewerk, was tun)
- Keine Markdown-Formatierung im JSON
- Erfinde keine Details die nicht im Mangel stehen
"""

TRIAGE_JSON_RE = re.compile(r"\{[\s\S]*\}", re.DOTALL)

_triage_locks: set[str] = set()


def _load_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        logger.warning("Could not parse %s — returning default", path)
        return default


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _photo_url(stored_path: str) -> str:
    parts = Path(stored_path).parts
    if "photos" in parts:
        idx = parts.index("photos")
        return "/photos/" + "/".join(parts[idx + 1 :])
    return stored_path


def _category(mangel: dict) -> str:
    haystack = " ".join(
        str(mangel.get(k, "")).lower() for k in ("art", "zusammenfassung")
    )
    if any(k in haystack for k in ("wasser", "tropft", "leck", "feucht", "abfluss")):
        return "Wasser & Sanitär"
    if any(k in haystack for k in ("heizung", "kalt", "warm", "thermostat")):
        return "Heizung"
    if any(k in haystack for k in ("strom", "elektr", "licht", "steckdose")):
        return "Elektrik"
    if any(k in haystack for k in ("schlüssel", "tür", "schloss", "fenster")):
        return "Schließanlage"
    return "Allgemein"


def _short_id(session_id: str) -> str:
    digest = hashlib.sha1(session_id.encode("utf-8")).hexdigest()
    return f"{int(digest[:6], 16) % 100000:05d}"


def _format_relative(ts: str | None) -> str:
    if not ts:
        return ""
    try:
        if ts.endswith("Z"):
            ts = ts[:-1] + "+00:00"
        dt = datetime.fromisoformat(ts)
    except ValueError:
        return ts
    now = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    delta = now - dt
    secs = int(delta.total_seconds())
    if secs < 60:
        return "gerade eben"
    if secs < 3600:
        return f"vor {secs // 60} Min."
    if secs < 86400:
        return f"vor {secs // 3600} Std."
    days = secs // 86400
    if days == 1:
        return "gestern"
    return f"vor {days} Tagen"


def _load_sessions_dict() -> dict:
    raw = _load_json(SESSIONS_FILE, {})
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, list):
        return {s.get("session_id", str(i)): s for i, s in enumerate(raw)}
    return {}


def _persist_triage(session_id: str, triage: dict) -> None:
    sessions = _load_sessions_dict()
    if session_id not in sessions:
        return
    sessions[session_id]["triage"] = triage
    sessions[session_id]["aktualisiert_am"] = _now_iso()
    SESSIONS_FILE.write_text(
        json.dumps(sessions, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    logger.info("Persisted triage for session %s (urgency=%s)", session_id[:8], triage.get("urgency"))


async def _generate_triage(mangel: dict, tenant: dict) -> dict | None:
    if claude is None:
        return None
    user_message = (
        "Mangelmeldung:\n"
        f"Art: {mangel.get('art', '')}\n"
        f"Ausmaß: {mangel.get('ausmass', '')}\n"
        f"Seit: {mangel.get('seit', '')}\n"
        f"Ursache: {mangel.get('ursache', '')}\n"
        f"Zusammenfassung: {mangel.get('zusammenfassung', '')}\n"
        f"\nObjekt-Adresse: {tenant.get('adresse', '')}"
    )
    try:
        response = await claude.messages.create(
            model="claude-opus-4-7",
            max_tokens=1024,
            system=TRIAGE_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )
        text = next((b.text for b in response.content if b.type == "text"), "")
        match = TRIAGE_JSON_RE.search(text)
        if not match:
            logger.warning("Triage response had no JSON: %s", text[:200])
            return None
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            logger.warning("Triage JSON unparseable: %s", match.group(0)[:200])
            return None
    except anthropic.APIError as e:
        logger.warning("Triage API error: %s", e.__class__.__name__)
        return None


async def _generate_and_persist(session: dict) -> None:
    sid = session.get("session_id", "")
    if not sid or sid in _triage_locks:
        return
    _triage_locks.add(sid)
    try:
        triage = await _generate_triage(
            session.get("mangelerfassung") or {},
            session.get("stammdaten") or {},
        )
        if triage:
            _persist_triage(sid, triage)
    finally:
        _triage_locks.discard(sid)


URGENCY_TO_PRIORITY = {
    "kritisch": "emergency",
    "hoch": "emergency",
    "mittel": "normal",
    "niedrig": "low",
}


def _priority_from_triage(triage: dict | None) -> str:
    if not triage:
        return "low"
    return URGENCY_TO_PRIORITY.get((triage.get("urgency") or "").lower(), "low")


def _build_case(session: dict) -> dict:
    sid = session.get("session_id", "")
    stamm = session.get("stammdaten") or {}
    mangel = session.get("mangelerfassung") or {}
    bilder = session.get("bilder") or {}
    triage = session.get("triage")

    foto_urls: list[str] = []
    if bilder.get("bild_allgemein"):
        foto_urls.append(_photo_url(bilder["bild_allgemein"]))
    detail_keys = sorted(
        (k for k in bilder.keys() if k.startswith("bild_") and k != "bild_allgemein"),
        key=lambda k: int(k.split("_", 1)[1]) if k.split("_", 1)[1].isdigit() else 0,
    )
    for k in detail_keys:
        if bilder[k]:
            foto_urls.append(_photo_url(bilder[k]))

    timestamp = mangel.get("timestamp") or session.get("aktualisiert_am") or session.get("erstellt_am")

    return {
        "id": _short_id(sid),
        "session_id": sid,
        "chat_id": session.get("chat_id", ""),
        "mietertyp": session.get("mietertyp", ""),
        "timestamp": timestamp,
        "erstellt_am": session.get("erstellt_am"),
        "relative_time": _format_relative(timestamp),
        "status": mangel.get("status", "offen"),
        "tenant": {
            "name": stamm.get("name", ""),
            "adresse": stamm.get("adresse", ""),
            "telefon": stamm.get("telefon", ""),
        },
        "mangel": {
            "zusammenfassung": mangel.get("zusammenfassung", ""),
            "art": mangel.get("art", ""),
            "ausmass": mangel.get("ausmass", ""),
            "seit": mangel.get("seit", ""),
            "ursache": mangel.get("ursache", ""),
        },
        "fotos": foto_urls,
        "category": _category(mangel),
        "triage": triage,
        "priority": _priority_from_triage(triage),
        "triage_pending": triage is None,
        "handwerker": session.get("handwerker"),
        "termine": session.get("termine"),
    }


def _completed_sessions() -> list[dict]:
    return [
        s
        for s in _load_sessions_dict().values()
        if (s.get("mangelerfassung") or {}).get("status") == "komplett"
    ]


def _kickoff_missing_triage(sessions: list[dict]) -> None:
    if claude is None:
        return
    for s in sessions:
        if s.get("triage"):
            continue
        sid = s.get("session_id", "")
        if not sid or sid in _triage_locks:
            continue
        asyncio.create_task(_generate_and_persist(s))


@app.get("/api/health")
def health() -> dict:
    return {"ok": True, "triage_enabled": claude is not None}


@app.get("/api/cases")
async def list_cases() -> list[dict]:
    sessions = _completed_sessions()
    _kickoff_missing_triage(sessions)
    cases = [_build_case(s) for s in sessions]
    cases.sort(key=lambda c: c.get("timestamp") or "", reverse=True)
    return cases


@app.get("/api/cases/{case_id}")
async def get_case(case_id: str) -> dict:
    case_id = case_id.lstrip("#")
    sessions = _completed_sessions()
    target: dict | None = None
    for s in sessions:
        sid = s.get("session_id", "")
        if _short_id(sid) == case_id or sid == case_id:
            target = s
            break
    if target is None:
        raise HTTPException(status_code=404, detail="Case not found")

    if not target.get("triage") and claude is not None:
        await _generate_and_persist(target)
        target = next(
            (s for s in _completed_sessions() if s.get("session_id") == target["session_id"]),
            target,
        )

    return _build_case(target)


@app.post("/api/cases/{case_id}/triage/regenerate")
async def regenerate_triage(case_id: str) -> dict:
    case_id = case_id.lstrip("#")
    target = next(
        (
            s
            for s in _completed_sessions()
            if _short_id(s.get("session_id", "")) == case_id or s.get("session_id") == case_id
        ),
        None,
    )
    if target is None:
        raise HTTPException(status_code=404, detail="Case not found")
    if claude is None:
        raise HTTPException(status_code=503, detail="ANTHROPIC_API_KEY not configured")
    target.pop("triage", None)
    await _generate_and_persist(target)
    fresh = next(
        (s for s in _completed_sessions() if s.get("session_id") == target["session_id"]),
        target,
    )
    return _build_case(fresh)


def _find_session_by_case_id(case_id: str, sessions: dict) -> dict | None:
    for s in sessions.values():
        sid = s.get("session_id", "")
        if _short_id(sid) == case_id or sid == case_id:
            return s
    return None


@app.get("/api/cases/{case_id}/handwerker")
async def list_handwerker(case_id: str) -> dict:
    case_id = case_id.lstrip("#")
    sessions = _load_sessions_dict()
    target = _find_session_by_case_id(case_id, sessions)
    if target is None:
        raise HTTPException(status_code=404, detail="Case not found")
    category = _category(target.get("mangelerfassung") or {})
    return {
        "case_id": case_id,
        "category": category,
        "recommendations": _recommend_handwerker(category),
        "already_assigned": target.get("handwerker"),
    }


class AssignBody(BaseModel):
    handwerker_id: str


@app.post("/api/cases/{case_id}/assign_handwerker")
async def assign_handwerker(case_id: str, body: AssignBody) -> dict:
    case_id = case_id.lstrip("#")
    sessions = _load_sessions_dict()
    target = _find_session_by_case_id(case_id, sessions)
    if target is None:
        raise HTTPException(status_code=404, detail="Case not found")
    handwerker = next((h for h in MOCK_HANDWERKER if h["id"] == body.handwerker_id), None)
    if handwerker is None:
        raise HTTPException(status_code=404, detail="Handwerker not found")

    timings = _next_week_timings()

    target["handwerker"] = {
        "id": handwerker["id"],
        "name": handwerker["name"],
        "gewerk": handwerker["gewerk"],
        "telefon": handwerker["telefon"],
        "assigned_at": _now_iso(),
    }
    target["termine"] = {
        "vorgeschlagen": timings,
        "ausgewaehlt": None,
    }
    target["aktualisiert_am"] = _now_iso()
    sessions[target["session_id"]] = target
    SESSIONS_FILE.write_text(
        json.dumps(sessions, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    chat_id = target.get("chat_id")
    bot = _get_telegram_bot()
    if bot and chat_id:
        text = (
            f"Wir haben einen Handwerker für Sie gefunden:\n\n"
            f"{handwerker['name']} ({handwerker['gewerk']})\n\n"
            f"Bitte wählen Sie einen passenden Termin in der nächsten Woche:"
        )
        keyboard = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton(t["label"], callback_data=f"timing:{t['id']}")]
                for t in timings
            ]
        )
        try:
            await bot.send_message(
                chat_id=int(chat_id), text=text, reply_markup=keyboard
            )
        except Exception as e:
            logger.warning("Failed to send Telegram message to %s: %s", chat_id, e)
    else:
        logger.warning(
            "Skipping Telegram notification (bot=%s, chat_id=%s)", bool(bot), chat_id
        )

    return _build_case(target)


@app.get("/api/stats")
async def stats() -> dict:
    sessions = _completed_sessions()
    by_priority = {"emergency": 0, "normal": 0, "low": 0}
    for s in sessions:
        p = _priority_from_triage(s.get("triage"))
        by_priority[p] = by_priority.get(p, 0) + 1
    return {
        "open_cases": len(sessions),
        "by_priority": by_priority,
        "sessions_total": len(_load_sessions_dict()),
        "triage_enabled": claude is not None,
    }
