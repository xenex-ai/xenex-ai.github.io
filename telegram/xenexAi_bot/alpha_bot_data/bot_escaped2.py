# -*- coding: utf-8 -*-
import json
import os
import requests
import random
import logging
import asyncio
from datetime import datetime, timezone, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ChatMemberHandler,
    ContextTypes,
    filters
)
from telegram.helpers import escape_markdown

# ------------ APSCHEDULER NOTES unterdrücken ------------
# logging.getLogger('apscheduler').setLevel(logging.WARNING)
# // DEAKTIVIERT

# ------------------ Bot-Konfiguration ------------------ #
BOT_TOKEN = "7761649059:AAEQtfHDd1FXeE5wH3rPIyuXzBXnqB4eP94"
CHANNEL_ID = "@xentst"
GROUP_ID = "-1001734852517"
ADMIN_USERS = ["w3kmdo", "Den_XNX"]  # Nur diese Nutzer dürfen Admin-Befehle nutzen

# --------------------- JSON-Dateien -------------------- #
POINTS_FILE = "tst_point.json"          # Normale Punkteliste
EVENT_POINTS_FILE = "tst_event_point.json"  # Punkte für das Frage-Event
WALLETS_FILE = "tst_wallet.json"          # Wallets der Nutzer
QUESTIONS_FILE = "questions.json"         # Fragen für das automatische Event
ADM_ACTIVITY_FILE = "tst_activity.json"   # ADMIN-Protokoll

ACTIVITY_FILE = ADM_ACTIVITY_FILE

# Globale Variablen für Event-Zeiten
event_end_time = None      # Zeitpunkt, zu dem das aktuelle Event endet
last_event_time = None     # Zeitpunkt, an dem das letzte Event gestartet wurde
next_event_time = None     # Zeitpunkt, an dem das nächste automatische Event startet

# --------------------- Aktivitätslog -------------------- #
def ensure_activity_file():
    """Stellt sicher, dass die Datei existiert und initialisiert sie bei Bedarf."""
    if not os.path.exists(ACTIVITY_FILE):
        with open(ACTIVITY_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)  # Leere Liste als Standardwert speichern

def load_activity_data():
    """Lädt die letzten 100 Einträge aus tst_activity.json oder legt die Datei neu an."""
    ensure_activity_file()  # Stellt sicher, dass die Datei existiert
    try:
        with open(ACTIVITY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, list):
                return []
            return data[-100:]
    except (json.JSONDecodeError, FileNotFoundError):
        ensure_activity_file()
        return []

def log_activity(user, action):
    """Speichert eine Benutzeraktion in tst_activity.json."""
    ensure_activity_file()
    try:
        with open(ACTIVITY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, list):
                data = []
    except (json.JSONDecodeError, FileNotFoundError):
        data = []
    timestamp = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S")
    data.append({"time": timestamp, "user": user, "action": action})
    with open(ACTIVITY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

# ------------------ Logging einrichten ------------------ #
logging.basicConfig(level=logging.INFO, format="%(asctime)s - [%(levelname)s] %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)

# ------------ Hilfsfunktion zum Antworten ------------- #
async def send_reply(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, reply_markup=None):
    """Hilfsfunktion zum Antworten, egal ob über Message oder CallbackQuery."""
    if update.message:
        await update.message.reply_text(text, reply_markup=reply_markup)
    elif update.callback_query and update.callback_query.message:
        await update.callback_query.message.reply_text(text, reply_markup=reply_markup)

# ---------------------- EVENT-STATUS ------------------- #
event_active = False  # Gibt an, ob ein Frage-Event aktiv ist

# ---------------- JSON HILFSFUNKTIONEN ----------------- #
def load_data(file):
    """Lädt Daten aus einer JSON-Datei. Falls die Datei nicht existiert, wird ein leeres Dictionary zurückgegeben."""
    try:
        with open(file, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_data(file, data):
    """Speichert Daten in eine JSON-Datei mit schöner Formatierung."""
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

# -------------------- PUNKTE-VERGABE -------------------- #
async def add_points(user_id, username, points):
    """
    Vergibt Punkte an einen Benutzer.
    - Ist ein Event aktiv, werden die Punkte in EVENT_POINTS_FILE gespeichert.
    - Ansonsten in POINTS_FILE.
    """
    global event_active
    file = EVENT_POINTS_FILE if event_active else POINTS_FILE
    data = load_data(file)
    if str(user_id) not in data:
        data[str(user_id)] = {"username": username, "points": 0}
    data[str(user_id)]["points"] += points
    save_data(file, data)
    logging.info(f"✅ {username} hat {points} Punkte erhalten! (Total: {data[str(user_id)]['points']})")
    # Datei hochladen
    url = "https://corenetwork.io/xenexAi/connect/json.php"
    with open(POINTS_FILE, "rb") as file_obj:
        try:
            response = requests.post(url, files={"file": file_obj})
            if response.status_code == 200:
                log_activity(username, "added_points")
                logging.info("📤 Datei erfolgreich hochgeladen!")
            else:
                logging.info(f"❌ Fehler beim Hochladen: {response.status_code}")
        except Exception as e:
            logging.info(f"❌ Fehler: {str(e)}")

# ------------------ RANGLISTE ZEIGEN -------------------- #
async def show_ranking(context: ContextTypes.DEFAULT_TYPE):
    """
    Sendet stündlich die Top 10 der Rangliste in die Gruppe.
    Die Rangliste wird aus POINTS_FILE erstellt.
    """
    data = load_data(POINTS_FILE)
    if not data:
        message = "🚫 Noch keine Punkte vergeben."
    else:
        ranking = sorted(data.items(), key=lambda x: x[1]["points"], reverse=True)
        message = "🏆 **Top Punkteliste** 🏆\n\n"
        for i, (user_id, info) in enumerate(ranking[:10], 1):
            username = escape_markdown(info['username'], version=2)
            message += f"{i}. {username} - {info['points']} Punkte\n"
    logging.info("📊 Rangliste wurde gesendet.")
    await context.bot.send_message(chat_id=GROUP_ID, text=message, parse_mode=ParseMode.MARKDOWN_V2)

# ---------- ZEIT-ERINNERUNGEN WÄHREND DES EVENT --------- #
async def send_time_reminder(context: ContextTypes.DEFAULT_TYPE):
    """
    Sendet eine Erinnerung während des Events, die die noch verbleibende Zeit anzeigt
    und einen intergalaktisch motivierenden Text enthält.
    """
    data = context.job.data
    remaining = data["remaining"]
    reminder_message = data["message"]
    text = f"⏰ Noch **{remaining} Minuten** bis zum Ende des Frage-Events!\n\n✨ {reminder_message}"
    await context.bot.send_message(chat_id=GROUP_ID, text=text, parse_mode=ParseMode.MARKDOWN_V2)

def schedule_reminders(job_queue):
    """
    Plant 4 Erinnerungs-Jobs während des Events.
    Die Erinnerungen werden nach 5, 10, 20 und 25 Minuten versendet,
    was einer verbleibenden Zeit von 25, 20, 10 bzw. 5 Minuten entspricht.
    Jeder Job erhält einen zufällig (und alle unterschiedlich) ausgewählten intergalaktischen Motivationsspruch.
    """
    messages = [
        "Die Sterne beben vor Energie! 🌟",
        "Intergalaktische Kräfte sind am Werk! 🚀",
        "Das Universum feuert dich an! ✨",
        "Kosmische Energie pulsiert durch deine Adern! ⚡"
    ]
    reminders = random.sample(messages, 4)
    job_queue.run_once(send_time_reminder, when=5 * 60, data={"remaining": 25, "message": reminders[0]})
    job_queue.run_once(send_time_reminder, when=10 * 60, data={"remaining": 20, "message": reminders[1]})
    job_queue.run_once(send_time_reminder, when=20 * 60, data={"remaining": 10, "message": reminders[2]})
    job_queue.run_once(send_time_reminder, when=25 * 60, data={"remaining": 5, "message": reminders[3]})
    logging.info("⏳ Zeit-Erinnerungen wurden geplant.")

# --------------- AUTOMATISCHES FRAGE-EVENT --------------- #
async def auto_question(context: ContextTypes.DEFAULT_TYPE):
    """
    Diese Funktion wird alle 2 Stunden automatisch ausgeführt:
    - Es wird eine Frage aus QUESTIONS_FILE (als Liste) zufällig ausgewählt.
    - Die Frage wird in der Gruppe gepostet und fixiert.
    - Das Event wird automatisch gestartet (event_active = True).
    - Gleichzeitig werden Erinnerungen und ein Job zum automatischen Beenden (nach 30 Minuten) geplant.
    """
    global event_active, event_end_time, last_event_time, next_event_time
    questions = load_data(QUESTIONS_FILE).get("questions", [])
    if not questions:
        await context.bot.send_message(chat_id=GROUP_ID, text="🚫 Keine Fragen gefunden.")
        return
    question = random.choice(questions)
    question_message = await context.bot.send_message(
        chat_id=GROUP_ID,
        text=f"❓ {question}\n\n💡 Antworte aktiv – der beste Beitrag erhält Extrapunkte!"
    )
    try:
        await question_message.pin()
        logging.info("📌 Frage wurde fixiert.")
    except Exception as e:
        logging.error(f"❌ Fehler beim Fixieren der Nachricht: {e}")

    event_active = True
    last_event_time = datetime.now(timezone.utc)
    event_end_time = last_event_time + timedelta(minutes=30)
    next_event_time = last_event_time + timedelta(seconds=7200)

    await context.bot.send_message(chat_id=GROUP_ID,
                                   text="🔥 Das Frage-Event hat begonnen! Alle Antworten zählen jetzt.")
    schedule_reminders(context.job_queue)
    context.job_queue.run_once(auto_stop_event, when=30 * 60, data=question_message.message_id)

# ---------------- AUTOMATISCHES EVENT-BEENDEN ---------------- #
async def auto_stop_event(context: ContextTypes.DEFAULT_TYPE):
    """
    Beendet das automatische Frage-Event:
    - Ermittelt den Gewinner aus EVENT_POINTS_FILE und schreibt Bonuspunkte in POINTS_FILE.
    - Setzt das Event zurück (event_active = False).
    - Unfixiert die ursprüngliche Frage (über die message_id, die als Job-Daten übergeben wurde).
    """
    global event_active
    event_active = False
    event_data = load_data(EVENT_POINTS_FILE)
    if not event_data:
        await context.bot.send_message(chat_id=GROUP_ID, text="🤖 Kein Teilnehmer hat Punkte gesammelt im Event.")
    else:
        winner = max(event_data.items(), key=lambda x: x[1]["points"])
        user_id, user_info = winner
        bonus_points = random.randint(100, 250)
        main_data = load_data(POINTS_FILE)
        if user_id not in main_data:
            main_data[user_id] = {"username": user_info["username"], "points": 0}
        main_data[user_id]["points"] += bonus_points
        save_data(POINTS_FILE, main_data)
        save_data(EVENT_POINTS_FILE, {})
        winner_message = (
            f"🎉 Das Frage-Event ist vorbei! 🎉\n\n"
            f"🏆 Herzlichen Glückwunsch {escape_markdown(user_info['username'], version=2)}!\n"
            f"Du hast das Event gewonnen und erhältst {bonus_points} Bonuspunkte!"
        )
        logging.info(f"🏆 Gewinner automatisch gekürt: {user_info['username']} mit {bonus_points} Punkten.")
        await context.bot.send_message(chat_id=GROUP_ID, text=winner_message, parse_mode=ParseMode.MARKDOWN_V2)
    message_id = context.job.data
    try:
        await context.bot.unpin_chat_message(chat_id=GROUP_ID, message_id=message_id)
        logging.info("📌 Die Frage wurde entfixiert.")
    except Exception as e:
        logging.error("❌ Fehler beim Entfixieren der Nachricht: " + str(e))

# ---------------- EVENT-START (manuell durch Admin) ---------------- #
async def start_event(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Startet ein Frage-Event (manuell).
    Nur Admins (in ADMIN_USERS) dürfen diesen Befehl ausführen.
    Während des Events werden Punkte in EVENT_POINTS_FILE gespeichert.
    Zusätzlich werden die Zeit-Erinnerungen geplant.
    """
    global event_active, event_end_time, last_event_time, next_event_time
    user = update.message.from_user if update.message else update.callback_query.from_user
    if user.username not in ADMIN_USERS:
        await update.message.reply_text("🚫 Du bist nicht berechtigt, diesen Befehl auszuführen.")
        return
    event_active = True
    save_data(EVENT_POINTS_FILE, {})

    last_event_time = datetime.now(timezone.utc)
    event_end_time = last_event_time + timedelta(minutes=30)
    next_event_time = last_event_time + timedelta(seconds=7200)

    logging.info("🔥 Frage-Event wurde manuell gestartet.")
    await context.bot.send_message(chat_id=GROUP_ID,
                                   text="🚀 Das Frage-Event hat begonnen! Alle Punkte zählen nun für das Event.")
    schedule_reminders(context.job_queue)

# ---------------- EVENT-BEENDEN & GEWINNER KÜREN (manuell durch Admin) ---------------- #
async def stop_event(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Beendet das Frage-Event (manuell), kürt den Gewinner und schreibt Bonuspunkte in POINTS_FILE.
    Nur Admins dürfen diesen Befehl ausführen.
    Nach Beendigung wird EVENT_POINTS_FILE zurückgesetzt.
    """
    global event_active
    user = update.message.from_user if update.message else update.callback_query.from_user
    if user.username not in ADMIN_USERS:
        await update.message.reply_text("🚫 Du bist nicht berechtigt, diesen Befehl auszuführen.")
        return
    event_active = False
    event_data = load_data(EVENT_POINTS_FILE)
    if not event_data:
        await context.bot.send_message(chat_id=GROUP_ID, text="🚫 Kein Teilnehmer hat Punkte gesammelt.")
        return
    winner = max(event_data.items(), key=lambda x: x[1]["points"])
    user_id, user_info = winner
    bonus_points = random.randint(100, 250)
    main_data = load_data(POINTS_FILE)
    if user_id not in main_data:
        main_data[user_id] = {"username": user_info["username"], "points": 0}
    main_data[user_id]["points"] += bonus_points
    save_data(POINTS_FILE, main_data)
    save_data(EVENT_POINTS_FILE, {})
    winner_message = (
        f"🎊 **Das Frage-Event ist vorbei!** 🎊\n\n"
        f"🏆 **Herzlichen Glückwunsch {escape_markdown(user_info['username'], version=2)}!**\n"
        f"Du hast das Event gewonnen und erhältst **{bonus_points} Bonuspunkte**!"
    )
    logging.info(f"🏆 Gewinner manuell gekürt: {user_info['username']} mit {bonus_points} Punkten.")
    await context.bot.send_message(chat_id=GROUP_ID, text=winner_message, parse_mode=ParseMode.MARKDOWN_V2)
    await context.bot.unpin_chat_message(chat_id=GROUP_ID, message_id=context.job.data)
    logging.info("📌 Die Frage wurde entfixiert.")

# ---------------- NEUE MITGLIEDER BEGRÜSSEN ---------------- #
async def welcome_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Begrüßt neue Mitglieder in der Gruppe und vergibt automatisch 3 Willkommenspunkte.
    """
    for member in update.message.new_chat_members:
        name = member.username if member.username else member.first_name
        username = f"@{name}"
        await add_points(member.id, username, 3)
        message = f"👋 Willkommen {username} in der Xenex AI Community! 🚀"
        await update.message.reply_text(message)

# ---------------- STANDARD BOT-BEFEHLE ---------------- #
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Standard /start-Befehl, der den Bot vorstellt.
    """
    await update.message.reply_text(
        "🤖 Willkommen beim Xenex AI Community Bot! Nutze /points, um deine Punkte zu sehen.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Verarbeitet normale Nachrichten und vergibt Punkte:
    - 1 Punkt für eine normale Nachricht
    - 2 Punkte, wenn die Nachricht eine Antwort ist
    """
    user = update.message.from_user if update.message else update.callback_query.from_user
    points_val = 2 if update.message.reply_to_message else 1
    username = escape_markdown(user.username or user.first_name, version=2)
    await add_points(user.id, username, points_val)

async def points(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Zeigt dem Nutzer seine aktuellen Punkte aus POINTS_FILE an.
    """
    user = update.message.from_user if update.message else update.callback_query.from_user
    data = load_data(POINTS_FILE)
    user_points = data.get(str(user.id), {}).get("points", 0)
    username = escape_markdown(user.username or user.first_name, version=2)
    message = f"💡 **{username}**, du hast **{user_points} Punkte**! 💎"
    if update.message:
        await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN_V2)
    elif update.callback_query:
        await update.callback_query.message.edit_text(message, parse_mode=ParseMode.MARKDOWN_V2)

async def claim(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Zeigt dem Nutzer eine Option, Punkte einzulösen, mit einem Inline-Button.
    """
    user = update.message.from_user if update.message else update.callback_query.from_user
    data = load_data(POINTS_FILE)
    user_points = data.get(str(user.id), {}).get("points", 0)
    keyboard = [[InlineKeyboardButton("✅ Ja, Punkte einlösen",
                                      url=f"https://xenex-ai.github.io/dev/29_tst_xnx.html?name={user.username}&address={user_points}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    message = f"💰 Möchtest du deine Punkte gegen $XNX eintauschen? Du hast **{user_points} Punkte**!"
    if update.message:
        await update.message.reply_text(message, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN_V2)
    elif update.callback_query:
        await update.callback_query.message.reply_text(message, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN_V2)

async def bot_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lässt Admins eine Nachricht im Namen des Bots senden."""
    user = update.message.from_user if update.message else update.callback_query.from_user
    if user.username not in ADMIN_USERS:
        await update.message.reply_text("🚫 Keine Berechtigung!")
        return
    try:
        text = " ".join(context.args)
        if not text:
            await update.message.reply_text("❌ Nutzung: /botsend <Text>")
            return
        logging.info(f"📝 Admin {user.username} hat eine Nachricht gesendet: {text}")
        await context.bot.send_message(chat_id=GROUP_ID, text=text)
        logging.info(f"✅ Admin-Nachricht gesendet: {text}")
        await update.message.reply_text("✅ Nachricht gesendet!")
    except Exception as e:
        logging.info(f"❌ Fehler beim Senden der Nachricht: {e}")
        await update.message.reply_text("❌ Fehler beim Senden der Nachricht.")

# -------------- KOMMANDOLISTE MIT BUTTONS ------------- #
async def commands_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Zeigt alle Befehle mit klickbaren Buttons an."""
    keyboard = [
        [InlineKeyboardButton("🏁 Start", callback_data="/start")],
        [InlineKeyboardButton("📊 Punkteliste", callback_data="/points")],
        [InlineKeyboardButton("💰 Punkte einlösen", callback_data="/claim")],
        [InlineKeyboardButton("🏁 Event status", callback_data="/event")]
    ]
    user = update.message.from_user if update.message else update.callback_query.from_user
    if user.username in ADMIN_USERS:
        keyboard.append([InlineKeyboardButton("➕ Fragenevent starten", callback_data="/start_event")])
        keyboard.append([InlineKeyboardButton("❌ Fragenevent stoppen", callback_data="/stop_event")])
        keyboard.append([InlineKeyboardButton("📢 Nachricht senden", callback_data="/botsend")])
        keyboard.append([InlineKeyboardButton("📝 Admin Protocol", callback_data="/protocol")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.message:
        await update.message.reply_text("📌 **Befehlsübersicht**\n\nWähle einen Befehl aus:", reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN_V2)
    elif update.callback_query:
        await update.callback_query.message.edit_text("📌 **Befehlsübersicht**\n\nWähle einen Befehl aus:", reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN_V2)

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reagiert auf Buttons und führt den entsprechenden Befehl aus."""
    query = update.callback_query
    await query.answer()
    command = query.data
    user = query.from_user
    # Befehle für alle Benutzer
    if command == "/start":
        await start(update, context)
    elif command == "/points":
        await points(update, context)
    elif command == "/claim":
        await claim(update, context)
    elif command == "/event":
        await event_status(update, context)
    # Bestätigung für Admin-Befehle
    elif user.username in ADMIN_USERS:
        if command == "/start_event":
            keyboard = [[InlineKeyboardButton("✅ Ja, jetzt ausführen", callback_data="/confirm_start_event")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.reply_text("⚠️ Möchtest du wirklich das Fragenevent starten?", reply_markup=reply_markup)
        elif command == "/stop_event":
            keyboard = [[InlineKeyboardButton("✅ Ja, jetzt ausführen", callback_data="/confirm_stop_event")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.reply_text("⚠️ Möchtest du wirklich das Fragenevent stoppen?", reply_markup=reply_markup)
        elif command == "/botsend":
            await query.message.reply_text("👽 Nachricht im Namen des Bot senden.\n\nℹ️ Nutzung: '/botsend <message>'")
        elif command == "/protocol":
            keyboard = [[InlineKeyboardButton("✅ Ja, jetzt ausführen", callback_data="/confirm_protocol")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.reply_text("⚠️ Möchtest du wirklich das Admin Protocol anzeigen?", reply_markup=reply_markup)
        # Bestätigungs-Callbacks:
        elif command == "/confirm_start_event":
            await start_event(update, context)
        elif command == "/confirm_stop_event":
            await stop_event(update, context)
        elif command == "/confirm_botsend":
            await bot_send(update, context)
        elif command == "/confirm_protocol":
            await adm_protocol(update, context)

# ---------------- Admin Protocol ---------------- #
async def adm_protocol(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Zeigt die letzten 100 Einträge aus tst_activity.json für Admins an."""
    user = update.message.from_user if update.message else update.callback_query.from_user
    if user.username not in ADMIN_USERS:
        if update.message:
            await update.message.reply_text("🚫 Du bist nicht berechtigt, diesen Befehl zu nutzen.")
        elif update.callback_query:
            await update.callback_query.message.reply_text("🚫 Du bist nicht berechtigt, diesen Befehl zu nutzen.")
        return
    activities = load_activity_data()
    if not activities:
        if update.message:
            await update.message.reply_text("📄 Keine Aktivitätsdaten gefunden.")
        elif update.callback_query:
            await update.callback_query.message.reply_text("📄 Keine Aktivitätsdaten gefunden.")
        return
    message = "📜 **Letzte 100 Aktivitäten:**\n\n"
    for entry in activities[-10:]:
        time_str = entry.get("time", "Unbekannt")
        message += f"⏰ [{time_str}] {entry.get('user')} - {entry.get('action')}\n"
    if len(message) > 4000:
        message_chunks = [message[i:i + 4000] for i in range(0, len(message), 4000)]
        for chunk in message_chunks:
            if update.message:
                await update.message.reply_text(chunk, parse_mode=ParseMode.MARKDOWN_V2)
            elif update.callback_query:
                await update.callback_query.message.reply_text(chunk, parse_mode=ParseMode.MARKDOWN_V2)
    else:
        if update.message:
            await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN_V2)
        elif update.callback_query:
            await update.callback_query.message.reply_text(message, parse_mode=ParseMode.MARKDOWN_V2)

# ---------------- Event Status ---------------- #
async def event_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Zeigt den Status des Frage-Events an.
    - Wenn ein Event aktiv ist: verbleibende Zeit und Event-Top-User (aus EVENT_POINTS_FILE).
    - Wenn kein Event aktiv ist: Zeitpunkt der nächsten Runde und allgemeine Top-User (aus POINTS_FILE).
    """
    global event_active, event_end_time, next_event_time
    now = datetime.now(timezone.utc)
    if event_active and event_end_time:
        remaining_seconds = int((event_end_time - now).total_seconds())
        if remaining_seconds < 0:
            remaining_seconds = 0
        minutes, seconds = divmod(remaining_seconds, 60)
        status_message = f"🚀 **Aktuelles Frage-Event aktiv!**\n\n⏰ Verbleibende Zeit: **{minutes} Minuten {seconds} Sekunden**\n\n"
        event_data = load_data(EVENT_POINTS_FILE)
        if event_data:
            ranking = sorted(event_data.items(), key=lambda x: x[1]["points"], reverse=True)
            status_message += "🏆 **Top-User im Event:**\n"
            for i, (user_id, info) in enumerate(ranking[:3], 1):
                username = escape_markdown(info['username'], version=2)
                status_message += f"{i}. {username} - {info['points']} Punkte\n"
        else:
            status_message += "ℹ️ Bisher keine Punkte im Event gesammelt."
    else:
        if next_event_time:
            if next_event_time < now:
                next_event_time = now + timedelta(seconds=7200)
            next_str = next_event_time.astimezone().strftime("%Y-%m-%d %H:%M:%S")
        else:
            next_str = "Unbekannt"
        status_message = f"🛑 **Kein aktives Frage-Event.**\n\n📅 Nächste Fragerunde startet am: **{next_str}**\n\n"
        data = load_data(POINTS_FILE)
        if data:
            ranking = sorted(data.items(), key=lambda x: x[1]["points"], reverse=True)
            status_message += "🏆 **Top-User insgesamt:**\n"
            for i, (user_id, info) in enumerate(ranking[:3], 1):
                username = escape_markdown(info['username'], version=2)
                status_message += f"{i}. {username} - {info['points']} Punkte\n"
        else:
            status_message += "ℹ️ Es wurden noch keine Punkte vergeben."
    # Escape reservierte Zeichen (Bindestriche, Ausrufezeichen, Punkte)
    status_message = status_message.replace("-", r"\-").replace("!", r"\!").replace(".", r"\.")
    if update.message:
        await update.message.reply_text(status_message, parse_mode=ParseMode.MARKDOWN_V2)
    elif update.callback_query:
        await update.callback_query.message.edit_text(status_message, parse_mode=ParseMode.MARKDOWN_V2)

# -------------- Hauptprogramm / BOT start -------------- #
def main():
    """
    Initialisiert den Telegram-Bot, registriert alle Befehle und startet den Polling-Prozess.
    Zusätzlich werden:
      - Die stündliche Ranglistenanzeige geplant.
      - Das automatische Frage-Event alle 2 Stunden eingeplant.
    """
    app = Application.builder().token(BOT_TOKEN).build()

    # Befehle registrieren
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("com", commands_list))
    app.add_handler(CommandHandler("points", points))
    app.add_handler(CommandHandler("event", event_status))
    app.add_handler(CommandHandler("claim", claim))
    app.add_handler(CommandHandler("start_event", start_event))
    app.add_handler(CommandHandler("stop_event", stop_event))
    app.add_handler(CommandHandler("botsend", bot_send))
    app.add_handler(CommandHandler("protocol", adm_protocol))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_new_member))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(button_click))

    # Job Queue: Rangliste und automatisches Event
    app.job_queue.run_repeating(show_ranking, interval=3600, first=10)
    app.job_queue.run_repeating(auto_question, interval=7200, first=10)

    logging.info("🤖 Bot läuft [erfolgreich]")
    app.run_polling()

if __name__ == "__main__":
    main()
