import json
import random
import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# Bot-Konfiguration
BOT_TOKEN = "7761649059:AAEQtfHDd1FXeE5wH3rPIyuXzBXnqB4eP94"
CHANNEL_ID = "@xentst"
GROUP_ID = "-1001734852517"
ADMIN_USERS = ["w3kmdo", "den_xnx"]  # Nur diese Nutzer dürfen Admin-Befehle nutzen

# JSON-Dateien für Punkte und Wallets
POINTS_FILE = "tst_point.json"
WALLETS_FILE = "tst_wallet.json"

# Logging
logging.basicConfig(level=logging.INFO)


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


### Bot-Befehle ###
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Begrüßt den Benutzer."""
    await update.message.reply_text("👋 Willkommen beim Xenex AI Community Bot! Nutze /pointlist, um die Rangliste zu sehen.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Vergibt Punkte für Nachrichten."""
    user = update.message.from_user
    points = 1 if random.random() < 0.5 else 2  # 50% Chance für 1 oder 2 Punkte
    await add_points(user.id, user.username or user.first_name, points)

async def pointlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Zeigt die Rangliste an."""
    await show_ranking(context)

async def claim(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fragt, ob der Benutzer Punkte einlösen möchte."""
    user = update.message.from_user
    keyboard = [[InlineKeyboardButton("✅ Ja, Punkte einlösen", url=f"https://xenex-ai.github.io/dev/24_tst_xnx.html?name={user.username}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("💰 Möchtest du deine Punkte gegen $XNX eintauschen?", reply_markup=reply_markup)

async def addpoints(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ermöglicht es Admins, einem Benutzer Punkte zu geben."""
    if update.message.from_user.username not in ADMIN_USERS:
        await update.message.reply_text("⛔ Du hast keine Berechtigung für diesen Befehl.")
        return

    try:
        target_username = context.args[0].replace("@", "")
        points = int(context.args[1])

        data = load_data(POINTS_FILE)
        for user_id, info in data.items():
            if info["username"] == target_username:
                data[user_id]["points"] += points
                save_data(POINTS_FILE, data)
                print(f"🔹 {target_username} hat {points} Punkte erhalten! (Total: {data[user_id]['points']})")
                await update.message.reply_text(f"✅ {target_username} hat {points} Punkte erhalten!")
                return

        await update.message.reply_text("⚠️ Benutzer nicht gefunden.")
    except:
        await update.message.reply_text("❌ Falsche Nutzung. Beispiel: /addpoints @username 10")

async def addwallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Speichert die Solana-Wallet eines Benutzers."""
    try:
        wallet = context.args[0]
        user = update.message.from_user

        wallets = load_data(WALLETS_FILE)
        wallets[str(user.id)] = {"username": user.username or user.first_name, "wallet": wallet}
        save_data(WALLETS_FILE, wallets)

        print(f"💳 {user.username} hat seine Wallet hinzugefügt: {wallet}")
        await update.message.reply_text("✅ Deine Solana-Wallet wurde gespeichert!")
    except:
        await update.message.reply_text("❌ Falsche Nutzung. Beispiel: /addwallet <Solana-Adresse>")

async def sendmessage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ermöglicht Admins, Nachrichten über den Bot in die Gruppe zu senden."""
    if update.message.from_user.username not in ADMIN_USERS:
        await update.message.reply_text("⛔ Du hast keine Berechtigung für diesen Befehl.")
        return

    text = " ".join(context.args)
    if not text:
        await update.message.reply_text("❌ Du musst eine Nachricht eingeben.")
        return

    print(f"📢 Admin-Nachricht: {text}")
    await context.bot.send_message(chat_id=GROUP_ID, text=text)


### Hauptprogramm ###
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # Befehle registrieren
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("pointlist", pointlist))
    app.add_handler(CommandHandler("claim", claim))
    app.add_handler(CommandHandler("addpoints", addpoints))
    app.add_handler(CommandHandler("addwallet", addwallet))
    app.add_handler(CommandHandler("sendmessage", sendmessage))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Stündliche Ranglisten-Anzeige
    app.job_queue.run_repeating(show_ranking, interval=3600, first=10)

    # Bot starten
    print("🤖 Bot läuft...")
    app.run_polling()


if __name__ == "__main__":
    main()
