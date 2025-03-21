import json
import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ChatMemberHandler, filters, ContextTypes

# Bot-Konfiguration
BOT_TOKEN = "7761649059:AAEQtfHDd1FXeE5wH3rPIyuXzBXnqB4eP94"
CHANNEL_ID = "@xentst"
GROUP_ID = "-1001734852517"
ADMIN_USERS = ["w3kmdo", "den_xnx"]  # Nur diese Nutzer dürfen Admin-Befehle nutzen

# JSON-Dateien
POINTS_FILE = "tst_point.json"
WALLETS_FILE = "tst_wallet.json"

# Logging konfigurieren
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

async def update_points(username, points, remove=False):
    """Fügt Punkte hinzu oder entfernt sie."""
    data = load_data(POINTS_FILE)
    
    for user_id, info in data.items():
        if info["username"] == username:
            if remove:
                data[user_id]["points"] = max(0, data[user_id]["points"] - points)
                action = "entfernt"
            else:
                data[user_id]["points"] += points
                action = "hinzugefügt"
            save_data(POINTS_FILE, data)
            logging.info(f"✅ {points} Punkte wurden von {username} {action}. (Total: {data[user_id]['points']})")
            return True
    return False

async def update_wallet(username, solana_wallet):
    """Speichert die Solana-Wallet eines Benutzers."""
    data = load_data(WALLETS_FILE)
    data[username] = solana_wallet
    save_data(WALLETS_FILE, data)
    logging.info(f"✅ Wallet für {username} gespeichert: {solana_wallet}")

### Begrüßung neuer Mitglieder ###
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
        await update_points(member.username, 3)
        await update.message.reply_text(welcome_message)

### Befehle ###
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reagiert auf /start mit optionalem Parameter."""
    user = update.message.from_user
    args = context.args  # Liest Parameter nach /start
    
    if args:
        command = args[0]  # Der erste Parameter (z.B. removepoints_test_5)
        parts = command.split("_")

        if len(parts) == 3 and parts[0] in ["removepoints", "addpoints"]:
            target_username = parts[1]
            points = int(parts[2])
            remove = parts[0] == "removepoints"

            if await update_points(target_username, points, remove):
                action_text = "entfernt" if remove else "hinzugefügt"
                await update.message.reply_text(f"✅ {points} Punkte wurden von {target_username} {action_text}!")
            else:
                await update.message.reply_text("⚠️ Benutzer nicht gefunden.")
        
        elif len(parts) == 3 and parts[0] == "setwallet":
            username = parts[1]
            wallet = parts[2]
            await update_wallet(username, wallet)
            await update.message.reply_text(f"✅ Wallet für {username} gespeichert!")

        else:
            await update.message.reply_text(f"🔹 Unbekannter Befehl: {command}")
    
    else:
        await update.message.reply_text("👋 Willkommen! Nutze /points, um deine Punkte zu sehen.")

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
    app.add_handler(CommandHandler("points", points))
    app.add_handler(CommandHandler("claim", claim))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_new_member))

    # Bot starten
    logging.info("🤖 Bot läuft...")
    app.run_polling()

if __name__ == "__main__":
    main()
