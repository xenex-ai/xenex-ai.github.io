import logging
import json
import random
import os
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes

# Konfiguration des Loggings
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# Globale Variablen für den Frage-Runden-Status
QUESTION_ROUND_ACTIVE = False
CURRENT_QUESTION_MESSAGE_ID = None
CURRENT_QUESTION_CHAT_ID = None
QUESTION_ROUND_ACTIVITY = {}  # {user_id: anzahl_nachrichten}
REMINDER_JOBS = []  # Referenzen zu Reminder-Jobs

# Dateipfade für Punkte und Fragen
POINTS_FILE = "tst_point.json"
QUESTIONS_FILE = "questions.json"

# --------------------- Helper-Funktionen ---------------------
def load_points():
    """Lädt die Punkte aus der JSON-Datei."""
    if os.path.exists(POINTS_FILE):
        with open(POINTS_FILE, "r") as f:
            return json.load(f)
    return {}

def save_points(points):
    """Speichert die Punkte in die JSON-Datei."""
    with open(POINTS_FILE, "w") as f:
        json.dump(points, f)

def load_questions():
    """Lädt die Fragen aus der JSON-Datei."""
    if os.path.exists(QUESTIONS_FILE):
        with open(QUESTIONS_FILE, "r") as f:
            return json.load(f)
    else:
        logger.error(f"{QUESTIONS_FILE} nicht gefunden.")
        return []

# --------------------- Command-Handler ---------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Begrüßt den User und informiert über den Bot."""
    await update.message.reply_text("Hallo! Jede Stunde wird eine Frage gestellt. Viel Spaß und Erfolg!")

async def claim(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Liefert den Claim-Link, der den aktuellen Punktewert und den Usernamen enthält.
    Alternativ kann auch der Inline-Button genutzt werden.
    """
    user = update.effective_user
    points = load_points()
    user_points = points.get(str(user.id), 0)
    username = user.username if user.username else user.first_name
    url = f"https://xenex-ai.github.io/dev/27_tst_xnx.html?address={user_points}&name={username}"
    await update.message.reply_text(f"Hier ist dein Claim-Link:\n{url}")

async def claim_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    CallbackQueryHandler für den 'Claim'-Button.
    Der Link wird basierend auf den aktuellen User-Punkten dynamisch generiert.
    """
    query = update.callback_query
    user = query.from_user
    points = load_points()
    user_points = points.get(str(user.id), 0)
    username = user.username if user.username else user.first_name
    url = f"https://xenex-ai.github.io/dev/27_tst_xnx.html?address={user_points}&name={username}"
    await query.answer()
    await query.edit_message_text(text=f"Claim-Link:\n{url}")

# --------------------- Job-Funktionen ---------------------
async def new_question_job(context: ContextTypes.DEFAULT_TYPE):
    """
    Job, der stündlich eine neue Frage startet:
    - Wählt eine zufällige Frage aus questions.json
    - Sendet die Frage an den Chat und pinnt die Nachricht
    - Setzt den Frage-Runden-Status auf aktiv
    - Plant Reminder (alle 10 Minuten) und das Ende der Runde (nach 30 Minuten)
    """
    global QUESTION_ROUND_ACTIVE, CURRENT_QUESTION_MESSAGE_ID, CURRENT_QUESTION_CHAT_ID, QUESTION_ROUND_ACTIVITY, REMINDER_JOBS

    if QUESTION_ROUND_ACTIVE:
        # Falls bereits eine Runde aktiv ist, wird keine neue gestartet.
        return

    questions = load_questions()
    if not questions:
        logger.error("Keine Fragen verfügbar!")
        return

    # Wähle eine zufällige Frage
    question = random.choice(questions)
    # Die Chat-ID wird als Context übergeben
    chat_id = context.job.data  # In der neuen API kann man "data" für einfache Werte verwenden

    # Erstelle eine Inline-Tastatur mit dem 'Claim'-Button
    keyboard = [[InlineKeyboardButton("Claim", callback_data="claim")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Sende die Frage
    message = await context.bot.send_message(chat_id=chat_id, text=f"Neue Frage: {question}", reply_markup=reply_markup)
    # Pinnen der Frage-Nachricht
    try:
        await context.bot.pin_chat_message(chat_id=chat_id, message_id=message.message_id)
    except Exception as e:
        logger.error("Fehler beim Pinnen: %s", e)

    # Setze den Frage-Runden-Status
    QUESTION_ROUND_ACTIVE = True
    CURRENT_QUESTION_MESSAGE_ID = message.message_id
    CURRENT_QUESTION_CHAT_ID = chat_id
    QUESTION_ROUND_ACTIVITY = {}  # Zurücksetzen der Aktivitätsdaten

    # Plane Reminder-Jobs (Reminder nach 10 und 20 Minuten, d.h. 20 bzw. 10 Minuten verbleibend)
    job_queue = context.job_queue
    reminder1 = job_queue.run_once(reminder_callback, when=10*60, data={"chat_id": chat_id, "time_left": 20})
    reminder2 = job_queue.run_once(reminder_callback, when=20*60, data={"chat_id": chat_id, "time_left": 10})
    REMINDER_JOBS = [reminder1, reminder2]

    # Plane das Ende der Frage-Runde nach 30 Minuten
    job_queue.run_once(end_question_round, when=30*60, data=chat_id)

async def reminder_callback(context: ContextTypes.DEFAULT_TYPE):
    """
    Sendet alle 10 Minuten während der Frage-Runde eine intergalaktische Erinnerung,
    wie viel Zeit noch verbleibt.
    """
    data = context.job.data
    chat_id = data["chat_id"]
    time_left = data["time_left"]

    # Auswahl an coolen, intergalaktischen Reminder-Texten
    messages = [
        f"Intergalaktischer Reminder: Nur noch {time_left} Minuten, bis das Universum sich wandelt!",
        f"XenexAi meldet: {time_left} Minuten verbleibend bis zur galaktischen Antwortrunde!",
        f"Kosmische Warnung: In {time_left} Minuten endet die Frage-Session. Seid bereit!"
    ]
    text = random.choice(messages)
    await context.bot.send_message(chat_id=chat_id, text=text)

async def end_question_round(context: ContextTypes.DEFAULT_TYPE):
    """
    Beendet die Frage-Runde:
    - Entpinnt die Frage
    - Ermittelt den aktivsten User während der Runde und belohnt diesen zufällig mit 100-250 Bonus-Punkten
    - Sendet eine öffentliche Feier-Nachricht
    - Setzt den Frage-Runden-Status zurück und entfernt Reminder-Jobs
    """
    global QUESTION_ROUND_ACTIVE, CURRENT_QUESTION_MESSAGE_ID, CURRENT_QUESTION_CHAT_ID, QUESTION_ROUND_ACTIVITY, REMINDER_JOBS

    chat_id = context.job.data

    # Entpinne die Frage-Nachricht
    try:
        await context.bot.unpin_chat_message(chat_id=chat_id, message_id=CURRENT_QUESTION_MESSAGE_ID)
    except Exception as e:
        logger.error("Unpin fehlgeschlagen: %s", e)

    # Ermittle den aktivsten User der Runde
    if QUESTION_ROUND_ACTIVITY:
        most_active_user = max(QUESTION_ROUND_ACTIVITY, key=QUESTION_ROUND_ACTIVITY.get)
        bonus = random.randint(100, 250)
        points = load_points()
        points[str(most_active_user)] = points.get(str(most_active_user), 0) + bonus
        save_points(points)
        await context.bot.send_message(chat_id=chat_id,
                                 text=f"Glückwunsch an den aktivsten User (ID: {most_active_user})! Du erhältst {bonus} Bonus-Punkte!")
    else:
        await context.bot.send_message(chat_id=chat_id, text="Keine Aktivität in dieser Runde. Nächste Runde startet in einer Stunde!")

    # Rücksetzen des Frage-Runden-Status
    QUESTION_ROUND_ACTIVE = False
    CURRENT_QUESTION_MESSAGE_ID = None
    CURRENT_QUESTION_CHAT_ID = None
    QUESTION_ROUND_ACTIVITY = {}

    # Entferne Reminder-Jobs
    for job in REMINDER_JOBS:
        job.schedule_removal()
    REMINDER_JOBS = []

# --------------------- Message-Handler ---------------------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handler für alle Textnachrichten (ohne Befehle):
    - Während einer Frage-Runde: Zählt er als Aktivität (wird für den Bonus gewertet)
    - Außerhalb der Frage-Runde: Erhält der User 0,5 Punkt pro Nachricht
    """
    global QUESTION_ROUND_ACTIVE, QUESTION_ROUND_ACTIVITY

    user = update.effective_user
    if not user:
        return
    user_id = user.id

    if QUESTION_ROUND_ACTIVE:
        # Erhöhe die Nachrichtenzahl für den User während der Runde
        QUESTION_ROUND_ACTIVITY[user_id] = QUESTION_ROUND_ACTIVITY.get(user_id, 0) + 1
    else:
        # Außerhalb der Runde gibt es 0,5 Punkte pro Nachricht
        points = load_points()
        points[str(user_id)] = points.get(str(user_id), 0) + 0.5
        save_points(points)

# --------------------- Main-Funktion ---------------------
def main():
    """
    Hauptfunktion, die den Bot initialisiert und startet.
    
    NOTES:
    - Wir verwenden jetzt Application.builder() statt Updater.
    - Die JobQueue wird über application.job_queue aufgerufen.
    - Alle Handler-Funktionen sind asynchron (async def) und werden mit await ausgeführt.
    """
    # Ersetze den Platzhalter durch deinen Bot-Token
    TOKEN = "7761649059:AAEQtfHDd1FXeE5wH3rPIyuXzBXnqB4eP94"

    application = Application.builder().token(TOKEN).build()

    # Handler registrieren
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("claim", claim))
    application.add_handler(CallbackQueryHandler(claim_callback, pattern="^claim$"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # JobQueue für die stündliche Frage-Runde einrichten
    job_queue = application.job_queue

    # Gib hier die Chat-ID an, in der der Bot operieren soll
    # ACHTUNG: Ersetze YOUR_CHAT_ID durch die tatsächliche Chat-ID (als Integer)
    chat_id = 100173852517  # z.B. 123456789

    # Starte den Job, der jede Stunde (3600 Sekunden) ausgeführt wird.
    # In der neuen API wird der "data"-Parameter genutzt, um die Chat-ID zu übergeben.
    job_queue.run_repeating(new_question_job, interval=3600, first=0, data=chat_id)

    # Bot starten (Polling)
    application.run_polling()

if __name__ == '__main__':
    main()
