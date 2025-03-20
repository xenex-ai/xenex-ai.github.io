import json
import random
import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ChatMemberHandler, filters, ContextTypes

# Bot-Konfiguration
BOT_TOKEN = "7761649059:AAEQtfHDd1FXeE5wH3rPIyuXzBXnqB4eP94"
CHANNEL_ID = "@xentst"
GROUP_ID = "-1001734852517"
ADMIN_USERS = ["w3kmdo", "den_xnx"]  # Nur diese Nutzer dürfen Admin-Befehle nutzen

# JSON-Dateien für Punkte und Wallets
POINTS_FILE = "tst_point.json"
WALLETS_FILE = "tst_wallet.json"

# Logging anpassen (keine HTTP-Requests mehr anzeigen)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)

### Hilfsfunktionen ###
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

async def add_points(user_id, username, points):
    """Fügt Punkte für einen Benutzer hinzu."""
    data = load_data(POINTS_FILE)
    
    if str(user_id) not in data:
        data[str(user_id)] = {"username": username, "points": 0}
    
    data[str(user_id)]["points"] += points
    save_data(POINTS_FILE, data)
    print(f"✅ {username} hat {points} Punkte erhalten! (Total: {data[str(user_id)]['points']})")

async def show_ranking(context: ContextTypes.DEFAULT_TYPE):
    """Zeigt jede Stunde die Rangliste an."""
    data = load_data(POINTS_FILE)
    
    if not data:
        message = "📊 Noch keine Punkte vergeben."
    else:
        ranking = sorted(data.items(), key=lambda x: x[1]["points"], reverse=True)
        message = "🏆 **Top Punkteliste** 🏆\n\n"
        for i, (user_id, info) in enumerate(ranking[:10], 1):
            message += f"{i}. {info['username']} - {info['points']} Punkte\n"
    
    print(message)
    await context.bot.send_message(chat_id=GROUP_ID, text=message)

### Begrüßung für neue Mitglieder ###
async def welcome_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Begrüßt neue Benutzer in der Gruppe und gibt 3 Punkte."""
    for member in update.message.new_chat_members:
        username = f"@{member.username}" if member.username else member.first_name
        welcome_message = (
            f"👋 Willkommen {username} in der Xenex AI Community! 🚀\n\n"
            "Hier diskutieren wir über AI, Blockchain & Web3.\n"
            "💡 Sei aktiv, stelle Fragen und sammle Punkte für deine Teilnahme!\n\n"
            "📌 Wichtige Befehle:\n"
            "/points - Zeigt deine aktuellen Punkte an\n"
            "/addwallet <Solana Wallet> - Verknüpfe deine Wallet für Belohnungen\n\n"
            "🔥 Tipp: Bleib aktiv und verdiene Belohnungen!\n"
            "Viel Spaß in der Community! 🎉"
        )
        print(f"👋 Neuer Benutzer: {username} wurde begrüßt und erhält 3 Punkte.")
        await add_points(member.id, username, 3)
        await update.message.reply_text(welcome_message)

### Bot-Befehle ###
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Begrüßt den Benutzer."""
    await update.message.reply_text("👋 Willkommen beim Xenex AI Community Bot! Nutze /points, um die Rangliste zu sehen.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Vergibt Punkte basierend auf der Nachricht."""
    user = update.message.from_user
    if update.message.reply_to_message:
        points = 2  # Antwort auf eine Nachricht gibt 2 Punkte
    else:
        points = 1  # Normale Nachricht gibt 1 Punkt
    await add_points(user.id, user.username or user.first_name, points)

async def points(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Zeigt die Rangliste und persönliche Punkte an."""
    user = update.message.from_user
    data = load_data(POINTS_FILE)
    user_points = data.get(str(user.id), {}).get("points", 0)

    message = f"🏅 **{user.username or user.first_name}, du hast {user_points} Punkte!**\n"
    
    keyboard = [[InlineKeyboardButton("ℹ️ So funktioniert’s", url="https://xenex-ai.github.io/dev/24_tst_xnx.html?name=test")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(message, reply_markup=reply_markup)

async def claim(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fragt, ob der Benutzer Punkte einlösen möchte."""
    user = update.message.from_user
    keyboard = [[InlineKeyboardButton("✅ Ja, Punkte einlösen", url=f"https://xenex-ai.github.io/dev/24_tst_xnx.html?name={user.username}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("💰 Möchtest du deine Punkte gegen $XNX eintauschen?", reply_markup=reply_markup)

### Hauptprogramm ###
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # Befehle registrieren
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("points", points))  # /points statt /pointlist
    app.add_handler(CommandHandler("claim", claim))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_new_member))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Stündliche Ranglisten-Anzeige
    app.job_queue.run_repeating(show_ranking, interval=3600, first=10)

    # Bot starten
    print("🤖 Bot läuft...")
    app.run_polling()


if __name__ == "__main__":
    main()
