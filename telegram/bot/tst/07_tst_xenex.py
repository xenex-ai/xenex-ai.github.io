import json
import random
import logging
import asyncio
from datetime import datetime, timedelta
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
    log_action(f"✅ {username} erhielt {points} Punkte! (Total: {data[str(user_id)]['points']})")

async def show_ranking(context: CallbackContext):
    """Zeigt die Rangliste der Top 10 Benutzer."""
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

# Befehle
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Begrüßt den Benutzer."""
    log_action(f"👤 {update.message.from_user.username} hat /start verwendet.")
    await update.message.reply_text("👋 Willkommen beim Xenex AI Community Bot! Nutze /pointlist, um die Rangliste zu sehen.")

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
    log_action(f"🔄 {user.username} möchte Punkte einlösen.")
    await update.message.reply_text("💰 Möchtest du deine Punkte gegen $XNX eintauschen?", reply_markup=reply_markup)

async def addpoints(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ermöglicht Admins, Punkte zu vergeben."""
    if update.message.from_user.username not in ADMIN_USERS:
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
    except:
        await update.message.reply_text("❌ Nutzung: /addpoints @username 10")

async def addwallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Speichert die Wallet eines Benutzers."""
    try:
        wallet = context.args[0]
        user = update.message.from_user
        wallets = load_data(WALLETS_FILE)
        wallets[str(user.id)] = {"username": user.username or user.first_name, "wallet": wallet}
        save_data(WALLETS_FILE, wallets)
        log_action(f"💳 {user.username} hat eine Wallet hinzugefügt: {wallet}")
        await update.message.reply_text("✅ Deine Solana-Wallet wurde gespeichert!")
    except:
        await update.message.reply_text("❌ Nutzung: /addwallet <Solana-Adresse>")

async def dailybonus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gibt aktiven Nutzern einen täglichen Bonus."""
    user = update.message.from_user
    data = load_data(POINTS_FILE)
    user_data = data.get(str(user.id), {"username": user.username, "points": 0, "last_bonus": None})

    last_bonus = user_data.get("last_bonus")
    today = datetime.now().strftime("%Y-%m-%d")

    if last_bonus == today:
        await update.message.reply_text("🎁 Du hast deinen täglichen Bonus bereits abgeholt!")
        return

    bonus = random.randint(5, 15)
    user_data["points"] += bonus
    user_data["last_bonus"] = today
    data[str(user.id)] = user_data
    save_data(POINTS_FILE, data)

    log_action(f"🎁 {user.username} erhielt {bonus} Punkte als täglichen Bonus!")
    await update.message.reply_text(f"✅ Du hast {bonus} Bonuspunkte erhalten!")

# Hauptprogramm
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("pointlist", pointlist))
    app.add_handler(CommandHandler("claim", claim))
    app.add_handler(CommandHandler("addpoints", addpoints))
    app.add_handler(CommandHandler("addwallet", addwallet))
    app.add_handler(CommandHandler("dailybonus", dailybonus))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.job_queue.run_repeating(show_ranking, interval=3600, first=10)

    log_action("🤖 Bot gestartet!")
    app.run_polling()

if __name__ == "__main__":
    main()
