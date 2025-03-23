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

# ------------------ Bot-Konfiguration ------------------ #
BOT_TOKEN = "7761649059:AAEQtfHDd1FXeE5wH3rPIyuXzBXnqB4eP94"
CHANNEL_ID = "@xentst"
GROUP_ID = "-1001734852517"
ADMIN_USERS = ["w3kmdo", "Den_XNX"]

# ------------------ JSON-Dateien ------------------ #
POINTS_FILE = "tst_point.json"
WALLETS_FILE = "tst_wallet.json"
QUESTIONS_FILE = "questions.json"

# ------------------ Logging einrichten ------------------ #
logging.basicConfig(level=logging.INFO, format="%(asctime)s - [%(levelname)s] %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)

# ------------------ Level-Bereiche ------------------ #
LEVELS = {
    1: 0,
    2: 250,
    3: 500,
    4: 750,
    5: 1000,
    6: 2500,
    7: 5000,
    8: 10000
}

# ------------------ Hilfsfunktionen ------------------ #
def log_action(action: str):
    """Loggt Aktionen mit Zeitstempel."""
    logging.info(action)

def load_data(file: str) -> dict:
    """Lädt Daten aus einer JSON-Datei."""
    try:
        with open(file, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_data(file: str, data: dict):
    """Speichert Daten in eine JSON-Datei."""
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

def get_user_level(points: int) -> int:
    """Ermittelt das Level basierend auf den Punkten."""
    for level, required_points in sorted(LEVELS.items(), reverse=True):
        if points >= required_points:
            return level
    return 1

async def send_reply(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, reply_markup=None):
    """Hilfsfunktion zum Antworten – egal ob über Message oder CallbackQuery."""
    if update.message:
        await update.message.reply_text(text, reply_markup=reply_markup)
    elif update.callback_query and update.callback_query.message:
        await update.callback_query.message.reply_text(text, reply_markup=reply_markup)

def get_storage(context: ContextTypes.DEFAULT_TYPE) -> dict:
    """
    Gibt ein veränderbares Dictionary zurück, in dem Chat-bezogene Daten gespeichert werden.
    Falls context.chat_data None ist, wird ein Dictionary in context.bot_data["chat_data"] verwendet.
    """
    if context.chat_data is None:
        if "chat_data" not in context.bot_data:
            context.bot_data["chat_data"] = {}
        return context.bot_data["chat_data"]
    return context.chat_data

# ------------------ Punktesystem ------------------ #
async def add_points(user_id, username, points: int):
    """Fügt Punkte hinzu und speichert sie."""
    data = load_data(POINTS_FILE)
    uid = str(user_id)
    if uid not in data:
        data[uid] = {"username": username, "points": 0, "last_bonus": None}
    data[uid]["points"] += points
    save_data(POINTS_FILE, data)
    log_action(f"✅ {username} erhielt {points} Punkte! (Total: {data[uid]['points']})")

async def show_ranking(context: ContextTypes.DEFAULT_TYPE):
    """Zeigt die Rangliste der Top 10 Benutzer an."""
    data = load_data(POINTS_FILE)
    if not data:
        message = "📊 Noch keine Punkte vergeben."
    else:
        ranking = sorted(data.items(), key=lambda x: x[1]["points"], reverse=True)
        message = "🏆 **Top Punkteliste** 🏆\n\n"
        for i, (user_id, info) in enumerate(ranking[:10], 1):
            level = get_user_level(info["points"])
            message += f"{i}. {info['username']} - {info['points']} Punkte (Level {level})\n"
    log_action("📢 Rangliste gesendet")
    await context.bot.send_message(chat_id=GROUP_ID, text=message)

# ------------------ Countdown-Aktualisierung ------------------ #
async def update_question_indicator(context: ContextTypes.DEFAULT_TYPE):
    """
    Aktualisiert die Frage-Nachricht mit einem Countdown, der anzeigt, wie lange die Fragerunde noch aktiv ist.
    """
    storage = get_storage(context)
    if "active_question" not in storage:
        return  # Keine aktive Fragerunde
    start_time = storage["active_question"]["start_time"]
    elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
    remaining = int(3600 - elapsed)
    if remaining < 0:
        remaining = 0
    message_id = storage["active_question"]["message_id"]
    question = storage["active_question"]["question"]
    updated_text = (
        f"❓ {question}\n\n"
        f"⏳ Fragerunde aktiv: noch {remaining // 60} Minuten und {remaining % 60} Sekunden!"
    )
    try:
        await context.bot.edit_message_text(
            chat_id=GROUP_ID,
            message_id=message_id,
            text=updated_text
        )
    except Exception as e:
        log_action(f"❌ Fehler beim Aktualisieren der Frageanzeige: {e}")

# ------------------ Fragerunden ------------------ #
async def start_question_round(context: ContextTypes.DEFAULT_TYPE):
    """
    Startet eine neue Fragerunde:
      - Wählt eine zufällige Frage aus.
      - Die Fragerunde dauert 1 Stunde (3600 Sekunden).
      - Während der Fragerunde werden KEINE Punkte vergeben.
      - Die Frage wird angepinnt.
      - Erinnerungsnachrichten werden alle 20 Minuten gesendet.
      - Der Countdown wird jede Minute aktualisiert.
    """
    storage = get_storage(context)
    storage.clear()  # Vorherigen Speicher leeren
    storage["question_round_started"] = True

    questions = load_data(QUESTIONS_FILE).get("questions", [])
    if not questions:
        await context.bot.send_message(chat_id=GROUP_ID, text="❌ Keine Fragen gefunden.")
        return

    question = random.choice(questions)
    question_message = await context.bot.send_message(
        chat_id=GROUP_ID,
        text=f"❓ {question}\n\n💡 **Antworte aktiv – nur der Gewinner erhält Extrapunkte!**"
    )

    # Speichere aktive Fragerunde inkl. Startzeit und Antworten
    storage["active_question"] = {
        "message_id": question_message.message_id,
        "question": question,
        "start_time": datetime.now(timezone.utc),
        "responses": {}
    }

    # Frage anpinnen
    try:
        await context.bot.pin_chat_message(chat_id=GROUP_ID, message_id=question_message.message_id)
    except Exception as e:
        log_action(f"❌ Fehler beim Anpinnen der Frage: {e}")

    log_action(f"📢 Neue Frage gestartet: {question}")

    # Plane Erinnerungen (alle 20 Minuten) und das Ende der Fragerunde (nach 1 Stunde)
    for i in range(1, 4):
        context.job_queue.run_once(reminder_message, when=i * 1200, chat_id=GROUP_ID)
    context.job_queue.run_once(evaluate_question_round, when=3600, chat_id=GROUP_ID)
    # Countdown wird jede Minute aktualisiert
    indicator_job = context.job_queue.run_repeating(update_question_indicator, interval=60, first=60, chat_id=GROUP_ID)
    storage["indicator_job"] = indicator_job

# Alias für JobQueue-Aufruf
start_random_question = start_question_round

async def track_user_activity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Erfasst die Nachrichtenaktivität der Benutzer während einer aktiven Fragerunde.
    """
    storage = get_storage(context)
    if "active_question" not in storage:
        log_action(f"⚠️ active_question not in storage.")
        return

    user = update.message.from_user
    user_id = str(user.id)
    responses = storage["active_question"].setdefault("responses", {})
    if user_id not in responses:
        responses[user_id] = {
            "username": user.username or user.first_name,
            "messages": 0
        }
    responses[user_id]["messages"] += 1
    log_action(f"📩 {user.username} hat auf die Frage geantwortet (Total: {responses[user_id]['messages']}).")

async def evaluate_question_round(context: ContextTypes.DEFAULT_TYPE):
    """
    Wertet die Fragerunde aus (nach 1 Stunde):
      - Hebt die Pinnung der Frage auf.
      - Ermittelt den aktivsten Teilnehmer.
      - Vergibt Extrapunkte (zwischen 100 und 250) an den Gewinner.
      - Zelebriert den Gewinner öffentlich.
    """
    storage = get_storage(context)
    if not storage or "active_question" not in storage:
        return

    # Pinnung aufheben
    try:
        await context.bot.unpin_chat_message(chat_id=GROUP_ID, message_id=storage["active_question"]["message_id"])
    except Exception as e:
        log_action(f"❌ Fehler beim Lösen der Frage: {e}")

    responses = storage["active_question"].get("responses", {})
    if not responses:
        await context.bot.send_message(
            chat_id=GROUP_ID,
            text="❌ Leider gab es keine Antworten auf die Frage. Vielleicht beim nächsten Mal!"
        )
        log_action("📉 Keine Antworten erhalten.")
    else:
        top_user = max(responses.items(), key=lambda x: x[1]["messages"])
        user_id, user_info = top_user
        top_username = user_info["username"]
        top_messages = user_info["messages"]
        reward_points = random.randint(100, 250)
        await add_points(user_id, top_username, reward_points)
        await context.bot.send_message(
            chat_id=GROUP_ID,
            text=(
                f"🎉 **Die Fragerunde ist beendet!** 🎉\n\n"
                f"🏆 **{top_username}** war der aktivste Teilnehmer mit **{top_messages} Nachrichten** und erhält **{reward_points} Extrapunkte**!\n\n"
                f"🥳 Herzlichen Glückwunsch an den Gewinner!"
            )
        )
        log_action(f"🏅 {top_username} wurde mit {reward_points} Extrapunkten belohnt!")
    if "indicator_job" in storage:
        storage["indicator_job"].schedule_removal()
    del storage["active_question"]

async def reminder_message(context: ContextTypes.DEFAULT_TYPE):
    """
    Sendet alle 20 Minuten während der Fragerunde eine Erinnerung, damit alle aktiv teilnehmen.
    """
    storage = get_storage(context)
    if not storage or "active_question" not in storage:
        return
    question = storage["active_question"]["question"]
    await context.bot.send_message(
        chat_id=GROUP_ID,
        text=(
            f"⏳ **Erinnerung!**\n\n"
            f"❓ *{question}*\n"
            f"💡 **Antworte aktiv – nur der Gewinner erhält Extrapunkte!**"
        )
    )
    log_action("🔔 Erinnerung gesendet.")

async def remind_bonus_points(context: ContextTypes.DEFAULT_TYPE):
    """
    Sendet Erinnerungen basierend auf der verbleibenden Zeit der Fragerunde.
    """
    storage = get_storage(context)
    if not storage or "active_question" not in storage:
        return
    round_start = storage["active_question"]["start_time"]
    elapsed = (datetime.now(timezone.utc) - round_start).total_seconds()
    remaining = 3600 - elapsed  # 1 Stunde Fragerunde
    if remaining > 0:
        remaining_minutes = int(remaining // 60)
        await context.bot.send_message(
            chat_id=GROUP_ID,
            text=f"🔔 **Erinnerung:** Noch {remaining_minutes} Minuten, um teilzunehmen und Extrapunkte zu gewinnen! 🏆"
        )
        log_action(f"🔔 Erinnerung gesendet: Noch {remaining_minutes} Minuten.")
    else:
        await context.bot.send_message(
            chat_id=GROUP_ID,
            text="⏰ **Die Fragerunde ist beendet!** Vielen Dank für die Teilnahme! 🎉"
        )
        if "active_question" in storage:
            del storage["active_question"]

# ------------------ Neue Mitglieder ------------------ #
async def greet_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Begrüßt neue Mitglieder mit einem zufälligen Text und entfernt Nutzer ohne Benutzernamen.
    """
    greetings = [
        "Welcome to XenexAi, {name}! 🚀 Get ready for an epic journey!",
        "Hey {name}, great to have you here! 🌌 Explore the future with us.",
        "Greetings, {name}! 🛸 You're now part of the XenexAi revolution!",
        "Welcome aboard, {name}! 🤖 Let’s shape the future together.",
        "Hello {name}! 🌟 Dive into the world of XenexAi and enjoy the ride!"
    ]
    if update.message.new_chat_members:
        for member in update.message.new_chat_members:
            if not member.username:
                await context.bot.ban_chat_member(chat_id=update.effective_chat.id, user_id=member.id)
                log_action(f"🚫 {member.first_name} wurde entfernt (kein Benutzername).")
                continue
            welcome_text = random.choice(greetings).format(name=member.first_name)
            keyboard = [
                [InlineKeyboardButton("🌐 Website", url="https://xenexai.com")],
                [InlineKeyboardButton("🏢 Headquarters", url=f"https://xenex-ai.github.io/dev/26_tst_xnx.html?name={member.username}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await context.bot.send_message(chat_id=update.effective_chat.id, text=welcome_text, reply_markup=reply_markup)
            log_action(f"👋 Begrüßung an {member.first_name} gesendet.")

# ------------------ Befehle ------------------ #
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Begrüßt den Nutzer (Startbefehl)."""
    user = update.message.from_user if update.message else update.callback_query.from_user
    log_action(f"👤 {user.username} hat /start verwendet.")
    await send_reply(update, context, "👋 Willkommen beim Xenex AI Community Bot! Nutze /pointlist, um die Rangliste zu sehen.")

async def commands_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Zeigt eine Übersicht der Befehle an."""
    keyboard = [
        [InlineKeyboardButton("🏁 Start", callback_data="/start")],
        [InlineKeyboardButton("📊 Punkteliste", callback_data="/pointlist")],
        [InlineKeyboardButton("💰 Punkte einlösen", callback_data="/claim")]
    ]
    if (update.message and update.message.from_user.username in ADMIN_USERS) or \
       (update.callback_query and update.callback_query.from_user.username in ADMIN_USERS):
        keyboard.append([InlineKeyboardButton("➕ Punkte vergeben", callback_data="/addpoints")])
        keyboard.append([InlineKeyboardButton("📢 Nachricht senden", callback_data="/message")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await send_reply(update, context, "📌 **Befehlsübersicht**\n\nWähle einen Befehl aus:", reply_markup=reply_markup)

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Verarbeitet die Buttons und führt den entsprechenden Befehl aus."""
    query = update.callback_query
    await query.answer()
    command = query.data
    if command == "/start":
        await start(update, context)
    elif command == "/pointlist":
        await pointlist(update, context)
    elif command == "/claim":
        await claim(update, context)
    elif command == "/addpoints" and query.from_user.username in ADMIN_USERS:
        await query.message.reply_text("Nutze den Befehl direkt: /addpoints @username 10")
    elif command == "/message" and query.from_user.username in ADMIN_USERS:
        await query.message.reply_text("Nutze den Befehl direkt: /message Dein Text")

# Während einer aktiven Fragerunde werden keine Punkte für normale Nachrichten vergeben.
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Verarbeitet normale Nachrichten – während der Fragerunde erfolgt KEINE Punktevergabe."""
    storage = get_storage(context)
    if "active_question" in storage:
        return
    else:
        user = update.message.from_user
        points = random.choice([1, 2])
        await add_points(user.id, user.username or user.first_name, points)

async def pointlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Zeigt die aktuelle Punkteliste an."""
    user = update.message.from_user if update.message else update.callback_query.from_user
    log_action(f"👤 {user.username} hat /pointlist aufgerufen.")
    await show_ranking(context)

async def claim(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ermöglicht es Nutzern, ihre Punkte gegen $XNX einzutauschen."""
    user = update.message.from_user if update.message else update.callback_query.from_user
    keyboard = [[InlineKeyboardButton("✅ Ja, Punkte einlösen", url=f"https://xenex-ai.github.io/dev/27_tst_xnx.html?name={user.username}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    log_action(f"🔄 {user.username} möchte Punkte einlösen.")
    await send_reply(update, context, "💰 Möchtest du deine Punkte gegen $XNX eintauschen?", reply_markup=reply_markup)

async def addpoints(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ermöglicht Admins, Punkte zu vergeben."""
    user = update.message.from_user
    if user.username not in ADMIN_USERS:
        await update.message.reply_text("⛔ Keine Berechtigung!")
        return
    try:
        target_username = context.args[0].replace("@", "")
        points = int(context.args[1])
        data = load_data(POINTS_FILE)
        for user_id, info in data.items():
            if info["username"] == target_username:
                data[user_id]["points"] += points
                save_data(POINTS_FILE, data)
                log_action(f"🔹 {target_username} erhielt {points} Punkte! (Total: {data[user_id]['points']})")
                await update.message.reply_text(f"✅ {target_username} erhielt {points} Punkte!")
                return
        await update.message.reply_text("⚠️ Benutzer nicht gefunden.")
    except Exception as e:
        log_action(f"❌ Fehler beim Hinzufügen von Punkten: {e}")
        await update.message.reply_text("❌ Nutzung: /addpoints @username 10")

async def removepoints(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ermöglicht Admins, Punkte zu entziehen."""
    user = update.message.from_user
    if user.username not in ADMIN_USERS:
        await update.message.reply_text("⛔ Keine Berechtigung!")
        return
    try:
        target_username = context.args[0].replace("@", "")
        points = int(context.args[1])
        data = load_data(POINTS_FILE)
        found = False
        for user_id, info in data.items():
            if info["username"] == target_username:
                found = True
                if info["points"] >= points:
                    info["points"] -= points
                    save_data(POINTS_FILE, data)
                    log_action(f"🔹 {target_username} wurden {points} Punkte entzogen! (Total: {info['points']})")
                    await update.message.reply_text(
                        f"✅ {target_username} wurden {points} Punkte entzogen! Er/Sie hat nun {info['points']} Punkte."
                    )
                else:
                    await update.message.reply_text(f"{target_username} hat nicht genügend Punkte.")
                return
        if not found:
            await update.message.reply_text("⚠️ Benutzer nicht gefunden.")
    except Exception as e:
        log_action(f"❌ Fehler beim Entziehen von Punkten: {e}")
        await update.message.reply_text("❌ Nutzung: /removepoints @username <Punkte>")

async def message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ermöglicht Admins, eine Nachricht im Namen des Bots zu senden."""
    user = update.message.from_user
    if user.username not in ADMIN_USERS:
        await update.message.reply_text("⛔ Keine Berechtigung!")
        return
    try:
        text = " ".join(context.args)
        if not text:
            await update.message.reply_text("❌ Nutzung: /message <Text>")
            return
        log_action(f"📢 Admin {user.username} hat eine Nachricht gesendet: {text}")
        await context.bot.send_message(chat_id=GROUP_ID, text=text)
        log_action(f"📢 Admin-Nachricht gesendet: {text}")
        await update.message.reply_text("✅ Nachricht gesendet!")
    except Exception as e:
        log_action(f"❌ Fehler beim Senden der Nachricht: {e}")
        await update.message.reply_text("❌ Fehler beim Senden der Nachricht.")

# ------------------ Hauptprogramm ------------------ #
def main():
    """Startet den Telegram-Bot."""
    application = Application.builder().token(BOT_TOKEN).build()

    # Befehle registrieren
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", commands_list))
    application.add_handler(CommandHandler("pointlist", pointlist))
    application.add_handler(CommandHandler("claim", claim))
    application.add_handler(CommandHandler("addpoints", addpoints))
    application.add_handler(CommandHandler("removepoints", removepoints))
    application.add_handler(CommandHandler("message", message))

    # Interaktive Buttons verarbeiten
    application.add_handler(CallbackQueryHandler(button_click))

    # Nachrichtenverarbeitung:
    # - Normale Nachrichten: Punkte werden nur vergeben, wenn KEINE Fragerunde läuft.
    # - Aktivitäts-Tracking während der Fragerunde
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, track_user_activity))

    # Begrüßung neuer Mitglieder
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, greet_new_member))

    # Periodische Aufgaben über den JobQueue:
    job_queue = application.job_queue
    job_queue.run_repeating(show_ranking, interval=86400, first=10)       # Rangliste täglich
    job_queue.run_repeating(start_random_question, interval=10800, first=10)  # Neue Frage alle 3 Stunden (Fragerunde 1 Std)
    job_queue.run_repeating(remind_bonus_points, interval=1200, first=1200)     # Erinnerung alle 20 Minuten

    log_action("🤖 Bot gestartet!")
    application.run_polling()

if __name__ == "__main__":
    main()
