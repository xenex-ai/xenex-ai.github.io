import json
import random
import logging
import asyncio
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackContext, filters, ContextTypes

# Bot-Konfiguration
BOT_TOKEN = "DEIN_BOT_TOKEN"
CHANNEL_ID = "@xentst"
GROUP_ID = "-1001734852517"
ADMIN_USERS = ["w3kmdo", "den_xnx"]

# JSON-Dateien
POINTS_FILE = "tst_point.json"
WALLETS_FILE = "tst_wallet.json"
QUESTIONS_FILE = "../json/questions.json"

# Logging einrichten
logging.basicConfig(level=logging.INFO, format="%(asctime)s - [%(levelname)s] %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)

# Level-Bereiche
LEVELS = {
    1: 0,
    2: 50,
    3: 150,
    4: 300,
    5: 500
}

# Hilfsfunktionen
def log_action(action):
    """Loggt Aktionen mit Zeitstempel."""
    logging.info(action)

def load_data(file):
    """Lädt Daten aus einer JSON-Datei."""
    try:
        with open(file, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_data(file, data):
    """Speichert Daten in eine JSON-Datei."""
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

def get_user_level(points):
    """Ermittelt das Level basierend auf den Punkten."""
    for level, required_points in sorted(LEVELS.items(), reverse=True):
        if points >= required_points:
            return level
    return 1

async def add_points(user_id, username, points):
    """Fügt Punkte hinzu und speichert sie."""
    data = load_data(POINTS_FILE)

    if str(user_id) not in data:
        data[str(user_id)] = {"username": username, "points": 0, "last_bonus": None}

    data[str(user_id)]["points"] += points
    save_data(POINTS_FILE, data)
    log_action(f"🎉 {username} hat sich {points} Punkte verdient! Gesamtpunkte: {data[str(user_id)]['points']}")

async def show_ranking(context: CallbackContext):
    """Zeigt die Rangliste der Top 10 Benutzer."""
    data = load_data(POINTS_FILE)
    if not data:
        message = "📊 Noch keine Punkte vergeben! Wirst du der Erste sein?"
    else:
        ranking = sorted(data.items(), key=lambda x: x[1]["points"], reverse=True)
        message = "🏆 **Top Punkteliste** 🏆\n\nDie besten Spieler unserer Community:\n"
        for i, (user_id, info) in enumerate(ranking[:10], 1):
            level = get_user_level(info["points"])
            message += f"{i}. {info['username']} – {info['points']} Punkte (Level {level})\n"

    log_action("📢 Rangliste wurde erfolgreich gesendet!")
    await context.bot.send_message(chat_id=GROUP_ID, text=message)

# Automatische Fragen-Funktion
async def post_random_question(context: CallbackContext):
    """Postet alle 3 Stunden eine zufällige Frage aus questions.json."""
    questions = load_data(QUESTIONS_FILE).get("questions", [])
    if questions:
        question = random.choice(questions)
        await context.bot.send_message(chat_id=GROUP_ID, text=f"❓ **Frage der Stunde**: {question}")
        log_action(f"📢 Neue Frage gepostet: {question}")

# Neue Mitglieder begrüßen
async def greet_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Begrüßt neue Mitglieder, die dem Chat beitreten."""
    if update.message.new_chat_members:
        for member in update.message.new_chat_members:
            welcome_text = f"🌟 Willkommen in der Xenex AI Community, {member.first_name}! Wir freuen uns, dass du hier bist! 🚀\n" \
                           f"Nutze /pointlist, um dich mit den besten Spielern der Community zu messen und vielleicht bald an der Spitze der Rangliste zu stehen! 💪"
            await context.bot.send_message(chat_id=update.effective_chat.id, text=welcome_text)
            log_action(f"👋 Begrüßung an {member.first_name} gesendet – der neue Star der Community!")

# Befehle
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Begrüßt den Benutzer."""
    log_action(f"👤 {update.message.from_user.username} hat /start verwendet.")
    await update.message.reply_text("👋 Willkommen beim Xenex AI Community Bot!\n\n"
                                   "Hier kannst du Punkte sammeln und tolle Belohnungen erhalten!\n\n"
                                   "Nutze /pointlist, um die Rangliste der besten Spieler zu sehen und /claim, um deine Punkte gegen XNX zu tauschen. 🚀")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Vergibt zufällig 1-2 Punkte für Nachrichten."""
    user = update.message.from_user
    points = random.choice([1, 2])
    await add_points(user.id, user.username or user.first_name, points)

async def pointlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Zeigt die Punkteliste."""
    log_action(f"👤 {update.message.from_user.username} hat /pointlist aufgerufen.")
    await show_ranking(context)

async def claim(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lässt Benutzer Punkte gegen XNX eintauschen."""
    user = update.message.from_user
    keyboard = [[InlineKeyboardButton("✅ Ja, Punkte einlösen", url=f"https://xenex-ai.github.io/dev/24_tst_xnx.html?name={user.username}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    log_action(f"🔄 {user.username} möchte Punkte gegen XNX einlösen.")
    await update.message.reply_text("💰 Möchtest du deine hart verdienten Punkte gegen $XNX eintauschen? "
                                    "Klicke auf den Button, um deinen Wunsch zu erfüllen! 🚀", reply_markup=reply_markup)

async def addpoints(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ermöglicht Admins, Punkte zu vergeben."""
    if update.message.from_user.username not in ADMIN_USERS:
        await update.message.reply_text("⛔ Du hast keine Berechtigung, diesen Befehl zu verwenden.")
        return

    try:
        target_username = context.args[0].replace("@", "")
        points = int(context.args[1])
        data = load_data(POINTS_FILE)

        for user_id, info in data.items():
            if info["username"] == target_username:
                data[user_id]["points"] += points
                save_data(POINTS_FILE, data)
                log_action(f"🔹 {target_username} hat {points} Punkte erhalten! (Gesamt: {data[user_id]['points']})")
                await update.message.reply_text(f"✅ {target_username} hat erfolgreich {points} Punkte erhalten! 🎉")
                return

        await update.message.reply_text("⚠️ Benutzer nicht gefunden. Bitte überprüfe den Benutzernamen.")
    except:
        await update.message.reply_text("❌ Falsche Eingabe! Nutze: /addpoints @username 10")

async def message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lässt Admins eine Nachricht im Namen des Bots senden."""
    if update.message.from_user.username not in ADMIN_USERS:
        await update.message.reply_text("⛔ Du hast keine Berechtigung, diesen Befehl zu verwenden.")
        return

    try:
        text = " ".join(context.args)
        if not text:
            await update.message.reply_text("❌ Falsche Eingabe! Nutze: /message <Text>")
            return

        log_action(f"📢 Admin {update.message.from_user.username} hat eine Nachricht gesendet: {text}")
        await context.bot.send_message(chat_id=GROUP_ID, text=text)
    except:
        await update.message.reply_text("❌ Fehler beim Senden der Nachricht. Bitte versuche es später.")

# Hauptprogramm
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # Registriere Befehle
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("pointlist", pointlist))
    app.add_handler(CommandHandler("claim", claim))
    app.add_handler(CommandHandler("addpoints", addpoints))
    app.add_handler(CommandHandler("message", message))

    # Registriere den Handler für neue Mitglieder
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, greet_new_member))

    # Registriere den Handler für normale Nachrichten
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Wiederholte Jobs starten
    app.job_queue.run_repeating(show_ranking, interval=3600, first=10)
    app.job_queue.run_repeating(post_random_question, interval=10800, first=30)  # Alle 3 Stunden eine Frage

    log_action("🤖 Der Xenex AI Community Bot ist gestartet! 🚀")
    app.run_polling()

if __name__ == "__main__":
    main()
