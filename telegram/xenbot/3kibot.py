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
ADMIN_USERS = ["w3kmdo", "Den_XNX"]  # Nur diese Nutzer dürfen Admin-Befehle nutzen

### 📂 JSON-DATEIEN ###
POINTS_FILE = "tst_point.json"           # Normale Punkteliste
EVENT_POINTS_FILE = "tst_event_point.json" # Punkte für das Frage-Event
WALLETS_FILE = "tst_wallet.json"          # Wallets der Nutzer

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
    - Falls ein Event aktiv ist, werden die Punkte in EVENT_POINTS_FILE gespeichert.
    - Ansonsten werden die Punkte in POINTS_FILE gespeichert.
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

### 🚀 EVENT-START ###
async def start_event(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Startet ein Frage-Event.
    Nur Admins (definiert in ADMIN_USERS) dürfen diesen Befehl ausführen.
    Während des Events werden Punkte in EVENT_POINTS_FILE gespeichert.
    """
    global event_active
    user = update.message.from_user
    if user.username not in ADMIN_USERS:
        await update.message.reply_text("❌ Du bist nicht berechtigt, diesen Befehl auszuführen.")
        return
    
    event_active = True
    save_data(EVENT_POINTS_FILE, {})  # Setzt Event-Punkte zurück
    logging.info("🎉 Frage-Event wurde gestartet.")
    await context.bot.send_message(GROUP_ID, "🎉 Das Frage-Event hat begonnen! Alle Punkte zählen nun für das Event.")

### 🏁 EVENT-BEENDEN & GEWINNER KÜREN (STOP EVENT) ###
async def stop_event(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Beendet das Frage-Event, kürt den Gewinner und schreibt Bonuspunkte in POINTS_FILE.
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
        await context.bot.send_message(GROUP_ID, "❌ Kein Teilnehmer hat Punkte gesammelt.")
        return

    # Gewinner ermitteln: Nutzer mit den meisten Event-Punkten
    winner = max(event_data.items(), key=lambda x: x[1]["points"])
    user_id, user_info = winner
    bonus_points = random.randint(100, 250)

    # Bonuspunkte auf das Hauptkonto gutschreiben (POINTS_FILE)
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
    logging.info(f"🏆 Gewinner gekürt: {user_info['username']} mit {bonus_points} Punkten.")
    await context.bot.send_message(GROUP_ID, winner_message)

### 👋 NEUE MITGLIEDER BEGRÜSSEN ###
async def welcome_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Begrüßt neue Mitglieder in der Gruppe und vergibt automatisch 3 Punkte.
    """
    for member in update.message.new_chat_members:
        username = f"@{member.username}" if member.username else member.first_name
        # Willkommenspunkte vergeben
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
    Zusätzlich wird die stündliche Ranglistenanzeige geplant.
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

    logging.info("🤖 Bot läuft...")
    app.run_polling()

if __name__ == "__main__":
    main()
