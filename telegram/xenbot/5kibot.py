import json
import random
import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ChatMemberHandler, filters, ContextTypes

### 🔧 BOT KONFIGURATION ###
BOT_TOKEN = "7761649059:AAEQtfHDd1FXeE5wH3rPIyuXzBXnqB4eP94"
CHANNEL_ID = "@xentst"
GROUP_ID = "-1001734852517"
ADMIN_USERS = ["w3kmdo", "den_xnx"]  # Nur diese Nutzer dürfen Admin-Befehle nutzen

### 📂 JSON-DATEIEN ###
POINTS_FILE = "tst_point.json"            # Normale Punkteliste
EVENT_POINTS_FILE = "tst_event_point.json"  # Punkte für das Frage-Event
WALLETS_FILE = "tst_wallet.json"           # Wallets der Nutzer
QUESTIONS_FILE = "questions.json"          # Fragen für das automatische Event

### 🌍 EVENT-STATUS ###
event_active = False  # Gibt an, ob ein Frage-Event aktiv ist

### 📝 LOGGING KONFIGURATION ###
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)

### 📂 JSON HILFSFUNKTIONEN ###
def load_data(file):
    """
    Lädt Daten aus einer JSON-Datei.
    Falls die Datei nicht existiert, wird ein leeres Dictionary zurückgegeben.
    """
    try:
        with open(file, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_data(file, data):
    """
    Speichert Daten in eine JSON-Datei mit schöner Formatierung.
    """
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

### 🔢 PUNKTE-VERGABE ###
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

### 🏆 RANGLISTE ZEIGEN ###
async def show_ranking(context: ContextTypes.DEFAULT_TYPE):
    """
    Sendet stündlich die Top 10 der Rangliste in die Gruppe.
    Die Rangliste wird aus POINTS_FILE erstellt.
    """
    data = load_data(POINTS_FILE)

    if not data:
        message = "📊 Noch keine Punkte vergeben."
    else:
        ranking = sorted(data.items(), key=lambda x: x[1]["points"], reverse=True)
        message = "🏆 **Top Punkteliste** 🏆\n\n"
        for i, (user_id, info) in enumerate(ranking[:10], 1):
            message += f"{i}. {info['username']} - {info['points']} Punkte\n"

    logging.info("📊 Rangliste wurde gesendet.")
    await context.bot.send_message(chat_id=GROUP_ID, text=message)

### ⏰ ZEIT-ERINNERUNGEN WÄHREND DES EVENTS ###
async def send_time_reminder(context: ContextTypes.DEFAULT_TYPE):
    """
    Sendet eine Erinnerung während des Events, die die noch verbleibende Zeit anzeigt
    und einen intergalaktisch motivierenden Text enthält.
    """
    data = context.job.data
    remaining = data["remaining"]  # Verbleibende Minuten bis zum Ende
    reminder_message = data["message"]
    text = f"⏰ Noch **{remaining} Minuten** bis zum Ende des Frage-Events!\n\n{reminder_message}"
    await context.bot.send_message(chat_id=GROUP_ID, text=text)

def schedule_reminders(job_queue):
    """
    Plant 4 Erinnerungs-Jobs während des Events.
    Die Erinnerungen werden nach 5, 10, 20 und 25 Minuten versendet,
    was einer verbleibenden Zeit von 25, 20, 10 bzw. 5 Minuten entspricht.
    Jeder Job erhält einen zufällig (und alle unterschiedlich) ausgewählten intergalaktischen Motivationsspruch.
    """
    # Liste mit intergalaktischen Motivationssprüchen
    messages = [
        "Die Sterne beben vor Energie!",
        "Intergalaktische Kräfte sind am Werk!",
        "Das Universum feuert dich an!",
        "Kosmische Energie pulsiert durch deine Adern!"
    ]
    # Wähle 4 unterschiedliche Sprüche zufällig aus
    reminders = random.sample(messages, 4)
    # Plane die Erinnerungen
    job_queue.run_once(send_time_reminder, when=5*60, data={"remaining": 25, "message": reminders[0]})
    job_queue.run_once(send_time_reminder, when=10*60, data={"remaining": 20, "message": reminders[1]})
    job_queue.run_once(send_time_reminder, when=20*60, data={"remaining": 10, "message": reminders[2]})
    job_queue.run_once(send_time_reminder, when=25*60, data={"remaining": 5, "message": reminders[3]})
    logging.info("⏰ Zeit-Erinnerungen wurden geplant.")

### 🚀 AUTOMATISCHES FRAGE-EVENT ###
async def auto_question(context: ContextTypes.DEFAULT_TYPE):
    """
    Diese Funktion wird alle 2 Stunden automatisch ausgeführt:
    - Es wird eine Frage aus QUESTIONS_FILE (als Liste) zufällig ausgewählt.
    - Die Frage wird in der Gruppe gepostet und fixiert.
    - Das Event wird automatisch gestartet (event_active = True).
    - Gleichzeitig werden Erinnerungen und ein Job zum automatischen Beenden (nach 30 Minuten) geplant.
    """
    global event_active

    # Lade Fragen aus der questions.json
    questions = load_data(QUESTIONS_FILE)
    if not questions or not isinstance(questions, list):
        logging.error("Fragen-Datei leer oder ungültig. Bitte überprüfe questions.json.")
        return

    # Zufällige Frage auswählen
    question = random.choice(questions)
    text = f"❓ **Frage des Events:**\n\n{question}"

    # Frage senden
    message = await context.bot.send_message(chat_id=GROUP_ID, text=text)
    logging.info("❓ Frage des Events wurde gesendet.")

    # Nachricht fixieren
    try:
        await context.bot.pin_chat_message(chat_id=GROUP_ID, message_id=message.message_id, disable_notification=True)
        logging.info("📌 Frage wurde fixiert.")
    except Exception as e:
        logging.error("Fehler beim Fixieren der Nachricht: " + str(e))

    # Event automatisch starten
    event_active = True
    await context.bot.send_message(chat_id=GROUP_ID, text="🎉 Das Frage-Event hat begonnen! Alle Antworten zählen jetzt.")
    
    # Plane die Zeit-Erinnerungen (4 Nachrichten mit verbleibender Zeit)
    schedule_reminders(context.job_queue)
    
    # Plane automatisches Beenden des Events in 30 Minuten
    context.job_queue.run_once(auto_stop_event, when=30*60, data=message.message_id)

### 🏁 AUTOMATISCHES EVENT-BEENDEN ###
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
        await context.bot.send_message(chat_id=GROUP_ID, text="❌ Kein Teilnehmer hat Punkte gesammelt im Event.")
    else:
        # Gewinner ermitteln: Nutzer mit den meisten Event-Punkten
        winner = max(event_data.items(), key=lambda x: x[1]["points"])
        user_id, user_info = winner
        bonus_points = random.randint(100, 250)

        # Bonuspunkte auf Hauptkonto gutschreiben (POINTS_FILE)
        main_data = load_data(POINTS_FILE)
        if user_id not in main_data:
            main_data[user_id] = {"username": user_info["username"], "points": 0}
        main_data[user_id]["points"] += bonus_points
        save_data(POINTS_FILE, main_data)

        # Event-Punkte zurücksetzen
        save_data(EVENT_POINTS_FILE, {})

        # Gewinner feiern
        winner_message = (
            f"🏆 **Das Frage-Event ist vorbei!** 🏆\n\n"
            f"🎉 **Herzlichen Glückwunsch {user_info['username']}!** 🎉\n"
            f"Du hast das Event gewonnen und erhältst **{bonus_points} Bonuspunkte**! 🎁"
        )
        logging.info(f"🏆 Gewinner automatisch gekürt: {user_info['username']} mit {bonus_points} Punkten.")
        await context.bot.send_message(chat_id=GROUP_ID, text=winner_message)

    # Nachricht entfixieren (verwende die message_id, die als Job-Daten übergeben wurde)
    message_id = context.job.data
    try:
        await context.bot.unpin_chat_message(chat_id=GROUP_ID, message_id=message_id)
        logging.info("📌 Die Frage wurde entfixiert.")
    except Exception as e:
        logging.error("Fehler beim Entfixieren der Nachricht: " + str(e))

### 🚀 EVENT-START (manuell durch Admin) ###
async def start_event(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Startet ein Frage-Event (manuell).
    Nur Admins (in ADMIN_USERS) dürfen diesen Befehl ausführen.
    Während des Events werden Punkte in EVENT_POINTS_FILE gespeichert.
    Zusätzlich werden die Zeit-Erinnerungen geplant.
    """
    global event_active
    user = update.message.from_user
    if user.username not in ADMIN_USERS:
        await update.message.reply_text("❌ Du bist nicht berechtigt, diesen Befehl auszuführen.")
        return

    event_active = True
    save_data(EVENT_POINTS_FILE, {})  # Setzt Event-Punkte zurück
    logging.info("🎉 Frage-Event wurde manuell gestartet.")
    await context.bot.send_message(chat_id=GROUP_ID, text="🎉 Das Frage-Event hat begonnen! Alle Punkte zählen nun für das Event.")
    
    # Plane Zeit-Erinnerungen (4 Nachrichten)
    schedule_reminders(context.job_queue)

### 🏁 EVENT-BEENDEN & GEWINNER KÜREN (manuell durch Admin) ###
async def stop_event(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Beendet das Frage-Event (manuell), kürt den Gewinner und schreibt Bonuspunkte in POINTS_FILE.
    Nur Admins dürfen diesen Befehl ausführen.
    Nach Beendigung wird EVENT_POINTS_FILE zurückgesetzt.
    """
    global event_active
    user = update.message.from_user
    if user.username not in ADMIN_USERS:
        await update.message.reply_text("❌ Du bist nicht berechtigt, diesen Befehl auszuführen.")
        return

    event_active = False
    event_data = load_data(EVENT_POINTS_FILE)

    if not event_data:
        await context.bot.send_message(chat_id=GROUP_ID, text="❌ Kein Teilnehmer hat Punkte gesammelt.")
        return

    # Gewinner ermitteln: Nutzer mit den meisten Event-Punkten
    winner = max(event_data.items(), key=lambda x: x[1]["points"])
    user_id, user_info = winner
    bonus_points = random.randint(100, 250)

    # Bonuspunkte auf Hauptkonto gutschreiben (POINTS_FILE)
    main_data = load_data(POINTS_FILE)
    if user_id not in main_data:
        main_data[user_id] = {"username": user_info["username"], "points": 0}
    main_data[user_id]["points"] += bonus_points
    save_data(POINTS_FILE, main_data)

    # Event-Punkte zurücksetzen
    save_data(EVENT_POINTS_FILE, {})

    # Gewinner feiern
    winner_message = (
        f"🏆 **Das Frage-Event ist vorbei!** 🏆\n\n"
        f"🎉 **Herzlichen Glückwunsch {user_info['username']}!** 🎉\n"
        f"Du hast das Event gewonnen und erhältst **{bonus_points} Bonuspunkte**! 🎁"
    )
    logging.info(f"🏆 Gewinner manuell gekürt: {user_info['username']} mit {bonus_points} Punkten.")
    await context.bot.send_message(chat_id=GROUP_ID, text=winner_message)

### 👋 NEUE MITGLIEDER BEGRÜSSEN ###
async def welcome_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Begrüßt neue Mitglieder in der Gruppe und vergibt automatisch 3 Willkommenspunkte.
    """
    for member in update.message.new_chat_members:
        username = f"@{member.username}" if member.username else member.first_name
        await add_points(member.id, username, 3)
        message = f"👋 Willkommen {username} in der Xenex AI Community! 🚀"
        await update.message.reply_text(message)

### 🤖 STANDARD BOT-BEFEHLE ###
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Standard /start-Befehl, der den Bot vorstellt.
    """
    await update.message.reply_text("👋 Willkommen beim Xenex AI Community Bot! Nutze /points, um deine Punkte zu sehen.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Verarbeitet normale Nachrichten und vergibt Punkte:
    - 1 Punkt für eine normale Nachricht
    - 2 Punkte, wenn die Nachricht eine Antwort ist
    """
    user = update.message.from_user
    points = 2 if update.message.reply_to_message else 1
    await add_points(user.id, user.username or user.first_name, points)

async def points(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Zeigt dem Nutzer seine aktuellen Punkte aus POINTS_FILE an.
    """
    user = update.message.from_user
    data = load_data(POINTS_FILE)
    user_points = data.get(str(user.id), {}).get("points", 0)
    await update.message.reply_text(f"🏅 **{user.username or user.first_name}, du hast {user_points} Punkte!**")

async def claim(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Zeigt dem Nutzer eine Option, Punkte einzulösen, mit einem Inline-Button.
    """
    user = update.message.from_user
    keyboard = [[InlineKeyboardButton("✅ Ja, Punkte einlösen", url=f"https://xenex-ai.github.io/dev/24_tst_xnx.html?name={user.username}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("💰 Möchtest du deine Punkte gegen $XNX eintauschen?", reply_markup=reply_markup)

### 🏗 HAUPTPROGRAMM / BOT START ###
def main():
    """
    Initialisiert den Telegram-Bot, registriert alle Befehle und startet den Polling-Prozess.
    Zusätzlich werden:
      - Die stündliche Ranglistenanzeige geplant.
      - Das automatische Frage-Event alle 2 Stunden eingeplant.
    """
    app = Application.builder().token(BOT_TOKEN).build()

    # 📜 Befehle registrieren
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("points", points))
    app.add_handler(CommandHandler("claim", claim))
    app.add_handler(CommandHandler("start_event", start_event))
    app.add_handler(CommandHandler("stop_event", stop_event))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_new_member))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # 🔄 Stündliche Ranglisten-Anzeige (Job Queue)
    app.job_queue.run_repeating(show_ranking, interval=3600, first=10)

    # 🤖 Automatisches Frage-Event alle 2 Stunden (7200 Sekunden)
    app.job_queue.run_repeating(auto_question, interval=7200, first=10)

    logging.info("🤖 Bot läuft...")
    app.run_polling()

if __name__ == "__main__":
    main()
