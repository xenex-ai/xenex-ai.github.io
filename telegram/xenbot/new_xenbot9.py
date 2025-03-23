import logging
import json
import random
import os
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, CallbackQueryHandler

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

def start(update: Update, context: CallbackContext):
    """Begrüßt den User und informiert über den Bot."""
    update.message.reply_text("Hallo! Jede Stunde wird eine Frage gestellt. Viel Spaß und Erfolg!")

def claim(update: Update, context: CallbackContext):
    """
    CommandHandler: Liefert den Claim-Link, der den aktuellen Punktewert und den Usernamen enthält.
    Alternativ kann auch der Inline-Button genutzt werden.
    """
    user = update.effective_user
    points = load_points()
    user_points = points.get(str(user.id), 0)
    username = user.username if user.username else user.first_name
    url = f"https://xenex-ai.github.io/dev/27_tst_xnx.html?address={user_points}&name={username}"
    update.message.reply_text(f"Hier ist dein Claim-Link:\n{url}")

def claim_callback(update: Update, context: CallbackContext):
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
    query.answer()
    query.edit_message_text(text=f"Claim-Link:\n{url}")

def new_question_job(context: CallbackContext):
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
    chat_id = context.job.context  # Hier wird als Kontext die Chat-ID übergeben

    # Erstelle eine Inline-Tastatur mit dem 'Claim'-Button
    keyboard = [[InlineKeyboardButton("Claim", callback_data="claim")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Sende die Frage
    message = context.bot.send_message(chat_id=chat_id, text=f"Neue Frage: {question}", reply_markup=reply_markup)
    # Pinnen der Frage-Nachricht
    context.bot.pin_chat_message(chat_id=chat_id, message_id=message.message_id)

    # Setze den Frage-Runden-Status
    QUESTION_ROUND_ACTIVE = True
    CURRENT_QUESTION_MESSAGE_ID = message.message_id
    CURRENT_QUESTION_CHAT_ID = chat_id
    QUESTION_ROUND_ACTIVITY = {}  # Zurücksetzen der Aktivitätsdaten

    # Plane Reminder-Jobs (Reminder nach 10 und 20 Minuten, d.h. 20 bzw. 10 Minuten verbleibend)
    job_queue = context.job_queue
    reminder1 = job_queue.run_once(reminder_callback, 10*60, context={"chat_id": chat_id, "time_left":20})
    reminder2 = job_queue.run_once(reminder_callback, 20*60, context={"chat_id": chat_id, "time_left":10})
    REMINDER_JOBS = [reminder1, reminder2]

    # Plane das Ende der Frage-Runde nach 30 Minuten
    job_queue.run_once(end_question_round, 30*60, context=chat_id)

def reminder_callback(context: CallbackContext):
    """
    Sendet alle 10 Minuten während der Frage-Runde eine intergalaktische Erinnerung,
    wie viel Zeit noch verbleibt.
    """
    data = context.job.context
    chat_id = data["chat_id"]
    time_left = data["time_left"]

    # Auswahl an coolen, intergalaktischen Reminder-Texten
    messages = [
        f"Intergalaktischer Reminder: Nur noch {time_left} Minuten, bis das Universum sich wandelt!",
        f"XenexAi meldet: {time_left} Minuten verbleibend bis zur galaktischen Antwortrunde!",
        f"Kosmische Warnung: In {time_left} Minuten endet die Frage-Session. Seid bereit!"
    ]
    text = random.choice(messages)
    context.bot.send_message(chat_id=chat_id, text=text)

def end_question_round(context: CallbackContext):
    """
    Beendet die Frage-Runde:
    - Entpinnt die Frage
    - Ermittelt den aktivsten User während der Runde und belohnt diesen zufällig mit 100-250 Bonus-Punkten
    - Sendet eine öffentliche Feier-Nachricht
    - Setzt den Frage-Runden-Status zurück und entfernt Reminder-Jobs
    """
    global QUESTION_ROUND_ACTIVE, CURRENT_QUESTION_MESSAGE_ID, CURRENT_QUESTION_CHAT_ID, QUESTION_ROUND_ACTIVITY, REMINDER_JOBS

    chat_id = context.job.context

    # Entpinne die Frage-Nachricht
    try:
        context.bot.unpin_chat_message(chat_id=chat_id, message_id=CURRENT_QUESTION_MESSAGE_ID)
    except Exception as e:
        logger.error("Unpin fehlgeschlagen: %s", e)

    # Ermittle den aktivsten User der Runde
    if QUESTION_ROUND_ACTIVITY:
        most_active_user = max(QUESTION_ROUND_ACTIVITY, key=QUESTION_ROUND_ACTIVITY.get)
        bonus = random.randint(100, 250)
        points = load_points()
        points[str(most_active_user)] = points.get(str(most_active_user), 0) + bonus
        save_points(points)
        context.bot.send_message(chat_id=chat_id,
                                 text=f"Glückwunsch an den aktivsten User (ID: {most_active_user})! Du erhältst {bonus} Bonus-Punkte!")
    else:
        context.bot.send_message(chat_id=chat_id, text="Keine Aktivität in dieser Runde. Nächste Runde startet in einer Stunde!")

    # Rücksetzen des Frage-Runden-Status
    QUESTION_ROUND_ACTIVE = False
    CURRENT_QUESTION_MESSAGE_ID = None
    CURRENT_QUESTION_CHAT_ID = None
    QUESTION_ROUND_ACTIVITY = {}

    # Entferne Reminder-Jobs
    for job in REMINDER_JOBS:
        job.schedule_removal()
    REMINDER_JOBS = []

def handle_message(update: Update, context: CallbackContext):
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

def main():
    """Hauptfunktion, die den Bot initialisiert und startet."""
    # Ersetze den Platzhalter durch deinen Bot-Token
    TOKEN = "7761649059:AAEQtfHDd1FXeE5wH3rPIyuXzBXnqB4eP94"

    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    # Handler registrieren
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("claim", claim))
    dp.add_handler(CallbackQueryHandler(claim_callback, pattern="^claim$"))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

    # JobQueue für die stündliche Frage-Runde einrichten
    job_queue = updater.job_queue

    # Gib hier die Chat-ID an, in der der Bot operieren soll
    # ACHTUNG: Ersetze YOUR_CHAT_ID durch die tatsächliche Chat-ID (als Integer)
    chat_id = 100173852517  # z.B. 123456789

    # Starte den Job, der jede Stunde (3600 Sekunden) ausgeführt wird.
    job_queue.run_repeating(new_question_job, interval=3600, first=0, context=chat_id)

    # Bot starten
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
