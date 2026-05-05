import json
import logging
import os
import re
from datetime import datetime
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

CHOOSING_TYPE, PRIVATE_STAMMDATEN, PRIVATE_MANGEL, COMMERCIAL_FLOW = range(4)

PRIVATE = "private"
COMMERCIAL = "commercial"

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)
TENANTS_FILE = DATA_DIR / "tenants.json"
MELDUNGEN_FILE = DATA_DIR / "mangelmeldungen.json"

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


def load_tenants() -> dict:
    if not TENANTS_FILE.exists():
        return {}
    try:
        data = json.loads(TENANTS_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}


def get_tenant(user_id: int) -> dict | None:
    return load_tenants().get(str(user_id))


def save_tenant(user_id: int, data: dict) -> None:
    tenants = load_tenants()
    tenants[str(user_id)] = {
        **data,
        "schritt": "stammdaten_komplett",
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
    TENANTS_FILE.write_text(
        json.dumps(tenants, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info("Saved Stammdaten for user_id=%s", user_id)


def save_meldung(user_id: int, mangel: dict) -> None:
    existing: list[dict] = []
    if MELDUNGEN_FILE.exists():
        try:
            loaded = json.loads(MELDUNGEN_FILE.read_text(encoding="utf-8"))
            if isinstance(loaded, list):
                existing = loaded
        except json.JSONDecodeError:
            existing = []
    existing.append({
        "user_id": user_id,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        **mangel,
    })
    MELDUNGEN_FILE.write_text(
        json.dumps(existing, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info("Saved Mangelmeldung for user_id=%s", user_id)


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


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    tenant = get_tenant(update.effective_user.id)
    if tenant:
        try:
            kickoff = await kickoff_mangel(context.user_data)
        except anthropic.APIError as e:
            logger.exception("Claude API error on returning-user kickoff")
            await update.message.reply_text(
                f"Willkommen zurück, {tenant.get('name', '')}! Leider ist der Assistent "
                f"gerade nicht erreichbar ({e.__class__.__name__}). Bitte versuchen Sie es gleich noch einmal."
            )
            return ConversationHandler.END
        await update.message.reply_html(
            f"Willkommen zurück, <b>{tenant.get('name', '')}</b>! Wir haben Ihre Stammdaten bereits.\n\n"
            f"{kickoff}"
        )
        return PRIVATE_MANGEL

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
    context.user_data["tenant_type"] = query.data

    if query.data == PRIVATE:
        context.user_data["stammdaten"] = {}
        context.user_data["field_index"] = 0
        first_question = STAMMDATEN_FIELDS[0][1]
        await query.edit_message_text(
            "Danke! Ich nehme jetzt kurz Ihre Stammdaten auf.\n\n" + first_question
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

    index = context.user_data.get("field_index", 0)
    field_key, _ = STAMMDATEN_FIELDS[index]
    context.user_data["stammdaten"][field_key] = answer

    next_index = index + 1
    if next_index < len(STAMMDATEN_FIELDS):
        context.user_data["field_index"] = next_index
        await update.message.reply_text(STAMMDATEN_FIELDS[next_index][1])
        return PRIVATE_STAMMDATEN

    data = context.user_data["stammdaten"]
    save_tenant(update.effective_user.id, data)
    summary = (
        "Vielen Dank, ich habe Ihre Stammdaten notiert:\n"
        f"• Name: {data['name']}\n"
        f"• Straße: {data['strasse']}\n"
        f"• Hausnummer: {data['hausnummer']}\n"
        f"• Etage: {data['etage']}\n"
        f"• Telefon: {data['telefon']}"
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

    data = extract_mangel(reply)
    if data:
        save_meldung(update.effective_user.id, data)
        visible = strip_mangel_json(reply)
        if visible:
            await update.message.reply_text(visible)
        await update.message.reply_text(
            "Ihre Mangelmeldung wurde aufgenommen. Wir melden uns zeitnah bei Ihnen."
        )
        return ConversationHandler.END

    await update.message.reply_text(reply)
    return PRIVATE_MANGEL


async def commercial_flow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # TODO: implement commercial-tenant workflow
    text = update.message.text
    context.user_data.setdefault("commercial_messages", []).append(text)
    await update.message.reply_text(
        f"[Gewerbe-Workflow] Eingang bestätigt:\n„{text}“\n\nNächster Schritt folgt …"
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
            COMMERCIAL_FLOW: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, commercial_flow)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel), CommandHandler("start", start)],
    )

    app.add_handler(conv)
    app.add_handler(CommandHandler("help", help_command))

    logger.info("Starting bot...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
