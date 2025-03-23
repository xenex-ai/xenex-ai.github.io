import json
import random
import logging
import asyncio
from datetime import datetime, timezone

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# ------------------ Konfiguration ------------------ #
BOT_TOKEN = "7761649059:AAEQtfHDd1FXeE5wH3rPIyuXzBXnqB4eP94x"  # Bot-Token hier einfügen
GROUP_ID = -100173852517         # Gruppen-ID (Zahl) hier einfügen
ADMIN_USERS = ["w3kmdo", "Den_XNX"]  # Liste der Admin-Benutzernamen

# JSON-Dateien für die Speicherung
POINTS_FILE = "tst_point.json"
WALLETS_FILE = "tst_wallet.json"
QUESTIONS_FILE = "questions.json"

# Dauer einer Fragerunde (in Sekunden)
QUESTION_ROUND_DURATION = 3600  # 1 Stunde
# Intervall für Erinnerungen während der Fragerunde (in Sekunden)
REMINDER_INTERVAL = 1200        # alle 20 Minuten
# Fragerunde alle 3 Stunden starten (in Sekunden)
QUESTION_INTERVAL = 10800

# ------------------ Logging ------------------ #
logging.basicConfig(level=logging.INFO, format="%(asctime)s - [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# ------------------ Hilfsfunktionen ------------------ #
def load_data(filename: str) -> dict:
    """Lädt Daten aus einer JSON-Datei."""
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_data(filename: str, data: dict):
    """Speichert Daten in eine JSON-Datei."""
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

def get_storage(context: ContextTypes.DEFAULT_TYPE) -> dict:
    """
    Gibt ein veränderbares Dictionary zurück, in dem chatbezogene Daten gespeichert werden.
    Nutzt context.chat_data, oder legt in context.bot_data['chat_data'] einen Speicher an.
    """
    if context.chat_data is None:
        if "chat_data" not in context.bot_data:
            context.bot_data["chat_data"] = {}
        return context.bot_data["chat_data"]
    return context.chat_data

async def send_reply(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, reply_markup=None):
    """Sendet eine Antwort, egal ob als Nachricht oder als Antwort auf einen Button-Callback."""
    if update.message:
        await update.message.reply_text(text, reply_markup=reply_markup)
    elif update.callback_query and update.callback_query.message:
        await update.callback_query.message.reply_text(text, reply_markup=reply_markup)

def get_user_points(user_id: int) -> int:
    """Liest den aktuellen Punktestand eines Benutzers aus der JSON-Datei."""
    data = load_data(POINTS_FILE)
    uid = str(user_id)
    if uid in data:
        return data[uid].get("points", 0)
    return 0

# ------------------ Punktesystem ------------------ #
async def add_points(user_id: int, username: str, points: int):
    """Fügt einem Benutzer Punkte hinzu und speichert diese."""
    data = load_data(POINTS_FILE)
    uid = str(user_id)
    if uid not in data:
        data[uid] = {"username": username, "points": 0, "last_bonus": None}
    data[uid]["points"] += points
    save_data(POINTS_FILE, data)
    logger.info(f"✅ {username} erhielt {points} Punkte (Total: {data[uid]['points']}).")

async def show_ranking(context: ContextTypes.DEFAULT_TYPE):
    """Erstellt und sendet eine Rangliste (Top 10) basierend auf den Punkten."""
    data = load_data(POINTS_FILE)
    if not data:
        message = "📊 Bisher wurden keine Punkte vergeben."
    else:
        ranking = sorted(data.items(), key=lambda x: x[1]["points"], reverse=True)
        message = "🏆 **Top Punkteliste** 🏆\n\n"
        for i, (uid, info) in enumerate(ranking[:10], 1):
            message += f"{i}. {info['username']} – {info['points']} Punkte\n"
    await context.bot.send_message(chat_id=GROUP_ID, text=message)
    logger.info("📢 Rangliste gesendet.")

# ------------------ Fragerunden ------------------ #
async def start_question_round(context: ContextTypes.DEFAULT_TYPE):
    """
    Startet eine neue Fragerunde:
      - Wählt eine zufällige Frage aus questions.json.
      - Postet und pinnt die Frage in der Gruppe.
      - Plant Erinnerungen und einen Countdown.
      - Speichert die aktive Fragerunde im Speicher.
      - Hinweis: Die Punkte der Benutzer bleiben erhalten, Punkte werden in dieser Zeit nicht vergeben.
    """
    storage = get_storage(context)
    # Aktive Fragerunde überschreiben oder neu anlegen
    storage["active_question"] = {}

    # Lade Fragen aus der JSON-Datei
    questions_data = load_data(QUESTIONS_FILE)
    questions = questions_data.get("questions", [])
    if not questions:
        await context.bot.send_message(chat_id=GROUP_ID, text="❌ Keine Fragen gefunden!")
        return

    # Wähle eine zufällige Frage
    question = random.choice(questions)
    question_msg = await context.bot.send_message(
        chat_id=GROUP_ID,
        text=f"❓ {question}\n\n💡 **Antworte aktiv – der aktivste Beitrag erhält Bonuspunkte!**"
    )

    # Speichere die aktive Fragerunde inkl. Startzeit, Frage und leere Antwortliste
    storage["active_question"] = {
        "message_id": question_msg.message_id,
        "question": question,
        "start_time": datetime.now(timezone.utc),
        "responses": {}
    }

    # Pinn die Frage-Nachricht
    try:
        await context.bot.pin_chat_message(chat_id=GROUP_ID, message_id=question_msg.message_id)
    except Exception as e:
        logger.error(f"❌ Fehler beim Pinnen der Frage: {e}")

    # Plane Erinnerungen alle 20 Minuten während der Fragerunde (1 Stunde)
    for i in range(1, QUESTION_ROUND_DURATION // REMINDER_INTERVAL + 1):
        context.job_queue.run_once(reminder_message, when=i * REMINDER_INTERVAL, chat_id=GROUP_ID)
    # Plane das Ende der Fragerunde nach 1 Stunde
    context.job_queue.run_once(evaluate_question_round, when=QUESTION_ROUND_DURATION, chat_id=GROUP_ID)
    # Starte den Countdown-Job, der jede Minute die Frage aktualisiert
    indicator_job = context.job_queue.run_repeating(update_question_indicator, interval=60, first=60, chat_id=GROUP_ID)
    storage["indicator_job"] = indicator_job

async def update_question_indicator(context: ContextTypes.DEFAULT_TYPE):
    """Aktualisiert jede Minute den Countdown in der gepinnten Frage."""
    storage = get_storage(context)
    if "active_question" not in storage:
        return
    start_time = storage["active_question"]["start_time"]
    elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
    remaining = max(0, int(QUESTION_ROUND_DURATION - elapsed))
    minutes, seconds = divmod(remaining, 60)
    question = storage["active_question"]["question"]
    updated_text = (
        f"❓ {question}\n\n"
        f"⏳ Fragerunde aktiv: noch {minutes} Minuten und {seconds} Sekunden!"
    )
    try:
        await context.bot.edit_message_text(
            chat_id=GROUP_ID,
            message_id=storage["active_question"]["message_id"],
            text=updated_text
        )
    except Exception as e:
        logger.error(f"❌ Fehler beim Aktualisieren des Countdowns: {e}")

async def reminder_message(context: ContextTypes.DEFAULT_TYPE):
    """Sendet Erinnerungen während der Fragerunde (alle 20 Minuten)."""
    storage = get_storage(context)
    if "active_question" not in storage:
        return
    question = storage["active_question"]["question"]
    await context.bot.send_message(
        chat_id=GROUP_ID,
        text=(
            f"⏳ **Erinnerung!**\n\n"
            f"❓ *{question}*\n"
            f"💡 Antworte aktiv – der aktivste Beitrag erhält Bonuspunkte!"
        )
    )
    logger.info("🔔 Erinnerung gesendet.")

async def track_user_activity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Zählt die Antworten von Benutzern während einer aktiven Fragerunde.
    Dieser Handler wird zusätzlich zu normalen Nachrichten genutzt.
    """
    storage = get_storage(context)
    if "active_question" not in storage:
        return  # Keine aktive Fragerunde
    user = update.message.from_user
    uid = str(user.id)
    responses = storage["active_question"].setdefault("responses", {})
    if uid not in responses:
        responses[uid] = {"username": user.username or user.first_name, "messages": 0}
    responses[uid]["messages"] += 1
    logger.info(f"📩 {user.username} hat geantwortet (Total: {responses[uid]['messages']}).")

async def evaluate_question_round(context: ContextTypes.DEFAULT_TYPE):
    """
    Wertet die aktive Fragerunde aus:
      - Hebt den Pinnstatus der Frage auf.
      - Ermittelt den aktivsten Teilnehmer (maximale Nachrichten).
      - Belohnt diesen mit zufälligen Bonuspunkten (zwischen 100 und 250).
      - Sendet eine Zusammenfassung in die Gruppe.
      - Löscht die aktive Fragerunde aus dem Speicher.
    """
    storage = get_storage(context)
    if "active_question" not in storage:
        return

    # Unpin die Frage
    try:
        await context.bot.unpin_chat_message(chat_id=GROUP_ID, message_id=storage["active_question"]["message_id"])
    except Exception as e:
        logger.error(f"❌ Fehler beim Unpinnen der Frage: {e}")

    responses = storage["active_question"].get("responses", {})
    if not responses:
        await context.bot.send_message(chat_id=GROUP_ID, text="❌ Keine Antworten während der Fragerunde erhalten. Versuche es beim nächsten Mal!")
        logger.info("📉 Fragerunde: Keine Antworten erhalten.")
    else:
        top_uid, top_data = max(responses.items(), key=lambda x: x[1]["messages"])
        bonus = random.randint(100, 250)
        await add_points(int(top_uid), top_data["username"], bonus)
        await context.bot.send_message(
            chat_id=GROUP_ID,
            text=(
                f"🎉 **Fragerunde beendet!** 🎉\n\n"
                f"🏆 Der aktivste Teilnehmer war **{top_data['username']}** mit **{top_data['messages']}** Nachrichten.\n"
                f"💰 Er erhält **{bonus} Bonuspunkte**!"
            )
        )
        logger.info(f"🏅 {top_data['username']} wurde mit {bonus} Bonuspunkten belohnt.")

    if "indicator_job" in storage:
        storage["indicator_job"].schedule_removal()
    storage.pop("active_question", None)

# ------------------ Neue Mitglieder ------------------ #
async def greet_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Begrüßt neue Mitglieder mit einer zufälligen Nachricht und entfernt Nutzer ohne Benutzernamen.
    """
    greetings = [
        "Welcome to our Community, {name}! 🚀",
        "Hey {name}, great to have you here! 🌟",
        "Greetings, {name}! Enjoy your stay!",
        "Hello {name}! Let’s make this community awesome!",
        "Hi {name}, welcome aboard!"
    ]
    if update.message.new_chat_members:
        for member in update.message.new_chat_members:
            if not member.username:
                try:
                    await context.bot.ban_chat_member(chat_id=update.effective_chat.id, user_id=member.id)
                    logger.info(f"🚫 {member.first_name} wurde entfernt (kein Username).")
                except Exception as e:
                    logger.error(f"❌ Fehler beim Entfernen von {member.first_name}: {e}")
                continue
            welcome_text = random.choice(greetings).format(name=member.first_name)
            keyboard = [
                [InlineKeyboardButton("🌐 Website", url="https://xenexai.com")],
                [InlineKeyboardButton("🏢 HQ", url=f"https://xenex-ai.github.io/dev/27_tst_xnx.html?name={member.username}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await context.bot.send_message(chat_id=update.effective_chat.id, text=welcome_text, reply_markup=reply_markup)
            logger.info(f"👋 Begrüßung für {member.first_name} gesendet.")

# ------------------ Bot-Befehle ------------------ #
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/start – Begrüßt den Benutzer."""
    user = update.effective_user
    logger.info(f"👤 {user.username} hat /start verwendet.")
    await send_reply(update, context, "👋 Willkommen beim Community Bot! Nutze /pointlist, /claim oder /rewardlist für weitere Infos.")

async def pointlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/pointlist – Zeigt die aktuelle Punkte-Rangliste an."""
    user = update.effective_user
    logger.info(f"👤 {user.username} hat /pointlist verwendet.")
    await show_ranking(context)

async def claim(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /claim – Ermöglicht es dem Nutzer, seine Punkte einzulösen.
    Es wird ein Link generiert, der den Benutzernamen und den aktuellen Punktestand enthält.
    """
    user = update.effective_user
    points = get_user_points(user.id)
    url = f"https://xenex-ai.github.io/dev/27_tst_xnx.html?name={user.username}&address={points}"
    keyboard = [[InlineKeyboardButton("✅ Punkte einlösen", url=url)]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    logger.info(f"💰 {user.username} hat /claim verwendet (Punkte: {points}).")
    await send_reply(update, context, "💰 Klicke auf den Button, um deine Punkte einzulösen:", reply_markup=reply_markup)

async def rewardlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /rewardlist – Zeigt die Rangliste oder Übersicht der Bonusbelohnungen.
    (Hier als Alias zur Punkte-Rangliste realisiert.)
    """
    await pointlist(update, context)

# ------------------ Admin-Befehle ------------------ #
async def addpoints(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /addpoints <username> <points> – Fügt einem Benutzer Punkte hinzu.
    Nur für Admins.
    """
    user = update.effective_user
    if user.username not in ADMIN_USERS:
        await update.message.reply_text("⛔ Keine Berechtigung!")
        return
    try:
        target_username = context.args[0].lstrip("@")
        points = int(context.args[1])
        data = load_data(POINTS_FILE)
        found = False
        for uid, info in data.items():
            if info["username"].lower() == target_username.lower():
                info["points"] += points
                found = True
                save_data(POINTS_FILE, data)
                logger.info(f"🔹 {target_username} erhielt {points} Punkte (Total: {info['points']}).")
                await update.message.reply_text(f"✅ {target_username} erhielt {points} Punkte!")
                break
        if not found:
            await update.message.reply_text("⚠️ Benutzer nicht gefunden.")
    except Exception as e:
        logger.error(f"❌ Fehler beim Hinzufügen von Punkten: {e}")
        await update.message.reply_text("❌ Nutzung: /addpoints <username> <points>")

async def removepoints(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /removepoints <username> <points> – Entzieht einem Benutzer Punkte.
    Nur für Admins.
    """
    user = update.effective_user
    if user.username not in ADMIN_USERS:
        await update.message.reply_text("⛔ Keine Berechtigung!")
        return
    try:
        target_username = context.args[0].lstrip("@")
        points = int(context.args[1])
        data = load_data(POINTS_FILE)
        found = False
        for uid, info in data.items():
            if info["username"].lower() == target_username.lower():
                found = True
                if info["points"] >= points:
                    info["points"] -= points
                    save_data(POINTS_FILE, data)
                    logger.info(f"🔹 {target_username} wurden {points} Punkte entzogen (Total: {info['points']}).")
                    await update.message.reply_text(f"✅ {target_username} wurden {points} Punkte entzogen!")
                else:
                    await update.message.reply_text(f"{target_username} hat nicht genügend Punkte!")
                break
        if not found:
            await update.message.reply_text("⚠️ Benutzer nicht gefunden.")
    except Exception as e:
        logger.error(f"❌ Fehler beim Entfernen von Punkten: {e}")
        await update.message.reply_text("❌ Nutzung: /removepoints <username> <points>")

async def message_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /message <text> – Sendet eine Nachricht im Namen des Bots in die Gruppe.
    Nur für Admins.
    """
    user = update.effective_user
    if user.username not in ADMIN_USERS:
        await update.message.reply_text("⛔ Keine Berechtigung!")
        return
    try:
        text = " ".join(context.args)
        if not text:
            await update.message.reply_text("❌ Nutzung: /message <Text>")
            return
        await context.bot.send_message(chat_id=GROUP_ID, text=text)
        logger.info(f"📢 Admin {user.username} sendete Nachricht: {text}")
        await update.message.reply_text("✅ Nachricht gesendet!")
    except Exception as e:
        logger.error(f"❌ Fehler beim Senden der Nachricht: {e}")
        await update.message.reply_text("❌ Fehler beim Senden der Nachricht.")

async def addwallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /addwallet <solana_address> – Fügt einem Benutzer eine Solana-Adresse hinzu.
    """
    user = update.effective_user
    try:
        sol_address = context.args[0]
        data = load_data(WALLETS_FILE)
        uid = str(user.id)
        data[uid] = {"username": user.username or user.first_name, "solana_address": sol_address}
        save_data(WALLETS_FILE, data)
        logger.info(f"🔑 {user.username} fügte eine Wallet hinzu: {sol_address}")
        await update.message.reply_text("✅ Wallet hinzugefügt!")
    except Exception as e:
        logger.error(f"❌ Fehler beim Hinzufügen der Wallet: {e}")
        await update.message.reply_text("❌ Nutzung: /addwallet <solana_address>")

async def wallets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /wallets – Zeigt die Liste der registrierten Wallets (Benutzername und Adresse).
    """
    data = load_data(WALLETS_FILE)
    if not data:
        await update.message.reply_text("Keine Wallets registriert.")
        return
    message = "🔑 **Registrierte Wallets:**\n\n"
    for uid, info in data.items():
        message += f"{info['username']}: {info['solana_address']}\n"
    await update.message.reply_text(message)

async def hq(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /hq – Öffnet den HQ-Link mit dem Benutzernamen.
    """
    user = update.effective_user
    url = f"https://xenex-ai.github.io/dev/27_tst_xnx.html?name={user.username}"
    keyboard = [[InlineKeyboardButton("🏢 HQ", url=url)]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Öffne HQ:", reply_markup=reply_markup)

# ------------------ Buttons und CallbackQuery ------------------ #
async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Verarbeitet Klicks auf Inline-Buttons und leitet die entsprechenden Befehle ein.
    """
    query = update.callback_query
    await query.answer()
    command = query.data
    if command == "/start":
        await start(update, context)
    elif command == "/pointlist":
        await pointlist(update, context)
    elif command == "/claim":
        await claim(update, context)
    elif command == "/rewardlist":
        await rewardlist(update, context)
    elif command == "/hq":
        await hq(update, context)
    elif command == "/addpoints" and query.from_user.username in ADMIN_USERS:
        await query.message.reply_text("Nutze: /addpoints <username> <points>")
    elif command == "/message" and query.from_user.username in ADMIN_USERS:
        await query.message.reply_text("Nutze: /message <Text>")
    # Weitere Button-Optionen können ergänzt werden

# ------------------ Nachrichtenverarbeitung ------------------ #
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Verarbeitet normale Nachrichten:
      - Falls keine Fragerunde aktiv ist, werden 1–2 Punkte zufällig vergeben.
      - Ist eine Fragerunde aktiv, wird darauf hingewiesen, dass Punkte aktuell nicht vergeben werden.
    """
    storage = get_storage(context)
    if "active_question" in storage:
        await update.message.reply_text("Aktuell läuft eine Fragerunde – Punkte werden in dieser Zeit nicht vergeben.")
    else:
        user = update.message.from_user
        points = random.choice([1, 2])
        await add_points(user.id, user.username or user.first_name, points)
        await update.message.reply_text(f"{user.first_name}, du hast {points} Punkte erhalten!")

# ------------------ Befehlsliste als interaktive Buttons ------------------ #
async def commands_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Zeigt eine Befehlsübersicht mit interaktiven Buttons.
    Einige Befehle sind nur für Admins sichtbar.
    """
    keyboard = [
        [InlineKeyboardButton("🏁 Start", callback_data="/start")],
        [InlineKeyboardButton("📊 Punkteliste", callback_data="/pointlist")],
        [InlineKeyboardButton("💰 Punkte einlösen", callback_data="/claim")],
        [InlineKeyboardButton("🎖 Rewardliste", callback_data="/rewardlist")],
        [InlineKeyboardButton("🏢 HQ", callback_data="/hq")],
    ]
    if (update.message and update.message.from_user.username in ADMIN_USERS) or \
       (update.callback_query and update.callback_query.from_user.username in ADMIN_USERS):
        keyboard.append([InlineKeyboardButton("➕ Punkte vergeben", callback_data="/addpoints")])
        keyboard.append([InlineKeyboardButton("🗑 Punkte abziehen", callback_data="/removepoints")])
        keyboard.append([InlineKeyboardButton("📢 Nachricht senden", callback_data="/message")])
        keyboard.append([InlineKeyboardButton("🔑 Wallet hinzufügen", callback_data="/addwallet")])
        keyboard.append([InlineKeyboardButton("📋 Wallets", callback_data="/wallets")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await send_reply(update, context, "📌 **Befehlsübersicht**\nWähle einen Befehl:", reply_markup=reply_markup)

# ------------------ Hauptprogramm ------------------ #
def main():
    """Startet den Telegram-Bot."""
    application = Application.builder().token(BOT_TOKEN).build()

    # Registriere Bot-Befehle
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("pointlist", pointlist))
    application.add_handler(CommandHandler("claim", claim))
    application.add_handler(CommandHandler("rewardlist", rewardlist))
    application.add_handler(CommandHandler("addpoints", addpoints))
    application.add_handler(CommandHandler("removepoints", removepoints))
    application.add_handler(CommandHandler("message", message_cmd))
    application.add_handler(CommandHandler("addwallet", addwallet))
    application.add_handler(CommandHandler("wallets", wallets))
    application.add_handler(CommandHandler("hq", hq))
    application.add_handler(CommandHandler("help", commands_list))

    # Interaktive Buttons verarbeiten
    application.add_handler(CallbackQueryHandler(button_click))

    # Nachrichten: Punktevergabe und Activity-Tracking (für Fragerunden)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, track_user_activity))

    # Begrüßung neuer Mitglieder
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, greet_new_member))

    # JobQueue-Aufgaben:
    job_queue = application.job_queue
    # Rangliste täglich posten (alle 86400 Sekunden)
    job_queue.run_repeating(show_ranking, interval=86400, first=10)
    # Fragerunde alle 3 Stunden starten
    job_queue.run_repeating(start_question_round, interval=QUESTION_INTERVAL, first=10)

    logger.info("🤖 Bot gestartet!")
    application.run_polling()

if __name__ == "__main__":
    main()
