import json
import logging
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

import anthropic
from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

CHOOSING_TYPE, PRIVATE_STAMMDATEN, PRIVATE_MANGEL, PRIVATE_FOTOS, COMMERCIAL_FLOW = range(5)

PRIVATE = "private"
COMMERCIAL = "commercial"

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)
TENANTS_FILE = DATA_DIR / "tenants.json"
SESSIONS_FILE = DATA_DIR / "sessions.json"
PHOTOS_DIR = DATA_DIR / "photos"
PHOTOS_DIR.mkdir(exist_ok=True)

PHOTO_REQUEST_TEXT = (
    "Damit wir den Schaden besser einschätzen können, brauchen wir noch Fotos. "
    "Bitte schicken Sie die Bilder in dieser Reihenfolge:\n"
    "1. Ein Übersichtsfoto des gesamten Raumes\n"
    "2. Ein oder mehrere Detailfotos direkt vom Schaden\n\n"
    "So kann unser Team den richtigen Handwerker schneller beauftragen.\n\n"
    "Sobald Sie alle Bilder geschickt haben, klicken Sie unten auf den Fertig-Button."
)

FOTOS_FERTIG_CALLBACK = "fotos_fertig"
TIMING_CALLBACK_PREFIX = "timing:"


def _fertig_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("✅ Fertig", callback_data=FOTOS_FERTIG_CALLBACK)]]
    )

STAMMDATEN_FIELDS = [
    ("name", "Wie ist Ihr Name?"),
    ("strasse", "Wie heißt die Straße?"),
    ("hausnummer", "Wie lautet die Hausnummer?"),
    ("etage", "In welcher Etage oder Wohnungseinheit befinden Sie sich?"),
    ("telefon", "Unter welcher Telefonnummer können wir Sie für Rückfragen erreichen?"),
]

MANGEL_PROMPT = """
Du bist ein freundlicher Assistent der Hausverwaltung und erfasst einen Mangel eines privaten Mieters. Die Stammdaten wurden bereits aufgenommen.

Deine Aufgabe: Erfasse den Mangel so präzise wie möglich.

PHASE 1 — PFLICHTFRAGEN (diese 5 Fragen müssen alle gestellt werden):
1. Art des Mangels: Was genau ist das Problem?
2. Ort: In welchem Raum oder Bereich?
3. Ausmaß: Wie schwerwiegend? (komplett ausgefallen vs. eingeschränkt)
4. Zeitpunkt: Seit wann besteht der Mangel?
5. Ursache: Gab es ein auslösendes Ereignis?

PHASE 2 — VERTIEFUNG (maximal 3 weitere Nachrichten):
Stelle nur dann Folgefragen wenn sie wirklich relevant sind um das Problem besser einzuschätzen.
Nach spätestens 3 weiteren Nachrichten gibst du den JSON-Block aus.

Wenn alle Pflichtfragen beantwortet sind und Phase 2 abgeschlossen ist, gib NUR diesen JSON-Block aus — kein Text danach:

{
  "erfassung": "komplett",
  "zusammenfassung": "Kurze präzise Beschreibung in 2-3 Sätzen",
  "art": "",
  "ort": "",
  "ausmass": "",
  "seit": "",
  "ursache": ""
}

Regeln:
- Dem Mieter niemals Priorität oder Einschätzung nennen
- JSON nur ausgeben wenn alle 5 Pflichtfragen beantwortet sind
- Fehlende Infos nach Phase 2 mit "nicht angegeben" füllen
- Antworte immer auf Deutsch
- Du musst nicht wieder hallo sagen

FORMATIERUNG (sehr wichtig):
- Antworte ausschließlich als einfacher Fließtext, ohne Markdown.
- Keine Sterne (*, **), keine Unterstriche (_), keine Backticks (`), keine Überschriften (#), keine Aufzählungszeichen (-, •).
- Hervorhebungen einfach durch normale Worte ausdrücken, nicht durch Sonderzeichen.
- Wenn du eine Frage stellst, schreibe sie als ganzen Satz ohne Formatierung.
"""

MANGEL_JSON_RE = re.compile(
    r"\{[^{}]*\"erfassung\"\s*:\s*\"komplett\"[^{}]*\}",
    re.DOTALL,
)

claude = anthropic.AsyncAnthropic()


# ---------- helpers ----------

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def compose_adresse(strasse: str, hausnummer: str, etage: str) -> str:
    parts = [f"{strasse} {hausnummer}".strip()]
    if etage:
        parts.append(f"Etage {etage}")
    return ", ".join(p for p in parts if p)


def empty_session(chat_id: str, mietertyp: str = "") -> dict:
    ts = now_iso()
    return {
        "session_id": str(uuid.uuid4()),
        "chat_id": chat_id,
        "mietertyp": mietertyp,
        "erstellt_am": ts,
        "aktualisiert_am": ts,
        "stammdaten": {"name": "", "adresse": "", "telefon": ""},
        "mangelerfassung": {
            "timestamp": "",
            "status": "offen",
            "zusammenfassung": "",
            "art": "",
            "ausmass": "",
            "seit": "",
            "ursache": "",
        },
        "bilder": {},
    }


def _load_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


def _write_json(path: Path, data) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_tenants() -> dict:
    data = _load_json(TENANTS_FILE, {})
    return data if isinstance(data, dict) else {}


def get_tenant_by_chat(chat_id: str) -> dict | None:
    return load_tenants().get(str(chat_id))


def save_tenant_cache(chat_id: str, stammdaten: dict) -> None:
    tenants = load_tenants()
    tenants[str(chat_id)] = {
        **stammdaten,
        "aktualisiert_am": now_iso(),
    }
    _write_json(TENANTS_FILE, tenants)
    logger.info("Cached stammdaten for chat_id=%s", chat_id)


def upsert_session(session: dict) -> None:
    sessions = _load_json(SESSIONS_FILE, {})
    if not isinstance(sessions, dict):
        sessions = {}
    session["aktualisiert_am"] = now_iso()
    sessions[session["session_id"]] = session
    _write_json(SESSIONS_FILE, sessions)
    logger.info(
        "Saved session %s (status=%s, bilder=%d)",
        session["session_id"][:8],
        session["mangelerfassung"].get("status"),
        len(session.get("bilder") or {}),
    )


def extract_mangel(text: str) -> dict | None:
    for match in MANGEL_JSON_RE.findall(text):
        try:
            return json.loads(match)
        except json.JSONDecodeError:
            continue
    return None


def strip_mangel_json(text: str) -> str:
    return MANGEL_JSON_RE.sub("", text).strip()


async def ask_claude_mangel(messages: list[dict]) -> str:
    response = await claude.messages.create(
        model="claude-opus-4-7",
        max_tokens=1024,
        system=MANGEL_PROMPT,
        messages=messages,
    )
    return next((b.text for b in response.content if b.type == "text"), "")


async def kickoff_mangel(user_data: dict) -> str:
    user_data["mangel_messages"] = [
        {"role": "user", "content": "Hallo, ich möchte einen Mangel melden."}
    ]
    reply = await ask_claude_mangel(user_data["mangel_messages"])
    user_data["mangel_messages"].append({"role": "assistant", "content": reply})
    return reply


# ---------- handlers ----------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    chat_id = str(update.effective_chat.id)
    cached = get_tenant_by_chat(chat_id)

    if cached:
        session = empty_session(chat_id, mietertyp="privat")
        session["stammdaten"] = {
            "name": cached.get("name", ""),
            "adresse": cached.get("adresse", ""),
            "telefon": cached.get("telefon", ""),
        }
        upsert_session(session)
        context.user_data["session"] = session

        try:
            kickoff = await kickoff_mangel(context.user_data)
        except anthropic.APIError as e:
            logger.exception("Claude API error on returning-user kickoff")
            await update.message.reply_text(
                f"Willkommen zurück, {cached.get('name', '')}! Leider ist der Assistent "
                f"gerade nicht erreichbar ({e.__class__.__name__}). Bitte versuchen Sie es gleich noch einmal."
            )
            return ConversationHandler.END

        await update.message.reply_html(
            f"Willkommen zurück, <b>{cached.get('name', '')}</b>! Wir haben Ihre Stammdaten bereits.\n\n"
            f"{kickoff}"
        )
        return PRIVATE_MANGEL

    # New tenant
    context.user_data["session"] = empty_session(chat_id)

    keyboard = [
        [
            InlineKeyboardButton("Privater Mieter", callback_data=PRIVATE),
            InlineKeyboardButton("Gewerblicher Mieter", callback_data=COMMERCIAL),
        ]
    ]
    await update.message.reply_html(
        "Herzlich willkommen! Vielen Dank für Ihre Nachricht! Ich bin Ihr digitaler "
        "Assistent der Hausverwaltung und helfe Ihnen dabei, Ihren Mangel schnell "
        "und unkompliziert zu melden.\n\n"
        "Darf ich zunächst fragen: Sind Sie privater Mieter oder gewerblicher Mieter?",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return CHOOSING_TYPE


async def choose_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    session = context.user_data.setdefault(
        "session", empty_session(str(update.effective_chat.id))
    )
    session["mietertyp"] = "privat" if query.data == PRIVATE else "gewerblich"
    upsert_session(session)

    if query.data == PRIVATE:
        context.user_data["stammdaten_buffer"] = {
            "name": "",
            "strasse": "",
            "hausnummer": "",
            "etage": "",
            "telefon": "",
        }
        context.user_data["field_index"] = 0
        await query.edit_message_text(
            "Danke! Ich nehme jetzt kurz Ihre Stammdaten auf.\n\n"
            + STAMMDATEN_FIELDS[0][1]
        )
        return PRIVATE_STAMMDATEN

    await query.edit_message_text(
        "Danke! Sie sind als <b>gewerblicher Mieter</b> registriert.\n\n"
        "Bitte nennen Sie zuerst Ihre Firma und beschreiben Sie anschließend den Mangel.",
        parse_mode="HTML",
    )
    return COMMERCIAL_FLOW


async def private_stammdaten(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    answer = update.message.text.strip()
    if not answer:
        await update.message.reply_text("Bitte geben Sie eine Antwort ein.")
        return PRIVATE_STAMMDATEN

    buffer = context.user_data["stammdaten_buffer"]
    index = context.user_data.get("field_index", 0)
    field_key, _ = STAMMDATEN_FIELDS[index]
    buffer[field_key] = answer

    next_index = index + 1
    if next_index < len(STAMMDATEN_FIELDS):
        context.user_data["field_index"] = next_index
        await update.message.reply_text(STAMMDATEN_FIELDS[next_index][1])
        return PRIVATE_STAMMDATEN

    # All Stammdaten collected — map into new schema
    stammdaten = {
        "name": buffer["name"],
        "adresse": compose_adresse(buffer["strasse"], buffer["hausnummer"], buffer["etage"]),
        "telefon": buffer["telefon"],
    }

    chat_id = str(update.effective_chat.id)
    session = context.user_data["session"]
    session["stammdaten"] = stammdaten
    upsert_session(session)
    save_tenant_cache(chat_id, stammdaten)

    summary = (
        "Vielen Dank, ich habe Ihre Stammdaten notiert:\n"
        f"• Name: {stammdaten['name']}\n"
        f"• Adresse: {stammdaten['adresse']}\n"
        f"• Telefon: {stammdaten['telefon']}"
    )

    try:
        kickoff = await kickoff_mangel(context.user_data)
    except anthropic.APIError as e:
        logger.exception("Claude API error transitioning to mangel")
        await update.message.reply_text(
            f"{summary}\n\nLeider ist der Assistent gerade nicht erreichbar "
            f"({e.__class__.__name__}). Bitte versuchen Sie es mit /start erneut."
        )
        return ConversationHandler.END

    await update.message.reply_text(f"{summary}\n\nJetzt zum Mangel:\n\n{kickoff}")
    return PRIVATE_MANGEL


async def private_mangel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    messages = context.user_data.setdefault("mangel_messages", [])
    messages.append({"role": "user", "content": update.message.text})

    try:
        reply = await ask_claude_mangel(messages)
    except anthropic.APIError as e:
        logger.exception("Claude API error during mangel")
        messages.pop()
        await update.message.reply_text(
            f"Entschuldigung, der Assistent hat gerade ein Problem ({e.__class__.__name__}). "
            "Bitte wiederholen Sie Ihre letzte Nachricht."
        )
        return PRIVATE_MANGEL

    messages.append({"role": "assistant", "content": reply})

    parsed = extract_mangel(reply)
    if parsed:
        session = context.user_data["session"]
        session["mangelerfassung"] = {
            "timestamp": now_iso(),
            "status": "komplett",
            "zusammenfassung": parsed.get("zusammenfassung", ""),
            "art": parsed.get("art", ""),
            "ausmass": parsed.get("ausmass", ""),
            "seit": parsed.get("seit", ""),
            "ursache": parsed.get("ursache", ""),
        }
        # NB: schema doesn't include "ort"; we keep it inside zusammenfassung text
        upsert_session(session)

        visible = strip_mangel_json(reply)
        if visible:
            await update.message.reply_text(visible)
        await update.message.reply_text(PHOTO_REQUEST_TEXT)
        return PRIVATE_FOTOS

    await update.message.reply_text(reply)
    return PRIVATE_MANGEL


async def private_fotos(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    message = update.message
    session = context.user_data.get("session")
    if session is None:
        await message.reply_text("Sitzung nicht gefunden. Bitte starten Sie mit /start neu.")
        return ConversationHandler.END

    bilder = session.setdefault("bilder", {})

    if message.photo:
        photo = message.photo[-1]
        try:
            file = await photo.get_file()
        except Exception:
            logger.exception("Failed to get_file from Telegram")
            await message.reply_text("Das Bild konnte nicht geladen werden. Bitte erneut senden.")
            return PRIVATE_FOTOS

        chat_id = str(update.effective_chat.id)
        chat_dir = PHOTOS_DIR / chat_id
        chat_dir.mkdir(parents=True, exist_ok=True)

        index = len(bilder)
        slot = "bild_allgemein" if index == 0 else f"bild_{index}"
        timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
        path = chat_dir / f"{session['session_id'][:8]}_{slot}_{timestamp}.jpg"
        await file.download_to_drive(custom_path=str(path))

        bilder[slot] = str(path)
        upsert_session(session)

        label = "Übersichtsfoto" if slot == "bild_allgemein" else f"Detailfoto {index}"
        await message.reply_text(
            f"{label} gespeichert. Senden Sie weitere Fotos oder klicken Sie unten auf Fertig.",
            reply_markup=_fertig_keyboard(),
        )
        return PRIVATE_FOTOS

    text = (message.text or "").strip().lower()
    if text == "fertig":
        return await _finalize_fotos(session, reply=message.reply_text)

    await message.reply_text(
        "Bitte senden Sie ein Foto oder klicken Sie auf den Fertig-Button, wenn Sie alle Bilder geschickt haben.",
        reply_markup=_fertig_keyboard() if bilder else None,
    )
    return PRIVATE_FOTOS


async def _finalize_fotos(session: dict, reply) -> int:
    upsert_session(session)
    anzahl = len(session.get("bilder") or {})
    await reply(
        f"Vielen Dank! Ihre Mangelmeldung mit {anzahl} Foto(s) wurde aufgenommen. "
        "Wir melden uns zeitnah bei Ihnen."
    )
    return ConversationHandler.END


async def fotos_fertig(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    session = context.user_data.get("session")
    if session is None:
        await query.edit_message_text("Sitzung nicht gefunden. Bitte starten Sie mit /start neu.")
        return ConversationHandler.END
    return await _finalize_fotos(session, reply=query.edit_message_text)


async def timing_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    chat_id = str(update.effective_chat.id)
    raw = query.data or ""
    if not raw.startswith(TIMING_CALLBACK_PREFIX):
        return
    slot_id = raw[len(TIMING_CALLBACK_PREFIX):]

    sessions = _load_json(SESSIONS_FILE, {})
    if not isinstance(sessions, dict):
        await query.edit_message_text("Keine offenen Termine gefunden.")
        return

    target = None
    for s in sorted(
        sessions.values(),
        key=lambda x: x.get("aktualisiert_am", ""),
        reverse=True,
    ):
        if str(s.get("chat_id")) != chat_id:
            continue
        termine = s.get("termine") or {}
        if termine.get("vorgeschlagen") and not termine.get("ausgewaehlt"):
            target = s
            break

    if target is None:
        await query.edit_message_text("Keine offenen Termine gefunden.")
        return

    proposed = (target.get("termine") or {}).get("vorgeschlagen") or []
    chosen = next((t for t in proposed if t.get("id") == slot_id), None)
    if chosen is None:
        await query.edit_message_text("Termin nicht gefunden.")
        return

    target.setdefault("termine", {})["ausgewaehlt"] = {**chosen, "selected_at": now_iso()}
    target["aktualisiert_am"] = now_iso()
    sessions[target["session_id"]] = target
    _write_json(SESSIONS_FILE, sessions)

    handwerker_name = (target.get("handwerker") or {}).get("name", "Der Handwerker")
    await query.edit_message_text(
        f"Vielen Dank! Ihr Wunschtermin wurde festgehalten:\n\n{chosen['label']}\n\n"
        f"{handwerker_name} kommt zum vereinbarten Zeitpunkt vorbei. "
        "Sie erhalten vorab eine Bestätigung."
    )


async def commercial_flow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # TODO: implement commercial-tenant workflow
    text = update.message.text
    context.user_data.setdefault("commercial_messages", []).append(text)
    await update.message.reply_text(
        f'[Gewerbe-Workflow] Eingang bestätigt:\n„{text}"\n\nNächster Schritt folgt …'
    )
    return COMMERCIAL_FLOW


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Vorgang abgebrochen. Mit /start neu beginnen.")
    return ConversationHandler.END


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Befehle:\n/start - Mangelmeldung starten\n/cancel - Vorgang abbrechen\n/help - diese Nachricht"
    )


def main() -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set. Add it to .env")
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise RuntimeError("ANTHROPIC_API_KEY is not set. Add it to .env")

    app = Application.builder().token(token).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSING_TYPE: [
                CallbackQueryHandler(choose_type, pattern=f"^({PRIVATE}|{COMMERCIAL})$")
            ],
            PRIVATE_STAMMDATEN: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, private_stammdaten)
            ],
            PRIVATE_MANGEL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, private_mangel)
            ],
            PRIVATE_FOTOS: [
                CallbackQueryHandler(fotos_fertig, pattern=f"^{FOTOS_FERTIG_CALLBACK}$"),
                MessageHandler(filters.PHOTO | (filters.TEXT & ~filters.COMMAND), private_fotos),
            ],
            COMMERCIAL_FLOW: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, commercial_flow)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel), CommandHandler("start", start)],
    )

    app.add_handler(conv)
    app.add_handler(CallbackQueryHandler(timing_selected, pattern=f"^{re.escape(TIMING_CALLBACK_PREFIX)}"))
    app.add_handler(CommandHandler("help", help_command))

    logger.info("Starting bot...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
