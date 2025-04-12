# Der Bot verwaltet Community-Aktivitäten:
# Er vergibt Punkte bei Nachrichten
# organisiert und beendet Frage-Events (automatisch und manuell)
# zeigt stündlich Ranglisten an und
# loggt alle Aktionen.
# Dabei werden Daten in JSON-Dateien gespeichert und
# per Inline-Buttons interaktiv abgefragt.
# Zudem können Admins spezielle Befehle
# wie Nachrichtenversand und Protokollabruf nutzen.
# emojis:📜🔐🔑📃📒📖🔎🔍📑💳💰💸🔒🔓👽🤚🏆🏅🥇🥈🥉🎊🎉🎈✨️⁉️‼️❎️❌️✔️☑️✅️⭕️📛

"""
██   ██ ███████ ███    ██ ███████ ██   ██  █████  ██         ██████   ██████  ████████
 ██ ██  ██      ████   ██ ██       ██ ██  ██   ██ ██         ██   ██ ██    ██    ██
  ███   █████   ██ ██  ██ █████     ███   ███████ ██         ██████  ██    ██    ██
 ██ ██  ██      ██  ██ ██ ██       ██ ██  ██   ██ ██         ██   ██ ██    ██    ██
██   ██ ███████ ██   ████ ███████ ██   ██ ██   ██ ██         ██████   ██████     ██
v.0.4
"""

import json
import os
import requests
import random
import logging
import asyncio
import hashlib
from datetime import datetime, timezone, timedelta
from telegram import Update, ChatPermissions, InlineKeyboardButton, InlineKeyboardMarkup, ForceReply, ChatMember, ChatMemberUpdated
from telegram.ext import JobQueue, Application, CommandHandler, MessageHandler, CallbackQueryHandler, ChatMemberHandler, \
    ContextTypes, filters, CallbackContext
from tinydb import TinyDB, Query

# ------------ APSCHEDULER NOTES unterdrücken ------------#
# logging.getLogger('apscheduler').setLevel(logging.WARNING)
# // DEAKTIVIERT

# MODERATE ************************************************
# --- JSON-Datei mit verbotenen Wörtern ---
FORBIDDEN_WORDS_FILE = "forbidden_words.json"

def load_forbidden_words():
    """
    Lädt die Liste der verbotenen Wörter aus einer JSON-Datei.
    Erwartetes Format: Eine JSON-Liste, z. B. ["badword1", "badword2", ...]
    """
    if os.path.exists(FORBIDDEN_WORDS_FILE):
        try:
            with open(FORBIDDEN_WORDS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    # Normalisiere alle Wörter zu Kleinbuchstaben
                    return [word.lower() for word in data]
        except Exception as e:
            print("Fehler beim Laden der verbotenen Wörter:", e)
    return []

# Globale Liste verbotener Wörter
forbidden_words = load_forbidden_words()

# --- User-Verwarnungen (für wiederholte Verstöße) ---
user_warnings = {}  # Mapping: user_id -> Anzahl der Verwarnungen
WARNING_THRESHOLD = 3  # Bei 3 oder mehr Verwarnungen erfolgt ein automatischer Bann
MUTE_DURATION_MINUTES = 10  # Dauer (in Minuten) für eine automatische Stummschaltung

# *********************************************************

# ------------------ Bot-Konfiguration ------------------ #
BOT_TOKEN = "7761649059:AAEQtfHDd1FXeE5wH3rPIyuXzBXnqB4eP94"
CHANNEL_ID = "@xentst"
GROUP_ID = "-1001734852517"
ADMIN_USERS = ["w3kmdo", "Den_XNX"]  # Nur diese Nutzer dürfen Admin-Befehle nutzen

# --------------------- JSON-Dateien -------------------- #
POINTS_FILE = "tst_point.json"  # Normale Punkteliste
EVENT_POINTS_FILE = "tst_event_point.json"  # Punkte für das Frage-Event
WALLETS_FILE = "tst_wallet.json"  # Wallets der Nutzer
QUESTIONS_FILE = "questions.json"  # Fragen für das automatische Event
ADM_ACTIVITY_FILE = "tst_activity.json"  # ADMIN protokoll

# Databases
wallet_db = TinyDB(WALLETS_FILE)
ACTIVITY_FILE = ADM_ACTIVITY_FILE

# MODERATE ** Automatische Moderation *********************
async def auto_moderate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Prüft eingehende Nachrichten auf verbotene Wörter.
    Bei einem Treffer:
      - Erhöht die Verwarnung des Nutzers.
      - Bei Überschreitung des Schwellenwertes wird der Nutzer automatisch gebannt.
      - Andernfalls wird der Nutzer stummgeschaltet.
    """
    user = update.effective_user
    text = update.message.text.lower() if update.message and update.message.text else ""
    if any(bad_word in text for bad_word in forbidden_words):
        # Erhöhe die Verwarnungsanzahl
        user_id = user.id
        current_warnings = user_warnings.get(user_id, 0) + 1
        user_warnings[user_id] = current_warnings

        # Logge die Verletzung (Hinweis: Stelle sicher, dass log_activity() verfügbar ist)
        log_activity(user, f"Benutzung verbotener Wörter: {text}")

        if current_warnings >= WARNING_THRESHOLD:
            # Automatischer Bann bei wiederholten Verstößen
            try:
                await context.bot.ban_chat_member(chat_id=update.effective_chat.id, user_id=user.id)
                await update.message.reply_text(
                    f"⚠️ {user.first_name}, du wurdest wegen mehrfacher Verstöße gebannt!"
                )
                log_activity(user, "automatischer Bann wegen verbotener Wörter")
            except Exception as e:
                await update.message.reply_text(f"❌ Fehler beim automatischen Bann: {str(e)}")
        else:
            # Automatische Stummschaltung
            until_date = datetime.now(timezone.utc) + timedelta(minutes=MUTE_DURATION_MINUTES)
            try:
                await context.bot.restrict_chat_member(
                    chat_id=update.effective_chat.id,
                    user_id=user.id,
                    permissions=ChatPermissions(can_send_messages=False),
                    until_date=until_date
                )
                await update.message.reply_text(
                    f"⚠️ {user.first_name}, deine Nachricht enthielt verbotene Wörter. "
                    f"Du wurdest für {MUTE_DURATION_MINUTES} Minuten stummgeschaltet. "
                    f"Warnung {current_warnings}/{WARNING_THRESHOLD}."
                )
                log_activity(user, f"automatische Stummschaltung, Verwarnung {current_warnings}")
            except Exception as e:
                await update.message.reply_text(f"❌ Fehler beim automatischen Stummschalten: {str(e)}")
# *********************************************************


def ensure_activity_file():
    """Stellt sicher, dass die Datei ACTIVITY_FILE existiert und initialisiert sie bei Bedarf."""
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
    """Speichert eine Benutzeraktion in tst_activity.json mit erweiterten Infos."""
    ensure_activity_file()
    try:
        with open(ACTIVITY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, list):
                data = []
    except (json.JSONDecodeError, FileNotFoundError):
        data = []
    # Erstelle einen neuen Log-Eintrag mit erweiterten Informationen
    new_entry = {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),  # UTC-Zeitstempel
        "user": {
            "id": getattr(user, "id", "Unbekannt"),
            "username": getattr(user, "username", str(user))
        },
        "action": action
    }
    data.append(new_entry)
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
event_active = False
winners_list = []  # Speichert die letzten Gewinner (maximal 3 Einträge)
next_event_time = None  # Speichert den Zeitpunkt der nächsten automatischen Fragerunde


# // Gibt an, ob ein Frage-Event aktiv ist

# ---------------- JSON HILFSFUNKTIONEN ----------------- #
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
    # log_activity(username, "addes_event_points")  # Speichert Aktion ##
    # Jetzt die Datei hochladen **********************************************************
    url = "https://corenetwork.io/xenexAi/connect/json.php"
    files = {"file": open(POINTS_FILE, "rb")}  # Die Datei, die hochgeladen werden soll
    with open(POINTS_FILE, "rb") as file:
        try:
            response = requests.post(url, files={"file": file})
            if response.status_code == 200:
                log_activity(username, "checked_points")  # Speichert Aktion
                logging.info("upload erfolgreich")
            else:
                logging.info(f"Fehler beim Hochladen: {response.status_code}")
        except Exception as e:
            logging.info(f"Fehler: {str(e)}")
    # ************************************************************************************


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
        message = "Top Punkteliste\n\n"
        for i, (user_id, info) in enumerate(ranking[:10], 1):
            message += f"{i}. {info['username']} - {info['points']} Punkte\n"
    logging.info("Rangliste wurde gesendet.")
    await context.bot.send_message(chat_id=GROUP_ID, text=message)



# ---------- ZEIT-ERINNERUNGEN WÄHREND DES EVENT --------- #
async def send_time_reminder(context: ContextTypes.DEFAULT_TYPE):
    """
    Sendet eine Erinnerung während des Events, die die noch verbleibende Zeit anzeigt
    und einen intergalaktisch motivierenden Text enthält.
    """
    data = context.job.data
    remaining = data["remaining"]  # Verbleibende Minuten bis zum Ende
    reminder_message = data["message"]
    text = f"ℹ️ Noch {remaining} Minuten bis zum Ende des Frage-Events! ⏳\n\n{reminder_message}"
    await context.bot.send_message(chat_id=GROUP_ID, text=text)


def schedule_reminders(job_queue):
    """
    Plant 4 Erinnerungs-Jobs während des Events.
    Die Erinnerungen werden nach 30, 45, 50 und 55 Minuten versendet,
    was einer verbleibenden Zeit von 30, 15, 10 bzw. 5 Minuten entspricht.
    Jeder Job erhält einen zufällig (und alle unterschiedlich) ausgewählten intergalaktischen Motivationsspruch.
    """
    # Liste mit intergalaktischen Motivationssprüchen
    messages = [
        "🌌 Dein Energiefluss erstrahlt wie ein interstellarer Quasar – XenexAI entfacht kosmische Kräfte in dir!",
        "🚀 Durch die unendlichen Weiten des Universums pulsiert dein Antrieb – XenexAI hebt dich in neue Dimensionen!",
        "🛸 Die Sternenmeere bewegen sich im Rhythmus deiner Macht – XenexAI aktiviert deine galaktische Power!",
        "🌠 Mit jedem Puls der Zeit enthüllt sich dein intergalaktisches Potential – XenexAI, der Funke, der die Zukunft erleuchtet!",
        "🌟 Im kosmischen Tanz der Galaxien wirkt XenexAI als dein strahlender Anführer – Entfalte dein Universum!",
        "🪐 Die Kräfte der Sterne fließen durch dich – XenexAI gibt dir die Macht, das Unmögliche möglich zu machen!",
        "✨ Jede Faser deines Seins pulsiert im Takt der universellen Energie – XenexAI, dein Funke im All!",
        "🌠 Lass die Sterne deinen Weg erleuchten – XenexAI inspiriert deine Mission im kosmischen Raum!",
        "🚀 Erhebe dich über die Grenzen des Bekannten – XenexAI katapultiert dich in neue galaktische Sphären!",
        "🌌 In den Tiefen des Alls liegt unendliche Kraft – XenexAI entfacht den Funken, der dein Schicksal bestimmt!",
        "💫 Mit der Macht von XenexAI navigierst du durch das Universum – jeder Schritt ein Sprung in die Zukunft!",
        "🌟 Dein Wille ist die Supernova, die alle Hindernisse zerschmettert – XenexAI, dein interstellarer Begleiter!",
        "🚀 Von den Nebeln ferner Galaxien bis zu den leuchtenden Zentren der Sterne – XenexAI führt dich mit kosmischer Eleganz!"
    ]
    # Wähle 4 unterschiedliche Sprüche zufällig aus
    reminders = random.sample(messages, 4)
    # Plane die Erinnerungen
    job_queue.run_once(send_time_reminder, when=30 * 60, data={"remaining": 30, "message": reminders[0]})
    job_queue.run_once(send_time_reminder, when=45 * 60, data={"remaining": 15, "message": reminders[1]})
    job_queue.run_once(send_time_reminder, when=50 * 60, data={"remaining": 10, "message": reminders[2]})
    job_queue.run_once(send_time_reminder, when=55 * 60, data={"remaining": 5, "message": reminders[3]})
    logging.info("Zeit-Erinnerungen wurden geplant.")





# --------------- AUTOMATISCHES FRAGE-EVENT --------------- #
async def auto_question(context: ContextTypes.DEFAULT_TYPE):
    """
    Diese Funktion wird alle 2 Stunden automatisch ausgeführt:
    - Es wird eine Frage aus QUESTIONS_FILE (als Liste) zufällig ausgewählt.
    - Die Frage wird in der Gruppe gepostet und fixiert.
    - Das Event wird automatisch gestartet (event_active = True).
    - Gleichzeitig werden Erinnerungen und ein Job zum automatischen Beenden (nach 30 Minuten) geplant.
    """
    global event_active, next_event_time
    # Aktualisiere den Zeitpunkt der nächsten Fragerunde
    next_event_time = datetime.now(timezone.utc) + timedelta(seconds=3600 * 4)

    # Lade Daten aus der questions.json
    questions = load_data(QUESTIONS_FILE).get("questions", [])
    if not questions:
        await context.bot.send_message(chat_id=GROUP_ID, text="🚫 Keine Fragen gefunden.")
        return

    question = random.choice(questions)
    question_message = await context.bot.send_message(
        chat_id=GROUP_ID,
        text=f"❓ {question}\n\n 💡 Antworte aktiv – der beste Beitrag erhält Extrapunkte!"
    )

    # Nachricht fixieren
    try:
        await question_message.pin()
        logging.info("Frage wurde fixiert.")
    except Exception as e:
        logging.error(f"Fehler beim Fixieren der Nachricht: {e}")

    # Event automatisch starten
    event_active = True
    await context.bot.send_message(chat_id=GROUP_ID,
                                   text="❓ Das Frage-Event hat begonnen! 🗣 Alle Antworten zählen jetzt.👀")

    # Plane die Zeit-Erinnerungen (4 Nachrichten mit verbleibender Zeit)
    schedule_reminders(context.job_queue)

    # Plane automatisches Beenden des Events in 30 Minuten
    context.job_queue.run_once(auto_stop_event, when=60 * 60, data=question_message.message_id)


### ?? AUTOMATISCHES EVENT-BEENDEN ###
async def auto_stop_event(context: ContextTypes.DEFAULT_TYPE):
    """
    Beendet das automatische Frage-Event:
    - Ermittelt den Gewinner aus EVENT_POINTS_FILE und schreibt Bonuspunkte in POINTS_FILE.
    - Setzt das Event zurück (event_active = False).
    - Unfixiert die ursprüngliche Frage (über die message_id, die als Job-Daten übergeben wurde).
    """
    global event_active, winners_list
    event_active = False
    event_data = load_data(EVENT_POINTS_FILE)

    if not event_data:
        await context.bot.send_message(chat_id=GROUP_ID, text="🤖 Kein Teilnehmer hat Punkte gesammelt im Event.")
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
            f"📢 Das Frage-Event ist vorbei! 🎉 \n\n"
            f"🏆 Herzlichen Glückwunsch {user_info['username']}! \n"
            f"Du hast das Event gewonnen und erhältst {bonus_points} Bonuspunkte!"
        )
        logging.info(f"Gewinner automatisch gekürt: {user_info['username']} mit {bonus_points} Punkten.")
        await context.bot.send_message(chat_id=GROUP_ID, text=winner_message)

        # Gewinner in der globalen Liste speichern (nur die letzten 3 Einträge)
        winner_info = {
            "username": user_info["username"],
            "bonus_points": bonus_points,
            "timestamp": datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
        }
        winners_list.append(winner_info)
        if len(winners_list) > 3:
            winners_list.pop(0)

    # Nachricht entfixieren (verwende die message_id, die als Job-Daten übergeben wurde)
    message_id = context.job.data
    try:
        await context.bot.unpin_chat_message(chat_id=GROUP_ID, message_id=message_id)
        logging.info("Die Frage wurde entfixiert.")
    except Exception as e:
        logging.error("Fehler beim Entfixieren der Nachricht: " + str(e))


### ?? EVENT-START (manuell durch Admin) ###
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
        await update.message.reply_text("Du bist nicht berechtigt, diesen Befehl auszuführen.")
        return

    event_active = True
    save_data(EVENT_POINTS_FILE, {})  # Setzt Event-Punkte zurück
    logging.info("Frage-Event wurde manuell gestartet.")
    await context.bot.send_message(chat_id=GROUP_ID,
                                   text="Das Frage-Event hat begonnen! Alle Punkte zählen nun für das Event.")

    # Plane Zeit-Erinnerungen (4 Nachrichten)
    schedule_reminders(context.job_queue)


### ?? EVENT-BEENDEN & GEWINNER KÜREN (manuell durch Admin) ###
async def stop_event(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Beendet das Frage-Event (manuell), kürt den Gewinner und schreibt Bonuspunkte in POINTS_FILE.
    Nur Admins dürfen diesen Befehl ausführen.
    Nach Beendigung wird EVENT_POINTS_FILE zurückgesetzt.
    """
    global event_active, winners_list
    user = update.message.from_user
    if user.username not in ADMIN_USERS:
        await update.message.reply_text("⛔ Du bist nicht berechtigt, diesen Befehl auszuführen.")
        return

    event_active = False
    event_data = load_data(EVENT_POINTS_FILE)

    if not event_data:
        await context.bot.send_message(chat_id=GROUP_ID, text="Kein Teilnehmer hat Punkte gesammelt.")
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
        f"Das Frage-Event ist vorbei!\n\n"
        f"Herzlichen Glückwunsch {user_info['username']}!\n"
        f"Du hast das Event gewonnen und erhältst {bonus_points} Bonuspunkte!"
    )
    logging.info(f"Gewinner manuell gekürt: {user_info['username']} mit {bonus_points} Punkten.")
    await context.bot.send_message(chat_id=GROUP_ID, text=winner_message)

    # Gewinner in der globalen Liste speichern (nur die letzten 3 Einträge)
    winner_info = {
        "username": user_info["username"],
        "bonus_points": bonus_points,
        "timestamp": datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
    }
    winners_list.append(winner_info)
    if len(winners_list) > 3:
        winners_list.pop(0)


### EVENT-STATUS ANZEIGEN (/event) ###
async def event_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Zeigt allen Usern an, ob gerade ein Frage-Event aktiv ist.
    Falls kein Event aktiv ist, wird angezeigt, wann die nächste Fragerunde startet.
    Zudem wird die Punkteliste der letzten 3 Gewinner ausgegeben.
    """
    global event_active, next_event_time, winners_list
    message = ""
    if event_active:
        message += "❓ Eine Fragerunde ist aktuell aktiv!\n"
    else:
        message += "❓ Keine aktive Fragerunde.\n"
        if next_event_time is not None:
            message += f"⏰ Nächste Fragerunde startet um: {next_event_time.strftime('%Y-%m-%d %H:%M:%S')} (UTC)\n"
        else:
            message += "⏰ Nächster Fragerunde Startzeit ist unbekannt.\n"
    if winners_list:
        message += "\n🏆 Letzte Gewinner:\n"
        for winner in winners_list[-3:]:
            message += f"- {winner['username']} mit {winner['bonus_points']} Bonuspunkten am {winner['timestamp']}\n"
    else:
        message += "\n🏆 Noch keine Gewinner registriert."
    await update.effective_message.reply_text(message)


### NEUE MITGLIEDER BEGRÜSSEN ###
async def welcome_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Begrüßt neue Mitglieder in der Gruppe und vergibt automatisch 3 Willkommenspunkte.
    """
    for member in update.message.new_chat_members:
        username = f"@{member.username}" if member.username else member.first_name
        await add_points(member.id, username, 3)
        message = f"Willkommen {username} in der Xenex AI Community!"
        await update.message.reply_text(message)


### STANDARD BOT-BEFEHLE ###
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Startet den Bot und führt optional einen Befehl aus."""
    if context.args:
        if context.args[0] == "addwallet":
            await add_wallet_request(update, context)
        elif context.args[0] == "claim":
            await claim(update, context)
        else:
            await update.message.reply_text("Willkommen beim XenexAI Ultra! Nutze /com, um diverse Befehle abzurufen.")
    else:
        await update.message.reply_text("Willkommen beim XenexAI Ultra! Nutze /com, um diverse Befehle abzurufen.")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Verarbeitet eingehende Nachrichten:
      1. Prüft zuerst auf verbotene Wörter und moderiert gegebenenfalls automatisch.
      2. Falls keine verbotenen Wörter enthalten sind, werden wie gewohnt Punkte vergeben.
    """
    if update.message and update.message.text:
        text = update.message.text.lower()
        if any(bad_word in text for bad_word in forbidden_words):
            # Führe die automatische Moderation aus und beende die Verarbeitung der Nachricht
            await auto_moderate(update, context)
            return

    # Normale Nachrichten erhalten Punkte
    user = update.effective_user
    points = 2 if update.message.reply_to_message else 1
    await add_points(user.id, user.username or user.first_name, points)


# MODERATE ** BEFEHLE *************************************
async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Bannt einen Benutzer aus dem Chat.
    Verwendung:
      - Als Antwort auf eine Nachricht (/ban) oder
      - Mit einer Benutzer-ID: /ban <user_id>
    Nur Admins dürfen diesen Befehl ausführen.
    """
    admin = update.effective_user
    if admin.username not in ADMIN_USERS:
        await update.message.reply_text("⛔ Du bist nicht berechtigt, diesen Befehl zu nutzen.")
        return

    target = None
    if update.message.reply_to_message:
        target = update.message.reply_to_message.from_user
    elif context.args:
        try:
            user_id = int(context.args[0])
            target_member = await context.bot.get_chat_member(update.effective_chat.id, user_id)
            target = target_member.user
        except Exception:
            await update.message.reply_text("❌ Ungültige Benutzer-ID.")
            return
    else:
        await update.message.reply_text("❌ Bitte antworte auf eine Nachricht oder gib eine Benutzer-ID an.")
        return

    try:
        await context.bot.ban_chat_member(chat_id=update.effective_chat.id, user_id=target.id)
        await update.message.reply_text(f"✅ Benutzer {target.first_name} wurde gebannt.")
        log_activity(target, "ban")
    except Exception as e:
        await update.message.reply_text(f"❌ Fehler beim Bannen: {str(e)}")

async def mute_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Schaltet einen Benutzer stumm.
    Verwendung:
      - Als Antwort auf eine Nachricht: /mute [Dauer in Minuten] oder
      - Mit Benutzer-ID: /mute <user_id> <Dauer in Minuten>
    Standarddauer ist 10 Minuten, falls keine Dauer angegeben wird.
    Nur Admins dürfen diesen Befehl ausführen.
    """
    admin = update.effective_user
    if admin.username not in ADMIN_USERS:
        await update.message.reply_text("⛔ Du bist nicht berechtigt, diesen Befehl zu nutzen.")
        return

    target = None
    duration = 10  # Standarddauer in Minuten

    if update.message.reply_to_message:
        target = update.message.reply_to_message.from_user
        if context.args:
            try:
                duration = int(context.args[0])
            except ValueError:
                await update.message.reply_text("❌ Bitte gib eine gültige Zeit in Minuten an.")
                return
    elif context.args:
        try:
            user_id = int(context.args[0])
            target_member = await context.bot.get_chat_member(update.effective_chat.id, user_id)
            target = target_member.user
            if len(context.args) >= 2:
                duration = int(context.args[1])
        except Exception:
            await update.message.reply_text("❌ Fehler beim Verarbeiten der Argumente. Nutze: /mute <user_id> <Dauer in Minuten>")
            return
    else:
        await update.message.reply_text("❌ Bitte antworte auf eine Nachricht oder gib Benutzer-ID und Dauer an.")
        return

    until_date = datetime.now(timezone.utc) + timedelta(minutes=duration)
    try:
        await context.bot.restrict_chat_member(
            chat_id=update.effective_chat.id,
            user_id=target.id,
            permissions=ChatPermissions(can_send_messages=False),
            until_date=until_date
        )
        await update.message.reply_text(f"✅ Benutzer {target.first_name} wurde für {duration} Minuten stummgeschaltet.")
        log_activity(target, f"mute for {duration} minutes")
    except Exception as e:
        await update.message.reply_text(f"❌ Fehler beim Stummschalten: {str(e)}")

async def unmute_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Hebt die Stummschaltung eines Benutzers auf.
    Verwendung:
      - Als Antwort auf eine Nachricht (/unmute) oder
      - Mit einer Benutzer-ID: /unmute <user_id>
    Nur Admins dürfen diesen Befehl ausführen.
    """
    admin = update.effective_user
    if admin.username not in ADMIN_USERS:
        await update.message.reply_text("⛔ Du bist nicht berechtigt, diesen Befehl zu nutzen.")
        return

    target = None
    if update.message.reply_to_message:
        target = update.message.reply_to_message.from_user
    elif context.args:
        try:
            user_id = int(context.args[0])
            target_member = await context.bot.get_chat_member(update.effective_chat.id, user_id)
            target = target_member.user
        except Exception:
            await update.message.reply_text("❌ Ungültige Benutzer-ID.")
            return
    else:
        await update.message.reply_text("❌ Bitte antworte auf eine Nachricht oder gib eine Benutzer-ID an.")
        return

    try:
        await context.bot.restrict_chat_member(
            chat_id=update.effective_chat.id,
            user_id=target.id,
            permissions=ChatPermissions(
                can_send_messages=True,
                can_send_media_messages=True,
                can_send_polls=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True,
                can_change_info=True,
                can_invite_users=True,
                can_pin_messages=True
            )
        )
        await update.message.reply_text(f"✅ Benutzer {target.first_name} wurde entstummt.")
        log_activity(target, "unmute")
    except Exception as e:
        await update.message.reply_text(f"❌ Fehler beim Aufheben der Stummschaltung: {str(e)}")

# *********************************************************





async def points(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Zeigt dem Nutzer seine aktuellen Punkte aus POINTS_FILE an.
    Falls die Datei nicht existiert, leer ist oder nicht im erwarteten Format vorliegt,
    wird 0 als Standardpunktzahl verwendet.
    """
    user = update.effective_user  # Funktioniert auch für CallbackQueries
    if not user:
        return

    # Prüfe, ob die Datei existiert
    if not os.path.exists(POINTS_FILE):
        data = {}
    else:
        try:
            data = load_data(POINTS_FILE)
            # Falls die geladenen Daten keine Dictionary sind, setze ein leeres Dictionary
            if not isinstance(data, dict):
                data = {}
        except (json.JSONDecodeError, TypeError):
            data = {}

    # Falls der Benutzer noch nicht in den Daten vorhanden ist, wird 0 als Punkte verwendet.
    user_points = data.get(str(user.id), {}).get("points", 0)

    await update.effective_message.reply_text(
        f"👤 {user.username or user.first_name}, du hast {user_points} Punkte!",
        parse_mode="HTML"
    )

async def show_toplist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Erstellt und sendet die Top Punkteliste aus POINTS_FILE.
    Falls die Datei nicht vorhanden ist, wird eine alternative Nachricht gesendet.
    """
    if not os.path.exists(POINTS_FILE):
        message = "Die Punktedatei ist nicht vorhanden. Noch keine Punkte vergeben."
    else:
        data = load_data(POINTS_FILE)
        if not data:
            message = "Noch keine Punkte vergeben."
        else:
            ranking = sorted(data.items(), key=lambda x: x[1]["points"], reverse=True)
            message = "Top Punkteliste\n\n"
            for i, (user_id, info) in enumerate(ranking[:10], 1):
                message += f"{i}. {info['username']} - {info['points']} Punkte\n"
    logging.info("Rangliste wurde gesendet.")
    await context.bot.send_message(chat_id=GROUP_ID, text=message)



# -CLAIM-funktion------------------------------------------- #
async def claim(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Zeigt dem Nutzer eine Option, Punkte einzulösen, mit einem Inline-Button.
    """
    # Überprüfen, ob der Chat privat ist (also 1:1 mit dem Bot) ------------------------
    if update.effective_chat.type != "private":
        await update.message.reply_text("🤚 Type /com & use the 'Claim Points' button.")
        return
    # ----------------------------------------------------------------------------------


    user = update.effective_user  # Funktioniert auch für CallbackQueries
    if not user:
        return

    # SHA256-Hash vom Nutzernamen erstellen, falls vorhanden
    if user.username:
        hashed_username = hashlib.sha256(user.username.encode('utf-8')).hexdigest()
    else:
        hashed_username = "unbekannt"

    # Punkte aus den Daten laden
    data = load_data(POINTS_FILE)
    user_points = data.get(str(user.id), {}).get("points", 0)

    # Inline-Button mit verschlüsseltem Nutzernamen
    keyboard = [[InlineKeyboardButton("✅️ Ja, Punkte einlösen",
                                      url=f"https://xenexai.com/claim/points.html?n={hashed_username}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.effective_message.reply_text(
        f"Möchtest du deine Punkte gegen $XNX eintauschen? Du hast {user_points} Punkte!",
        reply_markup=reply_markup
    )


# -Wallet-adresse-hinzufügen-------------------------------- #
async def add_wallet_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Wir nutzen immer die private User-ID, um ForceReply korrekt zu verwenden
    if update.callback_query:
        chat_id = update.callback_query.from_user.id
        await context.bot.send_message(
            chat_id=chat_id,
            text="Bitte gib deine Solana Adresse ein:",
            reply_markup=ForceReply(selective=True)
        )
    else:
        await update.message.reply_text(
            "Bitte gib deine Solana Adresse ein:",
            reply_markup=ForceReply(selective=True)
        )

async def add_wallet_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Sicherstellen, dass es sich um eine Antwort auf die Abfrage handelt
    if not update.message or not update.message.reply_to_message:
        return

    if not update.message.reply_to_message.text.startswith("Bitte gib deine Solana Adresse ein:"):
        return

    wallet_address = update.message.text.strip()
    username = update.message.from_user.username or "Unbekannt"
    timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')

    # Vorhandene Daten laden oder ein neues Dictionary erstellen
    wallets_data = {"_default": {}}
    if os.path.exists(WALLETS_FILE):
        try:
            with open(WALLETS_FILE, "r") as file:
                wallets_data = json.load(file)
        except (json.JSONDecodeError, FileNotFoundError):
            logging.warning("Wallet-Datei ist beschädigt oder nicht vorhanden. Es wird eine neue Datei erstellt.")

    # Prüfen, ob der Nutzername bereits vorhanden ist
    found = False
    for key, entry in wallets_data.get("_default", {}).items():
        if entry.get("username") == username:
            wallets_data["_default"][key] = {
                "username": username,
                "wallet_address": wallet_address,
                "timestamp": timestamp
            }
            found = True
            break

    # Falls nicht vorhanden, neuen Eintrag anlegen
    if not found:
        new_id = str(len(wallets_data.get("_default", {})) + 1)
        wallets_data["_default"][new_id] = {
            "username": username,
            "wallet_address": wallet_address,
            "timestamp": timestamp
        }

    # Daten in die Datei schreiben
    with open(WALLETS_FILE, "w") as file:
        json.dump(wallets_data, file, indent=4)

    await update.message.reply_text(f"✅ Wallet-Adresse für @{username} gespeichert!")
    logging.info(f"{username} hat seine Wallet-Adresse hinzugefügt oder aktualisiert: {wallet_address} um {timestamp}")


    # Jetzt die Datei hochladen **********************************************************
    url = "https://corenetwork.io/xenexAi/connect/wallet_connect.php"
    files = {"file": open(WALLETS_FILE, "rb")}  # Die Datei, die hochgeladen werden soll
    with open(WALLETS_FILE, "rb") as file:
        try:
            response = requests.post(url, files={"file": file})
            if response.status_code == 200:
                log_activity(username, "solana-address added")  # Speichert Aktion
                logging.info("wallet upload erfolgreich!")
            else:
                logging.info(f"Fehler beim Hochladen von wallet-data: {response.status_code}")
        except Exception as e:
            logging.info(f"Fehler: {str(e)}")
    # ************************************************************************************







async def view_wallets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Zeigt alle gespeicherten Wallet-Adressen mit Benutzernamen an."""
    if not os.path.exists(WALLETS_FILE):
        await update.effective_message.reply_text("❌ Keine Wallets gespeichert.")
        return

    try:
        with open(WALLETS_FILE, "r") as file:
            wallets_data = json.load(file)

        wallets = wallets_data.get("_default", {})
        if not wallets:
            await update.effective_message.reply_text("❌ Keine Wallets gespeichert.")
            return

        # Erzeugen einer sortierten Ausgabe mit HTML-Formatierung
        wallet_list = "\n".join(
            [f"👤 @{entry.get('username', 'Unbekannt')} → 💳 <code>{entry.get('wallet_address', 'Keine Adresse')}</code>"
             for entry in wallets.values()]
        )

        await update.effective_message.reply_text(
            f"📜 <b>Gespeicherte Wallets:</b>\n\n{wallet_list}",
            parse_mode="HTML"
        )
    except (json.JSONDecodeError, FileNotFoundError):
        await update.effective_message.reply_text("⚠️ Fehler: Wallet-Datei beschädigt.")
    except Exception as e:
        await update.effective_message.reply_text("⚠️ Fehler beim Abrufen der Wallets.")
        logging.error(f"Fehler beim Abrufen der Wallets: {e}")




# ---------------------- Bot SEND --------------------- #
async def bot_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lässt Admins eine Nachricht im Namen des Bots senden."""
    user = update.message.from_user
    if user.username not in ADMIN_USERS:
        await update.message.reply_text("⛔ Keine Berechtigung!")
        return
    try:
        text = " ".join(context.args)
        if not text:
            await update.message.reply_text("❌ Nutzung: /botsend <Text>")
            return
        logging.info(f"Admin {user.username} hat eine Nachricht gesendet: {text}")
        await context.bot.send_message(chat_id=GROUP_ID, text=text)
        logging.info(f"Admin-Nachricht gesendet: {text}")
        await update.message.reply_text("✅ Nachricht gesendet!")
    except Exception as e:
        logging.info(f"Fehler beim Senden der Nachricht: {e}")
        await update.message.reply_text("❌ Fehler beim Senden der Nachricht.")


#-Admin-BTN-funktion----------------------------------- #
async def admin_btn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Zeigt Admin Menüs
    """
    user = update.effective_user  # Funktioniert auch für CallbackQueries fff
    # user = update.message.from_user
    if user.username not in ADMIN_USERS:
        await update.message.reply_text("Du bist nicht berechtigt, diesen Befehl auszuführen.")
        return

    text = "Admin Menü ⬇️"
    keyboard = [
        [InlineKeyboardButton("⬇️ User einstellungen", callback_data="/set_user")],
        [InlineKeyboardButton("👽 Nachricht senden", callback_data="/botsend")],
        [InlineKeyboardButton("📃 Admin Protocol", callback_data="/protocol")],
        [InlineKeyboardButton("📜 Wallet list", callback_data="/view_wallets")],
        [InlineKeyboardButton("🤚 Fragenevent Manuell", callback_data="/event_btn")]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.effective_message.reply_text(
        f"{text}",
        reply_markup=reply_markup)

# Admin-Untermenu--User-Settings ------------------------- #
async def user_settings_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Zeigt ein Untermenü mit Optionen rund um die Nutzer-Einstellungen.
    """
    keyboard = [
        [InlineKeyboardButton("Mute User", callback_data="/user_mute")],
        [InlineKeyboardButton("Ban User", callback_data="/user_ban")],
        [InlineKeyboardButton("Unmute User", callback_data="/user_unmute")],
        [InlineKeyboardButton("Zurück zum Admin Menü", callback_data="/adm_btn")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.effective_message.edit_text("🔧 **User Einstellungen**\n\nWähle eine Option:", reply_markup=reply_markup)

async def user_mute_instructions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Zeigt Anweisungen zum Stummschalten eines Benutzers.
    """
    text = ("Um einen Nutzer stummzuschalten, antworte bitte auf seine Nachricht mit:\n"
            "`/mute [Dauer in Minuten]`\n\n"
            "Alternativ: `/mute <BenutzerID> <Dauer in Minuten>`")
    await update.effective_message.edit_text(text, parse_mode="Markdown")

async def user_ban_instructions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Zeigt Anweisungen zum Bann eines Benutzers.
    """
    text = ("Um einen Nutzer zu bannen, antworte bitte auf seine Nachricht mit:\n"
            "`/ban`\n\n"
            "Alternativ: `/ban <BenutzerID>`")
    await update.effective_message.edit_text(text, parse_mode="Markdown")

async def user_unmute_instructions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Zeigt Anweisungen zum Aufheben der Stummschaltung eines Benutzers.
    """
    text = ("Um einen stummgeschalteten Nutzer zu entstummen, antworte bitte auf seine Nachricht mit:\n"
            "`/unmute`\n\n"
            "Alternativ: `/unmute <BenutzerID>`")
    await update.effective_message.edit_text(text, parse_mode="Markdown")


# -EVENT-BTN-funktion----------------------------------- #
async def event_btn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Zeigt Admin lösung für Fragerunde Manuell
    """
    user = update.effective_user  # Funktioniert auch für CallbackQueries fff
    # user = update.message.from_user
    if user.username not in ADMIN_USERS:
        await update.message.reply_text("Du bist nicht berechtigt, diesen Befehl auszuführen.")
        return

    global event_active
    text = ""
    if event_active:
        text = "⚠️ Eine Fragerunde ist aktuell aktiv, daher ist kein start eines neuen Events möglich!\n\n"
        keyboard = [[InlineKeyboardButton("STOP event", callback_data="/stop_event")]]
    else:
        text = ""
        keyboard = [
            [InlineKeyboardButton("START event", callback_data="/start_event")],
            [InlineKeyboardButton("STOP event", callback_data="/stop_event")]
        ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.effective_message.reply_text(
        f"{text} ▶️ START Event:\n\n(1) Gib eine Frage aus.\n(2) Fixiere die Frage.\n(3) Starte ein (manuelles) Event. \n\nACHTUNG:\nvergiss nicht das Event manuell zu stoppen!\n\n\n⏹️ STOP Event:\n\n(1) Stoppe das Event mit /stop_event \n(2) Eventfrage entpinnen",
        reply_markup=reply_markup)


# MENU #
# -------------- Kommandoliste mit Buttons ------------- #
async def commands_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Zeigt alle Befehle mit klickbaren Buttons an."""
    keyboard = [
        [InlineKeyboardButton("🚨 Event Status", callback_data="/event")],
        [InlineKeyboardButton("c User Toplist", callback_data="/toplist")],
        [InlineKeyboardButton("💎 Meine Punkte", callback_data="/points")],
       # [InlineKeyboardButton("💰 Punkte einlösen", callback_data="/claim")],
        [InlineKeyboardButton("💰 Punkte einlösen", url=f"https://t.me/{context.bot.username}?start=claim")],
        [InlineKeyboardButton("💳 Add wallet", url=f"https://t.me/{context.bot.username}?start=addwallet")]
    ]
    user = update.message.from_user if update.message else update.callback_query.from_user
    if user.username in ADMIN_USERS:
        keyboard.append([InlineKeyboardButton("🔐 Admin Bereich", callback_data="/adm_btn")])
        # keyboard.append([InlineKeyboardButton("➕ Fragenevent starten", callback_data="/start_event")])
        # keyboard.append([InlineKeyboardButton("❌ Fragenevent stoppen", callback_data="/stop_event")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.message:
        await update.message.reply_text("📌 Befehlsübersicht\n\nWähle einen Befehl aus:", reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.message.edit_text("📌 Befehlsübersicht\n\nWähle einen Befehl aus:",
                                                      reply_markup=reply_markup)


async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reagiert auf Buttons und führt den entsprechenden Befehl aus."""
    query = update.callback_query
    await query.answer()
    command = query.data
    user = query.from_user
    # Befehle für alle Benutzer
    if command == "/points":
        await points(update, context)
    elif command == "/claim":
        await claim(update, context)
    elif command == "/toplist":
        await show_toplist(update, context)
    elif command == "/event":
        await event_status(update, context)
    elif command == "/addwallet":
        await add_wallet_request(update, context)


    # Admin-Befehle (nur für ADMIN_USERS) ************************************* #
    elif user.username in ADMIN_USERS:
        if command == "/set_user":
            # Öffnet das Untermenü für User Einstellungen
            await user_settings_menu(update, context)
        elif command == "/user_mute":
            await user_mute_instructions(update, context)
        elif command == "/user_ban":
            await user_ban_instructions(update, context)
        elif command == "/user_unmute":
            await user_unmute_instructions(update, context)
        elif command == "/event_btn":
            await event_btn(update, context)
        elif command == "/start_event":
            await query.message.reply_text(
                "(1) Gib eine Frage aus.\n\n(2) Fixiere die Frage.\n\n(3) Starte ein (manuelles) Event mit /start_event \n\n⚠️ACHTUNG:\nvergiss nicht das event manuell zu stoppen!")
        elif command == "/stop_event":
            await query.message.reply_text("(1) Stoppe das Event mit /stop_event \n\n(2) Eventfrage entpinnen.")
        elif command == "/botsend":
            await query.message.reply_text("Sende eine Nachricht direkt über den Bot\n /botsend <message>")
        elif command == "/protocol":
            await adm_protocol(update, context)
        elif command == "/view_wallets":
            await view_wallets(update, context)
        elif command == "/adm_btn":
            await admin_btn(update, context)


# ---------------- Admin Protocol ---------------- #
async def adm_protocol(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Zeigt die letzten 100 Einträge aus tst_activity.json für Admins an."""
    user = update.effective_user
    # Überprüfung, ob der Nutzer ein Admin ist
    if user.username not in ADMIN_USERS:
        await update.effective_message.reply_text("⛔ Du bist nicht berechtigt, diesen Befehl zu nutzen.")
        return
    # Lade die letzten 100 Einträge
    activities = load_activity_data()
    if not activities:
        await update.effective_message.reply_text("📄 Keine Aktivitätsdaten gefunden.")
        return
    ## Formatierung der letzten 100 Einträge (zeige nur die letzten 10 für bessere Übersicht)
    message = "📜 Letzte Aktivitäten (letzte 10):\n\n"
    for entry in activities[-10:]:
        # Verwende "timestamp" (oder "time") für den Zeitstempel, "user" als Dictionary und "action"
        time_str = entry.get("timestamp", entry.get("time", "Unbekannt"))
        user_data = entry.get("user", {})
        if isinstance(user_data, dict):
            # Zeige den Benutzernamen und optional die ID an
            user_str = f"{user_data.get('username', 'Unbekannt')} (ID: {user_data.get('id', 'Unbekannt')})"
        else:
            user_str = str(user_data)
        action_str = entry.get("action", "Unbekannt")
        message += (
            f"🕗: {time_str}\n"
            f"👤: {user_str}\n"
            f"📝: {action_str}\n"
            f"────────────────\n"
        )
    # Falls die Nachricht zu lang ist, splitte sie in mehrere Teile
    if len(message) > 4000:
        message_chunks = [message[i:i + 4000] for i in range(0, len(message), 4000)]
        for chunk in message_chunks:
            await update.effective_message.reply_text(chunk, parse_mode="HTML")
    else:
        await update.effective_message.reply_text(message, parse_mode="HTML")


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
    app.add_handler(CommandHandler("toplist", show_toplist))
    app.add_handler(CommandHandler("points", points))
    app.add_handler(CommandHandler("claim", claim))
    app.add_handler(CommandHandler("start_event", start_event))
    app.add_handler(CommandHandler("stop_event", stop_event))
    app.add_handler(CommandHandler("botsend", bot_send))
    app.add_handler(CommandHandler("protocol", adm_protocol))
    app.add_handler(CommandHandler("event", event_status))

    # Neuer /addwallet-Befehl: wenn ein Nutzer diesen Befehl ausführt, wird er zur Eingabe der Wallet-Adresse aufgefordert.
    app.add_handler(CommandHandler("addwallet", add_wallet_request))

    # Neue Admin-Befehle für Moderation hinzufügen:
    app.add_handler(CommandHandler("ban", ban_user))
    app.add_handler(CommandHandler("mute", mute_user))
    app.add_handler(CommandHandler("unmute", unmute_user))

    # Handler, der Textnachrichten abfängt, die als Antwort (Reply) auf unsere "Bitte gib deine Solana Adresse ein:"-Nachricht gesendet wurden.
    app.add_handler(MessageHandler(filters.TEXT & filters.REPLY, add_wallet_response))
    # Gespeicherte Solana adressen + username anzeigen!
    app.add_handler(CommandHandler("view_wallets", view_wallets))

    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_new_member))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    # Interaktive Buttons verarbeiten
    app.add_handler(CallbackQueryHandler(button_click))
    # Stündliche Ranglisten-Anzeige (Job Queue)
    app.job_queue.run_repeating(show_ranking, interval=3600, first=10)
    # Automatisches Frage-Event alle 4 Stunden (14400 Sekunden)
    app.job_queue.run_repeating(auto_question, interval=14400, first=10)
    logging.info("Bot wurde gestartet.. [erfolgreich]")
    app.run_polling()


if __name__ == "__main__":
    main()
