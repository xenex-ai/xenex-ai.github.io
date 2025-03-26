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

# ------------ APSCHEDULER NOTES unterdrücken ------------#
# logging.getLogger('apscheduler').setLevel(logging.WARNING)
# // DEAKTIVIERT

# ------------------ Bot-Konfiguration ------------------ #
BOT_TOKEN = "7761649059:AAEQtfHDd1FXeE5wH3rPIyuXzBXnqB4eP94"
CHANNEL_ID = "@xentst"
GROUP_ID = "-1001734852517"
ADMIN_USERS = ["w3kmdo", "Den_XNX"]  # Nur diese Nutzer dürfen Admin-Befehle nutzen

# --------------------- JSON-Dateien -------------------- #
POINTS_FILE = "tst_point.json"           # Normale Punkteliste
EVENT_POINTS_FILE = "tst_event_point.json"  # Punkte für das Frage-Event
WALLETS_FILE = "tst_wallet.json"         # Wallets der Nutzer
QUESTIONS_FILE = "questions.json"        # Fragen für das automatische Event
ADM_ACTIVITY_FILE = "tst_activity.json"  # ADMIN protokoll

ACTIVITY_FILE = ADM_ACTIVITY_FILE

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
            if not isinstance(data, list):  # Falls das Format falsch ist
                return []
            return data[-100:]  # Letzte 100 Einträge zurückgeben
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
    data.append({"user": user, "action": action})
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
    logging.info(f"{username} hat {points} Punkte erhalten! (Total: {data[str(user_id)]['points']})")
    # Datei-Upload (falls benötigt)
    url = "https://corenetwork.io/xenexAi/connect/json.php"
    with open(POINTS_FILE, "rb") as file_obj:
        try:
            response = requests.post(url, files={"file": file_obj})
            if response.status_code == 200:
                log_activity(username, "checked_points")
                logging.info("Datei erfolgreich hochgeladen!")
            else:
                logging.info(f"Fehler beim Hochladen: {response.status_code}")
        except Exception as e:
            logging.info(f"Fehler: {str(e)}")

# ------------------ RANGLISTE ZEIGEN -------------------- #
async def show_ranking(context: ContextTypes.DEFAULT_TYPE):
    """
    Sendet stündlich die Top 10 der Rangliste in die Gruppe.
    Die Rangliste wird aus POINTS_FILE erstellt.
    """
    data = load_data(POINTS_FILE)
    if not data:
        message = "Noch keine Punkte vergeben."
    else:
        ranking = sorted(data.items(), key=lambda x: x[1]["points"], reverse=True)
        message = "**Top Punkteliste**\n\n"
        for i, (user_id, info) in enumerate(ranking[:10], 1):
            message += f"{i}. {info['username']} - {info['points']} Punkte\n"
    logging.info("Rangliste wurde gesendet.")
    await context.bot.send_message(chat_id=GROUP_ID, text=message)

# ---------- ZEIT-ERINNERUNGEN WÄHREND DES EVENT --------- #
async def send_time_reminder(context: ContextTypes.DEFAULT_TYPE):
    """Sendet eine Erinnerung während des Events, die die noch verbleibende Zeit anzeigt und einen intergalaktischen Motivationsspruch enthält."""
    data = context.job.data
    remaining = data["remaining"]
    reminder_message = data["message"]
    text = f"Noch **{remaining} Minuten** bis zum Ende des Frage-Events!\n\n{reminder_message}"
    await context.bot.send_message(chat_id=GROUP_ID, text=text)

def schedule_reminders(job_queue):
    """Plant 4 Erinnerungs-Jobs während des Events mit intergalaktischen Motivationssprüchen."""
    messages = [
        "Die Sterne beben vor Energie!",
        "Intergalaktische Kräfte sind am Werk!",
        "Das Universum feuert dich an!",
        "Kosmische Energie pulsiert durch deine Adern!"
    ]
    reminders = random.sample(messages, 4)
    job_queue.run_once(send_time_reminder, when=5 * 60, data={"remaining": 25, "message": reminders[0]})
    job_queue.run_once(send_time_reminder, when=10 * 60, data={"remaining": 20, "message": reminders[1]})
    job_queue.run_once(send_time_reminder, when=20 * 60, data={"remaining": 10, "message": reminders[2]})
    job_queue.run_once(send_time_reminder, when=25 * 60, data={"remaining": 5, "message": reminders[3]})
    logging.info("Zeit-Erinnerungen wurden geplant.")

# --------------- AUTOMATISCHES FRAGE-EVENT --------------- #
async def auto_question(context: ContextTypes.DEFAULT_TYPE):
    """Wählt zufällig eine Frage aus und startet das automatische Frage-Event."""
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
        logging.info("Frage wurde fixiert.")
    except Exception as e:
        logging.error(f"Fehler beim Fixieren der Nachricht: {e}")
    event_active = True
    await context.bot.send_message(chat_id=GROUP_ID, text="❓ Das Frage-Event hat begonnen! Alle Antworten zählen jetzt.")
    schedule_reminders(context.job_queue)
    context.job_queue.run_once(auto_stop_event, when=30 * 60, data=question_message.message_id)

async def auto_stop_event(context: ContextTypes.DEFAULT_TYPE):
    """
    Beendet das automatische Frage-Event, kürt den Gewinner und schreibt Bonuspunkte in POINTS_FILE.
    Setzt das Event zurück und entfixiert die ursprüngliche Frage.
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
            f"📢 Das Frage-Event ist vorbei! 🎉 \n\n"
            f"🏆 Herzlichen Glückwunsch {user_info['username']}! \n"
            f"Du hast das Event gewonnen und erhältst {bonus_points} Bonuspunkte!"
        )
        logging.info(f"Gewinner automatisch gekürt: {user_info['username']} mit {bonus_points} Punkten.")
        await context.bot.send_message(chat_id=GROUP_ID, text=winner_message)
    message_id = context.job.data
    try:
        await context.bot.unpin_chat_message(chat_id=GROUP_ID, message_id=message_id)
        logging.info("Die Frage wurde entfixiert.")
    except Exception as e:
        logging.error("Fehler beim Entfixieren der Nachricht: " + str(e))

# ### EVENT-START (manuell durch Admin) ###
async def start_event(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Startet ein Frage-Event manuell (nur für Admins)."""
    global event_active
    user = update.message.from_user
    if user.username not in ADMIN_USERS:
        await update.message.reply_text("Du bist nicht berechtigt, diesen Befehl auszuführen.")
        return
    event_active = True
    save_data(EVENT_POINTS_FILE, {})  # Event-Punkte zurücksetzen
    logging.info("Frage-Event wurde manuell gestartet.")
    await context.bot.send_message(chat_id=GROUP_ID,
                                   text="Das Frage-Event hat begonnen! Alle Punkte zählen nun für das Event.")
    schedule_reminders(context.job_queue)

# ### EVENT-BEENDEN & GEWINNER KÜREN (manuell durch Admin) ###
async def stop_event(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Beendet das Frage-Event manuell (nur für Admins) und kürt den Gewinner."""
    global event_active
    user = update.message.from_user
    if user.username not in ADMIN_USERS:
        await update.message.reply_text("⛔ Du bist nicht berechtigt, diesen Befehl auszuführen.")
        return
    event_active = False
    event_data = load_data(EVENT_POINTS_FILE)
    if not event_data:
        await context.bot.send_message(chat_id=GROUP_ID, text="Kein Teilnehmer hat Punkte gesammelt.")
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
        f"**Das Frage-Event ist vorbei!**\n\n"
        f"**Herzlichen Glückwunsch {user_info['username']}!**\n"
        f"Du hast das Event gewonnen und erhältst **{bonus_points} Bonuspunkte**!"
    )
    logging.info(f"Gewinner manuell gekürt: {user_info['username']} mit {bonus_points} Punkten.")
    await context.bot.send_message(chat_id=GROUP_ID, text=winner_message)

# ### NEUE MITGLIEDER BEGRÜSSEN ###
async def welcome_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Begrüßt neue Mitglieder in der Gruppe und vergibt automatisch 3 Willkommenspunkte.
    """
    for member in update.message.new_chat_members:
        username = f"@{member.username}" if member.username else member.first_name
        await add_points(member.id, username, 3)
        message = f"Willkommen {username} in der Xenex AI Community!"
        await update.message.reply_text(message)

# ### STANDARD BOT-BEFEHLE ###
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Standard /start-Befehl, der den Bot vorstellt."""
    await update.message.reply_text("Willkommen beim Xenex AI Community Bot! Nutze /points, um deine Punkte zu sehen.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Verarbeitet normale Nachrichten und vergibt Punkte:
    - 1 Punkt für eine normale Nachricht
    - 2 Punkte, wenn die Nachricht eine Antwort ist.
    """
    user = update.message.from_user
    points_val = 2 if update.message.reply_to_message else 1
    await add_points(user.id, user.username or user.first_name, points_val)

async def points(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Zeigt dem Nutzer seine aktuellen Punkte aus POINTS_FILE an."""
    user = update.message.from_user
    data = load_data(POINTS_FILE)
    user_points = data.get(str(user.id), {}).get("points", 0)
    await update.message.reply_text(f"{user.username or user.first_name}, du hast {user_points} Punkte!")

async def claim(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Zeigt dem Nutzer eine Option, Punkte einzulösen, mit einem Inline-Button."""
    user = update.message.from_user
    data = load_data(POINTS_FILE)
    user_points = data.get(str(user.id), {}).get("points", 0)
    keyboard = [[InlineKeyboardButton("Ja, Punkte einlösen",
                                      url=f"https://xenex-ai.github.io/dev/27_tst_xnx.html?name={user.username}&address={user_points}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(f"Möchtest du deine Punkte gegen $XNX eintauschen? Du hast {user_points} Punkte!",
                                    reply_markup=reply_markup)

async def bot_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lässt Admins eine Nachricht im Namen des Bots senden."""
    user = update.message.from_user
    if user.username not in ADMIN_USERS:
        await update.message.reply_text("⛔ Keine Berechtigung!")
        return
    try:
        text = " ".join(context.args)
        if not text:
            await update.message.reply_text("Nutzung: /botsend <Text>")
            return
        logging.info(f"Admin {user.username} hat eine Nachricht gesendet: {text}")
        await context.bot.send_message(chat_id=GROUP_ID, text=text)
        logging.info(f"Admin-Nachricht gesendet: {text}")
        await update.message.reply_text("Nachricht gesendet!")
    except Exception as e:
        logging.info(f"Fehler beim Senden der Nachricht: {e}")
        await update.message.reply_text("Fehler beim Senden der Nachricht.")

# -------------- KOMMANDOLISTE MIT BUTTONS ------------- #
async def commands_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Zeigt alle Befehle mit klickbaren Buttons an."""
    keyboard = [
        [InlineKeyboardButton("🏁 Start", callback_data="/start")],
        [InlineKeyboardButton("📊 Punkteliste", callback_data="/points")],
        [InlineKeyboardButton("💰 Punkte einlösen", callback_data="/claim")]
    ]
    user = update.message.from_user if update.message else update.callback_query.from_user
    if user.username in ADMIN_USERS:
        keyboard.append([InlineKeyboardButton("➕ Fragenevent starten", callback_data="/start_event")])
        keyboard.append([InlineKeyboardButton("❌ Fragenevent stoppen", callback_data="/stop_event")])
        keyboard.append([InlineKeyboardButton("📢 Nachricht senden", callback_data="/botsend")])
        keyboard.append([InlineKeyboardButton("👋 Admin Protocol", callback_data="/protocol")])
    # Füge unseren neuen Button für das Ranking-Chart hinzu
    keyboard.append([InlineKeyboardButton("📈 Ranglisten-Chart", callback_data="/ranking_chart")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.message:
        await update.message.reply_text("**Befehlsübersicht**\n\nWähle einen Befehl aus:", reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.message.edit_text("**Befehlsübersicht**\n\nWähle einen Befehl aus:", reply_markup=reply_markup)

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reagiert auf Buttons und führt den entsprechenden Befehl aus."""
    query = update.callback_query
    await query.answer()
    command = query.data
    user = query.from_user
    if command == "/start":
        await start(update, context)
    elif command == "/points":
        await points(update, context)
    elif command == "/claim":
        await claim(update, context)
    elif command == "/ranking_chart":
        await ranking_chart(update, context)
    elif user.username in ADMIN_USERS:
        if command == "/start_event":
            await query.message.reply_text("Nutze den Befehl direkt: /start_event")
        elif command == "/stop_event":
            await query.message.reply_text("Nutze den Befehl direkt: /stop_event")
        elif command == "/botsend":
            await query.message.reply_text("Nutze den Befehl direkt: /botsend <message>")
        elif command == "/protocol":
            await query.message.reply_text("Nutze den Befehl direkt: /protocol")

# ---------------- Admin Protocol ---------------- #
async def adm_protocol(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Zeigt die letzten 100 Einträge aus tst_activity.json für Admins an."""
    user = update.message.from_user
    if user.username not in ADMIN_USERS:
        await update.message.reply_text("⛔ Du bist nicht berechtigt, diesen Befehl zu nutzen.")
        return
    activities = load_activity_data()
    if not activities:
        await update.message.reply_text("Keine Aktivitätsdaten gefunden.")
        return
    message = "**Letzte 100 Aktivitäten:**\n\n"
    for entry in activities[-10:]:
        message += f"- {entry}\n"
    if len(message) > 4000:
        message_chunks = [message[i:i + 4000] for i in range(0, len(message), 4000)]
        for chunk in message_chunks:
            await update.message.reply_text(chunk, parse_mode="Markdown")
    else:
        await update.message.reply_text(message, parse_mode="Markdown")

# ----------------- RANKING CHART /ranking_chart ----------------- #
def load_points():
    """Lädt die Punkte aus der JSON-Datei."""
    if not os.path.exists(POINTS_FILE):
        return {}
    with open(POINTS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def generate_ranking_chart():
    """
    Erstellt ein Balkendiagramm der Top 10 Rangliste mit einem futuristischen, galaktischen Look.
    Speichert das Diagramm als Bild und gibt den Pfad zurück.
    """
    points_data = load_points()
    if not points_data:
        return None

    # Sortiere die Daten nach Punkten (absteigend) und nimm die Top 10
    sorted_items = sorted(points_data.items(), key=lambda x: x[1]["points"], reverse=True)[:10]
    usernames = [item[1]["username"] for item in sorted_items]
    scores = [item[1]["points"] for item in sorted_items]

    # Setze den Matplotlib-Stil auf dark_background für den galaktischen Look
    mpl.style.use("dark_background")
    fig, ax = plt.subplots(figsize=(10, 6))
    # Erstelle horizontale Balken, invertiere Reihenfolge für Top-List-Optik
    bars = ax.barh(usernames[::-1], scores[::-1], color="#00FFFF", edgecolor="#0000FF")
    ax.set_xlabel("Punkte", fontsize=14, color="white")
    ax.set_ylabel("Spieler", fontsize=14, color="white")
    ax.set_title("Galaktische Top 10 Rangliste", fontsize=18, color="white", pad=15)
    ax.grid(axis="x", linestyle="--", alpha=0.7)

    # Beschrifte jeden Balken mit dem jeweiligen Score
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
    """Sendet das generierte Ranking-Diagramm an den Chat."""
    image_path = generate_ranking_chart()
    if image_path:
        await context.bot.send_photo(chat_id=update.effective_chat.id, photo=open(image_path, "rb"))
    else:
        await update.message.reply_text("Keine Punkte verfügbar, um ein Chart zu erstellen.")

# ----------------- Zusätzlicher Daily Bonus (Special) ----------------- #
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
    """Gibt dem User einmal täglich einen Zufallsbonus an Punkten."""
    user = update.message.from_user
    daily_data = load_daily_bonus()
    user_id = str(user.id)
    current_time = time.time()
    last_claim = daily_data.get(user_id, 0)
    if current_time - last_claim < 86400:
        await update.message.reply_text("Du hast deinen täglichen Bonus schon abgeholt! Komm morgen wieder.")
        return
    bonus = random.randint(50, 200)
    await add_points(user.id, user.username or user.first_name, bonus)
    daily_data[user_id] = current_time
    save_daily_bonus(daily_data)
    await update.message.reply_text(f"Glückwunsch {user.username or user.first_name}! Du hast heute {bonus} Bonuspunkte erhalten!")

# ---------------------- Hauptprogramm / BOT start -------------- #
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
    app.add_handler(CommandHandler("claim", claim))
    app.add_handler(CommandHandler("start_event", start_event))
    app.add_handler(CommandHandler("stop_event", stop_event))
    app.add_handler(CommandHandler("botsend", bot_send))
    app.add_handler(CommandHandler("protocol", adm_protocol))
    app.add_handler(CommandHandler("daily", daily_bonus))
    # Unser Ranking-Chart-Befehl
    app.add_handler(CommandHandler("ranking_chart", ranking_chart))
    
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_new_member))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Interaktive Buttons verarbeiten
    app.add_handler(CallbackQueryHandler(button_click))
    
    # Job Queue: Stündliche Ranglistenanzeige
    app.job_queue.run_repeating(show_ranking, interval=3600, first=10)
    # Automatisches Frage-Event alle 2 Stunden (7200 Sekunden)
    app.job_queue.run_repeating(auto_question, interval=7200, first=10)

    logging.info("Bot läuft [erfolgreich]")
    app.run_polling()

if __name__ == "__main__":
    main()
