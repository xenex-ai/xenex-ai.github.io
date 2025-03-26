import json
import os
import requests
import random
import logging
import asyncio
import time
import matplotlib.pyplot as plt
import matplotlib as mpl
from datetime import datetime, timezone
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ChatMemberHandler,
    ContextTypes,
    filters,
)

# ------------ APSCHEDULER NOTES unterdrücken ------------
# logging.getLogger('apscheduler').setLevel(logging.WARNING)
# // DEAKTIVIERT

# ------------------ Bot-Konfiguration ------------------ #
BOT_TOKEN = "7761649059:AAEQtfHDd1FXeE5wH3rPIyuXzBXnqB4eP94"
CHANNEL_ID = "@xentst"
GROUP_ID = "-1001734852517"
ADMIN_USERS = ["w3kmdo", "Den_XNX"]  # Nur diese Nutzer dürfen Admin-Befehle nutzen

# --------------------- JSON-Dateien -------------------- #
POINTS_FILE = "tst_point.json"             # Normale Punkteliste
EVENT_POINTS_FILE = "tst_event_point.json"   # Punkte für das Frage-Event
WALLETS_FILE = "tst_wallet.json"             # Wallets der Nutzer
QUESTIONS_FILE = "questions.json"            # Fragen für das automatische Event
ADM_ACTIVITY_FILE = "tst_activity.json"      # ADMIN-Protokoll

ACTIVITY_FILE = ADM_ACTIVITY_FILE

# ---------------- Hilfsfunktionen für Aktivitätsprotokoll ---------------- #
def ensure_activity_file():
    """Stellt sicher, dass die Aktivitätsdatei existiert."""
    if not os.path.exists(ACTIVITY_FILE):
        with open(ACTIVITY_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)

def load_activity_data():
    """Lädt die letzten 100 Einträge aus dem Aktivitätsprotokoll."""
    ensure_activity_file()
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
    """Speichert eine Aktion eines Nutzers im Aktivitätsprotokoll."""
    ensure_activity_file()
    try:
        with open(ACTIVITY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, list):
                data = []
    except (json.JSONDecodeError, FileNotFoundError):
        data = []
    data.append({
        "user": user,
        "action": action,
        "time": datetime.now(timezone.utc).isoformat()
    })
    with open(ACTIVITY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

# ------------------ Logging einrichten ------------------ #
logging.basicConfig(level=logging.INFO, format="%(asctime)s - [%(levelname)s] %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)

# ------------ Hilfsfunktion zum Antworten ------------- #
async def send_reply(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, reply_markup=None):
    """Antwortet, egal ob als Nachricht oder CallbackQuery."""
    if update.message:
        await update.message.reply_text(text, reply_markup=reply_markup)
    elif update.callback_query and update.callback_query.message:
        await update.callback_query.message.reply_text(text, reply_markup=reply_markup)

# ---------------------- EVENT-STATUS ------------------- #
event_active = False  # Gibt an, ob ein Frage-Event aktiv ist

# ---------------- JSON HILFSFUNKTIONEN ----------------- #
def load_data(file):
    """Lädt Daten aus einer JSON-Datei oder gibt ein leeres Dict zurück."""
    try:
        with open(file, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_data(file, data):
    """Speichert Daten in einer JSON-Datei mit schöner Formatierung."""
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

# -------------------- PUNKTE-VERGABE -------------------- #
async def add_points(user_id, username, points):
    """
    Vergibt Punkte an einen Nutzer.
    Bei aktiven Events werden die Punkte im EVENT_POINTS_FILE gespeichert, sonst im POINTS_FILE.
    """
    global event_active
    file = EVENT_POINTS_FILE if event_active else POINTS_FILE
    data = load_data(file)
    if str(user_id) not in data:
        data[str(user_id)] = {"username": username, "points": 0}
    data[str(user_id)]["points"] += points
    save_data(file, data)
    logging.info(f"✨ {username} erhält {points} Punkte! (Gesamt: {data[str(user_id)]['points']})")
    # Optionaler Datei-Upload (zur Synchronisation)
    url = "https://corenetwork.io/xenexAi/connect/json.php"
    with open(POINTS_FILE, "rb") as file_obj:
        try:
            response = requests.post(url, files={"file": file_obj})
            if response.status_code == 200:
                log_activity(username, "checked_points")
                logging.info("📤 Datei erfolgreich hochgeladen!")
            else:
                logging.info(f"⚠️ Fehler beim Hochladen: {response.status_code}")
        except Exception as e:
            logging.info(f"❌ Fehler: {str(e)}")

# ------------------ RANGLISTE ZEIGEN -------------------- #
async def show_ranking(context: ContextTypes.DEFAULT_TYPE):
    """
    Sendet stündlich die Top 10 Rangliste in die Gruppe.
    """
    data = load_data(POINTS_FILE)
    if not data:
        message = "Noch keine Punkte vergeben. 😢"
    else:
        ranking = sorted(data.items(), key=lambda x: x[1]["points"], reverse=True)
        message = "🌟 **Top Punkteliste** 🌟\n\n"
        for i, (user_id, info) in enumerate(ranking[:10], 1):
            message += f"{i}. {info['username']} – {info['points']} Punkte\n"
    logging.info("Rangliste gesendet.")
    await context.bot.send_message(chat_id=GROUP_ID, text=message)

# ---------- ZEIT-ERINNERUNGEN WÄHREND DES EVENT --------- #
async def send_time_reminder(context: ContextTypes.DEFAULT_TYPE):
    """Sendet intergalaktische Erinnerungen während eines Events."""
    data = context.job.data
    remaining = data["remaining"]
    reminder_message = data["message"]
    text = f"⏰ Noch **{remaining} Minuten** bis zum Ende des Frage-Events!\n\n{reminder_message}"
    await context.bot.send_message(chat_id=GROUP_ID, text=text)

def schedule_reminders(job_queue):
    """Plant 4 Erinnerungen mit zufällig ausgewählten, motivierenden Sprüchen."""
    messages = [
        "Die Sterne beben vor Energie! ✨",
        "Intergalaktische Kräfte sind am Werk! 🚀",
        "Das Universum feuert dich an! 🌌",
        "Kosmische Energie pulsiert durch deine Adern! 💫"
    ]
    reminders = random.sample(messages, 4)
    job_queue.run_once(send_time_reminder, when=5 * 60, data={"remaining": 25, "message": reminders[0]})
    job_queue.run_once(send_time_reminder, when=10 * 60, data={"remaining": 20, "message": reminders[1]})
    job_queue.run_once(send_time_reminder, when=20 * 60, data={"remaining": 10, "message": reminders[2]})
    job_queue.run_once(send_time_reminder, when=25 * 60, data={"remaining": 5, "message": reminders[3]})
    logging.info("⏰ Zeit-Erinnerungen geplant.")

# --------------- AUTOMATISCHES FRAGE-EVENT --------------- #
async def auto_question(context: ContextTypes.DEFAULT_TYPE):
    """Startet automatisch ein Frage-Event mit einer zufälligen Frage."""
    global event_active
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
        logging.info("📌 Frage fixiert.")
    except Exception as e:
        logging.error(f"Fehler beim Fixieren: {e}")
    event_active = True
    await context.bot.send_message(chat_id=GROUP_ID, text="❓ Das Frage-Event hat begonnen! Alle Antworten zählen jetzt.")
    schedule_reminders(context.job_queue)
    context.job_queue.run_once(auto_stop_event, when=30 * 60, data=question_message.message_id)

async def auto_stop_event(context: ContextTypes.DEFAULT_TYPE):
    """
    Beendet das automatische Frage-Event, kürt den Gewinner und vergibt Bonuspunkte.
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
            f"📢 Das Frage-Event ist vorbei! 🎉\n\n"
            f"🏆 Glückwunsch {user_info['username']} – du erhältst {bonus_points} Bonuspunkte!"
        )
        logging.info(f"Gewinner: {user_info['username']} ({bonus_points} Punkte)")
        await context.bot.send_message(chat_id=GROUP_ID, text=winner_message)
    message_id = context.job.data
    try:
        await context.bot.unpin_chat_message(chat_id=GROUP_ID, message_id=message_id)
        logging.info("📌 Frage entfixiert.")
    except Exception as e:
        logging.error(f"Fehler beim Entfixieren: {e}")

# ### EVENT-START (Admin) ###
async def start_event(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Startet manuell ein Frage-Event (nur Admins)."""
    global event_active
    user = update.message.from_user
    if user.username not in ADMIN_USERS:
        await update.message.reply_text("⛔ Keine Berechtigung!")
        return
    event_active = True
    save_data(EVENT_POINTS_FILE, {})
    logging.info("🚀 Manuelles Frage-Event gestartet.")
    await context.bot.send_message(chat_id=GROUP_ID, text="🚀 Das Frage-Event hat begonnen!")
    schedule_reminders(context.job_queue)

# ### EVENT-ENDE (Admin) ###
async def stop_event(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Beendet manuell ein Frage-Event (nur Admins) und kürt den Gewinner."""
    global event_active
    user = update.message.from_user
    if user.username not in ADMIN_USERS:
        await update.message.reply_text("⛔ Keine Berechtigung!")
        return
    event_active = False
    event_data = load_data(EVENT_POINTS_FILE)
    if not event_data:
        await context.bot.send_message(chat_id=GROUP_ID, text="Keine Teilnehmer im Event.")
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
        f"🎉 **Das Frage-Event ist vorbei!**\n\n"
        f"🏆 **Glückwunsch {user_info['username']}!**\n"
        f"Du erhältst {bonus_points} Bonuspunkte!"
    )
    logging.info(f"Manueller Gewinner: {user_info['username']} ({bonus_points} Punkte)")
    await context.bot.send_message(chat_id=GROUP_ID, text=winner_message)

# ### NEUE MITGLIEDER BEGRÜSSEN ###
async def welcome_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Begrüßt neue Mitglieder und vergibt 3 Willkommenspunkte."""
    for member in update.message.new_chat_members:
        username = f"@{member.username}" if member.username else member.first_name
        await add_points(member.id, username, 3)
        message = f"👋 Willkommen {username} in der Xenex AI Community!"
        await update.message.reply_text(message)

# ### STANDARD BOT-BEFEHLE ###
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Standard /start-Befehl."""
    await update.message.reply_text("Willkommen beim Xenex AI Community Bot! Nutze /points, um deine Punkte zu sehen. 🚀")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Vergibt Punkte für Nachrichten:
      - 1 Punkt für eine normale Nachricht
      - 2 Punkte für Antworten.
    """
    user = update.message.from_user
    points_val = 2 if update.message.reply_to_message else 1
    await add_points(user.id, user.username or user.first_name, points_val)

async def points(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Zeigt die aktuellen Punkte des Nutzers an."""
    user = update.message.from_user
    data = load_data(POINTS_FILE)
    user_points = data.get(str(user.id), {}).get("points", 0)
    await update.message.reply_text(f"⭐ {user.username or user.first_name}, du hast {user_points} Punkte!")

async def claim(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bietet eine Option, Punkte einzulösen (Inline-Button)."""
    user = update.message.from_user
    data = load_data(POINTS_FILE)
    user_points = data.get(str(user.id), {}).get("points", 0)
    keyboard = [[InlineKeyboardButton("Ja, Punkte einlösen 💰",
                                      url=f"https://xenex-ai.github.io/dev/27_tst_xnx.html?name={user.username}&address={user_points}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(f"Möchtest du deine {user_points} Punkte gegen $XNX eintauschen?", reply_markup=reply_markup)

async def bot_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ermöglicht Admins, eine Nachricht im Namen des Bots zu senden."""
    user = update.message.from_user
    if user.username not in ADMIN_USERS:
        await update.message.reply_text("⛔ Keine Berechtigung!")
        return
    try:
        text = " ".join(context.args)
        if not text:
            await update.message.reply_text("Nutzung: /botsend <Text>")
            return
        logging.info(f"Admin {user.username} sendet: {text}")
        await context.bot.send_message(chat_id=GROUP_ID, text=text)
        await update.message.reply_text("✅ Nachricht gesendet!")
    except Exception as e:
        logging.info(f"Fehler: {e}")
        await update.message.reply_text("❌ Fehler beim Senden der Nachricht.")

# -------------- KOMMANDOLISTE MIT BUTTONS ------------- #
async def commands_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Zeigt eine interaktive Übersicht aller Befehle."""
    # Ermitteln des Nutzers über effective_user
    user = update.effective_user
    keyboard = [
        [InlineKeyboardButton("🏁 Start", callback_data="/start")],
        [InlineKeyboardButton("📊 Punkteliste", callback_data="/points")],
        [InlineKeyboardButton("💰 Punkte einlösen", callback_data="/claim")]
    ]
    if user and user.username in ADMIN_USERS:
        keyboard.append([InlineKeyboardButton("➕ Fragenevent starten", callback_data="/start_event")])
        keyboard.append([InlineKeyboardButton("❌ Fragenevent stoppen", callback_data="/stop_event")])
        keyboard.append([InlineKeyboardButton("📢 Nachricht senden", callback_data="/botsend")])
        keyboard.append([InlineKeyboardButton("👋 Admin Protocol", callback_data="/protocol")])
    # Extravagante Features
    keyboard.append([InlineKeyboardButton("📈 Ranglisten-Chart", callback_data="/ranking_chart")])
    keyboard.append([InlineKeyboardButton("🎰 Galactic Lottery", callback_data="/lottery")])
    keyboard.append([InlineKeyboardButton("🚀 Adventure", callback_data="/adventure")])
    keyboard.append([InlineKeyboardButton("💎 Schatzsuche", callback_data="/treasure")])
    keyboard.append([InlineKeyboardButton("⚔️ Galactic Battle", callback_data="/battle")])
    keyboard.append([InlineKeyboardButton("🛠️ Galactic Upgrade", callback_data="/upgrade")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.message:
        await update.message.reply_text("✨ **Befehlsübersicht** ✨\n\nWähle einen Befehl aus:", reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.message.edit_text("✨ **Befehlsübersicht** ✨\n\nWähle einen Befehl aus:", reply_markup=reply_markup)

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Verarbeitet Button-Klicks und ruft den entsprechenden Befehl auf."""
    query = update.callback_query
    await query.answer()
    command = query.data
    if command == "/start":
        await start(update, context)
    elif command == "/points":
        await points(update, context)
    elif command == "/claim":
        await claim(update, context)
    elif command == "/ranking_chart":
        await ranking_chart(update, context)
    elif command == "/lottery":
        await lottery(update, context)
    elif command == "/adventure":
        await adventure(update, context)
    elif command == "/treasure":
        await treasure(update, context)
    elif command == "/battle":
        await battle(update, context)
    elif command == "/upgrade":
        await upgrade(update, context)
    else:
        # Falls ein Admin-Befehl via Button ausgewählt wurde:
        user = update.effective_user
        if user and user.username in ADMIN_USERS:
            if command == "/start_event":
                await query.message.reply_text("Bitte nutze den Befehl direkt: /start_event")
            elif command == "/stop_event":
                await query.message.reply_text("Bitte nutze den Befehl direkt: /stop_event")
            elif command == "/botsend":
                await query.message.reply_text("Bitte nutze: /botsend <message>")
            elif command == "/protocol":
                await query.message.reply_text("Bitte nutze: /protocol")
        else:
            await query.message.reply_text("Unbekannter Befehl.")

async def adm_protocol(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Zeigt das Admin-Protokoll in geordneter Form an."""
    user = update.message.from_user
    if user.username not in ADMIN_USERS:
        await update.message.reply_text("⛔ Keine Berechtigung!")
        return
    activities = load_activity_data()
    if not activities:
        await update.message.reply_text("📄 Es wurden keine Aktivitäten gefunden.")
        return
    # Formatierung: Nummerierte Liste
    lines = ["📜 **Letzte 100 Aktivitäten:**"]
    for i, entry in enumerate(activities[-10:], start=1):
        lines.append(f"{i}. {entry['time']} – {entry['user']}: {entry['action']}")
    message = "\n".join(lines)
    await update.message.reply_text(message, parse_mode="Markdown")

# ----------------- RANGLISTEN-CHART ----------------- #
def load_points():
    """Lädt Punkte aus der JSON-Datei."""
    if not os.path.exists(POINTS_FILE):
        return {}
    with open(POINTS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def generate_ranking_chart():
    """
    Erstellt ein Balkendiagramm der Top 10 Rangliste im galaktischen Stil.
    """
    points_data = load_points()
    if not points_data:
        return None
    sorted_items = sorted(points_data.items(), key=lambda x: x[1]["points"], reverse=True)[:10]
    usernames = [item[1]["username"] for item in sorted_items]
    scores = [item[1]["points"] for item in sorted_items]
    mpl.style.use("dark_background")
    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.barh(usernames[::-1], scores[::-1], color="#00FFFF", edgecolor="#0000FF")
    ax.set_xlabel("Punkte", fontsize=14, color="white")
    ax.set_ylabel("Spieler", fontsize=14, color="white")
    ax.set_title("🌌 Galaktische Top 10 Rangliste", fontsize=18, color="white", pad=15)
    ax.grid(axis="x", linestyle="--", alpha=0.7)
    for bar in bars:
        width = bar.get_width()
        ax.text(width + 1, bar.get_y() + bar.get_height()/2,
                f"{int(width)}", va="center", color="white", fontsize=12)
    image_path = "ranking_chart.png"
    plt.tight_layout()
    plt.savefig(image_path, dpi=150)
    plt.close()
    return image_path

async def ranking_chart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sendet das generierte Ranglisten-Diagramm."""
    image_path = generate_ranking_chart()
    if image_path:
        await context.bot.send_photo(chat_id=update.effective_chat.id, photo=open(image_path, "rb"))
    else:
        await update.message.reply_text("Keine Punkte vorhanden, um ein Diagramm zu erstellen.")

# ----------------- DAILY BONUS (Special) ----------------- #
DAILY_BONUS_FILE = "daily_bonus.json"

def load_daily_bonus():
    try:
        with open(DAILY_BONUS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_daily_bonus(data):
    with open(DAILY_BONUS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

async def daily_bonus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gibt einmal täglich einen Zufallsbonus."""
    user = update.message.from_user
    daily_data = load_daily_bonus()
    user_id = str(user.id)
    current_time = time.time()
    last_claim = daily_data.get(user_id, 0)
    if current_time - last_claim < 86400:
        await update.message.reply_text("Du hast deinen täglichen Bonus bereits erhalten! 🌙")
        return
    bonus = random.randint(50, 200)
    await add_points(user.id, user.username or user.first_name, bonus)
    daily_data[user_id] = current_time
    save_daily_bonus(daily_data)
    await update.message.reply_text(f"🌟 Glückwunsch {user.username or user.first_name}! Du erhältst {bonus} Bonuspunkte!")

# ----------------- GALACTIC LOTTERY (Special) ----------------- #
async def lottery(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Nimm an der Galactic Lottery teil!
    Einsatz: 50 Punkte.
      - 50%: Gewinn zwischen 100 und 300 Punkten
      - 30%: 0 Punkte Gewinn
      - 20%: Verlust von 50 Punkten
    """
    user = update.message.from_user
    data = load_data(POINTS_FILE)
    user_id = str(user.id)
    current_points = data.get(user_id, {}).get("points", 0)
    if current_points < 50:
        await update.message.reply_text("Du benötigst mindestens 50 Punkte, um an der Galactic Lottery teilzunehmen!")
        return
    await add_points(user.id, user.username or user.first_name, -50)
    outcome = random.choices(["win", "nothing", "lose"], weights=[50, 30, 20], k=1)[0]
    if outcome == "win":
        win_points = random.randint(100, 300)
        await add_points(user.id, user.username or user.first_name, win_points)
        message = f"🎉 Glückwunsch {user.username or user.first_name}! Du gewinnst {win_points} Punkte!"
    elif outcome == "nothing":
        message = f"😕 Schade, {user.username or user.first_name} – diesmal kein Gewinn."
    else:
        message = f"💥 Oh nein, {user.username or user.first_name}! Du verlierst 50 Punkte."
    await update.message.reply_text(message)

# ----------------- ADVENTURE (Special) ----------------- #
adventure_steps = {
    "start": {
        "text": "Du stehst an einem galaktischen Scheideweg. Betrittst du den Pfad der Sterne ✨ oder tauchst du in die dunkle Leere der Galaxie ein? 🌌",
        "options": [
            {"text": "Pfad der Sterne", "next": "stars"},
            {"text": "Dunkle Leere", "next": "dark"}
        ]
    },
    "stars": {
        "text": "Die Sterne leuchten! Du erhältst 100 Bonuspunkte. Weiter zum kosmischen Ozean 🌊 oder verweilst du auf dem Sternenplateau? 🏞️",
        "options": [
            {"text": "Kosmischen Ozean", "next": "ocean"},
            {"text": "Sternenplateau", "next": "plateau"}
        ],
        "bonus": 100
    },
    "dark": {
        "text": "Die Dunkelheit fordert dich – du verlierst 50 Punkte. Willst du den Lichtstrahl suchen oder weiter in der Dunkelheit wandeln? 🔦",
        "options": [
            {"text": "Lichtstrahl", "next": "light"},
            {"text": "Weiterwandeln", "next": "deeper"}
        ],
        "penalty": 50
    },
    "ocean": {
        "text": "Der kosmische Ozean offenbart ein Portal! Du erhältst 150 Bonuspunkte und kehrst als Held zurück. 🏆",
        "options": [],
        "bonus": 150,
        "end": True
    },
    "plateau": {
        "text": "Auf dem Sternenplateau ruhst du aus – keine zusätzlichen Punkte, aber du fühlst dich erfrischt. 🌠",
        "options": [],
        "end": True
    },
    "light": {
        "text": "Der Lichtstrahl führt dich in Sicherheit. Du gewinnst 50 Punkte und findest deinen Weg zurück. 🔆",
        "options": [],
        "bonus": 50,
        "end": True
    },
    "deeper": {
        "text": "Du verirrst dich in der Dunkelheit und verlierst weitere 50 Punkte. Doch am Ende findest du einen rettenden Lichtblick. 💡",
        "options": [],
        "penalty": 50,
        "end": True
    }
}

async def adventure(update: Update, context: ContextTypes.DEFAULT_TYPE, step="start"):
    """
    Führt dich durch ein interaktives galaktisches Abenteuer mit Bonus- oder Maluspunkten.
    """
    user = update.message.from_user if update.message else update.callback_query.from_user
    current_step = adventure_steps.get(step)
    if not current_step:
        await update.message.reply_text("Abenteuerfehler!")
        return
    text = current_step["text"]
    if "bonus" in current_step:
        await add_points(user.id, user.username or user.first_name, current_step["bonus"])
        text += f"\n\n(+{current_step['bonus']} Punkte)"
    if "penalty" in current_step:
        await add_points(user.id, user.username or user.first_name, -current_step["penalty"])
        text += f"\n\n(-{current_step['penalty']} Punkte)"
    if current_step.get("end", False) or not current_step.get("options"):
        keyboard = [[InlineKeyboardButton("Neustart 🔄", callback_data="/adventure_restart")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        if update.message:
            await update.message.reply_text(text, reply_markup=reply_markup)
        elif update.callback_query:
            await update.callback_query.message.edit_text(text, reply_markup=reply_markup)
        return
    keyboard = []
    for option in current_step["options"]:
        keyboard.append([InlineKeyboardButton(option["text"], callback_data=f"/adventure_{option['next']}")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.message:
        await update.message.reply_text(text, reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.message.edit_text(text, reply_markup=reply_markup)

async def adventure_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data  # z.B. "/adventure_stars"
    if data == "/adventure_restart":
        await adventure(update, context, step="start")
    else:
        next_step = data.split("_", 1)[1]
        await adventure(update, context, step=next_step)

# ----------------- GALACTIC TREASURE (Special) ----------------- #
async def treasure(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Startet die intergalaktische Schatzsuche.
    Klicke auf "Schatz suchen" und starte dein Abenteuer!
    """
    keyboard = [[InlineKeyboardButton("Schatz suchen 🔍", callback_data="/treasure_search")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("💎 Willkommen zur intergalaktischen Schatzsuche! Klicke auf 'Schatz suchen' und starte dein Abenteuer!", reply_markup=reply_markup)

async def treasure_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    outcome = random.choices(["treasure", "nothing", "trap"], weights=[50, 30, 20], k=1)[0]
    user = query.from_user
    if outcome == "treasure":
        bonus = random.randint(100, 300)
        await add_points(user.id, user.username or user.first_name, bonus)
        message = f"🎉 Glückwunsch, {user.username or user.first_name}! Du hast einen galaktischen Schatz gefunden und {bonus} Punkte gewonnen!"
    elif outcome == "nothing":
        message = f"😕 Leider, {user.username or user.first_name}, hast du keinen Schatz gefunden. Versuch es nochmal!"
    else:
        penalty = random.randint(20, 50)
        await add_points(user.id, user.username or user.first_name, -penalty)
        message = f"💥 Oh nein, {user.username or user.first_name}! Eine Falle – du verlierst {penalty} Punkte!"
    await query.message.edit_text(message)

# ----------------- GALACTIC BATTLE (Extra Special) ----------------- #
async def battle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Fordere den feindlichen Kapitän in einem galaktischen Duell heraus!
    Einsatz: 100 Punkte.
      - Sieg: Gewinn zwischen 200 und 500 Punkten.
      - Unentschieden: Keine Änderung.
      - Niederlage: Verlust von weiteren 100 Punkten.
    """
    user = update.message.from_user
    data = load_data(POINTS_FILE)
    user_id = str(user.id)
    current_points = data.get(user_id, {}).get("points", 0)
    if current_points < 100:
        await update.message.reply_text("Du benötigst mindestens 100 Punkte für den Galactic Battle!")
        return
    await add_points(user.id, user.username or user.first_name, -100)  # Einsatz abziehen
    outcome = random.choices(["win", "draw", "lose"], weights=[40, 30, 30], k=1)[0]
    if outcome == "win":
        reward = random.randint(200, 500)
        await add_points(user.id, user.username or user.first_name, reward)
        message = f"⚔️ Sieg! {user.username or user.first_name}, du besiegst den feindlichen Kapitän und gewinnst {reward} Punkte!"
    elif outcome == "draw":
        message = f"🤝 Unentschieden! Der Kampf war hart, aber es ändert sich nichts."
    else:
        await add_points(user.id, user.username or user.first_name, -100)
        message = f"💥 Niederlage! {user.username or user.first_name}, du verlierst den Kampf und zusätzlich 100 Punkte."
    await update.message.reply_text(message)

# ----------------- GALACTIC UPGRADE (Extra Feature) ----------------- #
async def upgrade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Starte ein galaktisches Upgrade!
    Kosten: 200 Punkte.
    Nach 60 Sekunden erhältst du einen zufälligen Bonus (150–500 Punkte).
    """
    user = update.message.from_user
    data = load_data(POINTS_FILE)
    user_id = str(user.id)
    current_points = data.get(user_id, {}).get("points", 0)
    if current_points < 200:
        await update.message.reply_text("Du benötigst mindestens 200 Punkte für ein Upgrade! 🚀")
        return
    await add_points(user.id, user.username or user.first_name, -200)
    await update.message.reply_text("🛠️ Dein galaktisches Upgrade startet! Bitte warte 60 Sekunden...")
    context.job_queue.run_once(upgrade_complete, 60, data={"user_id": user.id, "username": user.username or user.first_name})

async def upgrade_complete(context: ContextTypes.DEFAULT_TYPE):
    data = context.job.data
    user_id = data["user_id"]
    username = data["username"]
    bonus = random.randint(150, 500)
    await add_points(user_id, username, bonus)
    await context.bot.send_message(chat_id=GROUP_ID, text=f"🚀 Upgrade abgeschlossen! {username} erhält {bonus} Bonuspunkte!")

# ---------------------- Hauptprogramm / BOT start -------------- #
def main():
    """
    Initialisiert den Telegram-Bot, registriert alle Befehle und startet den Polling-Prozess.
    Außerdem werden:
      - Die stündliche Ranglistenanzeige
      - Das automatische Frage-Event alle 2 Stunden
    eingeplant.
    """
    app = Application.builder().token(BOT_TOKEN).build()

    # Befehle registrieren
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("com", commands_list))
    app.add_handler(CommandHandler("points", points))
    app.add_handler(CommandHandler("claim", claim))
    app.add_handler(CommandHandler("start_event", start_event))
    app.add_handler(CommandHandler("stop_event", stop_event))
    app.add_handler(CommandHandler("botsend", bot_send))
    app.add_handler(CommandHandler("protocol", adm_protocol))
    app.add_handler(CommandHandler("daily", daily_bonus))
    app.add_handler(CommandHandler("ranking_chart", ranking_chart))
    app.add_handler(CommandHandler("lottery", lottery))
    app.add_handler(CommandHandler("adventure", adventure))
    app.add_handler(CommandHandler("treasure", treasure))
    app.add_handler(CommandHandler("battle", battle))
    app.add_handler(CommandHandler("upgrade", upgrade))
    
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_new_member))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Interaktive Buttons verarbeiten
    app.add_handler(CallbackQueryHandler(button_click))
    app.add_handler(CallbackQueryHandler(adventure_callback, pattern=r"^/adventure_"))
    app.add_handler(CallbackQueryHandler(treasure_callback, pattern=r"^/treasure_"))
    
    # Job Queue: Stündliche Ranglistenanzeige
    app.job_queue.run_repeating(show_ranking, interval=3600, first=10)
    # Automatisches Frage-Event alle 2 Stunden (7200 Sekunden)
    app.job_queue.run_repeating(auto_question, interval=7200, first=10)

    logging.info("🚀 Bot läuft [erfolgreich]!")
    app.run_polling()

if __name__ == "__main__":
    main()
