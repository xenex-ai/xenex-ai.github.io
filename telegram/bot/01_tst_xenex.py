import os
import random
from datetime import datetime, timedelta
from telegram import Update, ChatMember
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
from tinydb import TinyDB, Query

# Telegram test-Bot Token
BOT_TOKEN = "7761649059:AAEQtfHDd1FXeE5wH3rPIyuXzBXnqB4eP94"
CHANNEL_ID = "@xentst"
GROUP_ID = "-1001734852517"

# Datenbanken
db = TinyDB("tst_rewards.json")
wallet_db = TinyDB("tst_wallets.json")
User = Query()

# Punktesystem-Konfiguration
BASE_POINTS = 2  # Punkte pro Nachricht
BONUS_POINTS = 5  # Extra-Punkte für hohe Aktivität
BONUS_THRESHOLD = 5  # Anzahl der Nachrichten für Bonus
LEADERBOARD_SIZE = 10  # Anzahl der Top-Mitglieder

# Community-Fragen
questions = [
    "🔮 What are your thoughts on AI-driven cryptocurrencies?",
    "💡 How do you see AI improving blockchain technology?",
    "🚀 What’s your opinion on decentralized AI models?",
    "🤖 How can AI help improve cybersecurity in Web3?",
    "🌍 In what ways can AI contribute to sustainability efforts?",
]

# Willkommensnachricht für neue Mitglieder
async def welcome_new_member(update: Update, context: CallbackContext) -> None:
    for member in update.message.new_chat_members:
        username = f"@{member.username}" if member.username else member.first_name
        welcome_message = (
            f"👋 Welcome {username} to the Xenex AI Community! 🚀\n\n"
            "💡 Join discussions, ask questions, and earn rewards!\n\n"
            "📌 Commands: \n"
            "/points - Check your points\n"
            "/leaderboard - See the top members\n"
            "/addwallet <Solana Wallet> - Link your wallet\n\n"
            "🔥 Stay active and earn rewards!\n"
        )
        await update.message.reply_text(welcome_message, parse_mode="Markdown")

# Punkte für Aktivität vergeben
async def reward_activity(update: Update, context: CallbackContext) -> None:
    username = update.message.from_user.username
    if not username:
        return

    user_data = db.search(User.username == username)
    if user_data:
        current_points = user_data[0]["points"]
        message_count = user_data[0]["messages"] + 1
    else:
        current_points = 0
        message_count = 1

    earned_points = BASE_POINTS + (BONUS_POINTS if message_count >= BONUS_THRESHOLD else 0)
    new_total = current_points + earned_points

    if user_data:
        db.update({"points": new_total, "messages": message_count}, User.username == username)
    else:
        db.insert({"username": username, "points": new_total, "messages": message_count})

    print(f"🏆 {username} earned {earned_points} points! Total: {new_total}")

# Punktestand anzeigen
async def show_points(update: Update, context: CallbackContext) -> None:
    username = update.message.from_user.username
    user_data = db.search(User.username == username)

    if user_data:
        total_points = user_data[0]["points"]
        await update.message.reply_text(f"🔹 @{username}, you have {total_points} points!")
    else:
        await update.message.reply_text(f"🔹 @{username}, you haven't earned any points yet.")

# Leaderboard anzeigen
async def show_leaderboard(update: Update, context: CallbackContext) -> None:
    leaderboard = sorted(db.all(), key=lambda x: x["points"], reverse=True)[:LEADERBOARD_SIZE]
    if not leaderboard:
        await update.message.reply_text("🏆 No points have been awarded yet!")
        return

    message = "🏆 Leaderboard 🏆\n"
    for i, user in enumerate(leaderboard, start=1):
        message += f"{i}. @{user['username']} - {user['points']} points\n"

    await update.message.reply_text(message, parse_mode="Markdown")

# Wallet-Adresse speichern
async def add_wallet(update: Update, context: CallbackContext) -> None:
    if len(context.args) < 1:
        await update.message.reply_text("Usage: /addwallet <Solana Wallet Address>")
        return

    wallet_address = context.args[0]
    username = update.message.from_user.username
    if not username:
        await update.message.reply_text("Error: Unable to detect your username.")
        return

w3 kmdo, [18.03.2025 19:45]
wallet_db.upsert({"username": username, "wallet": wallet_address}, User.username == username)
    await update.message.reply_text(f"✅ Wallet for @{username} saved successfully!")

# Manuelles Punkte-Hinzufügen (Nur für Admins)
async def add_points(update: Update, context: CallbackContext) -> None:
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /addpoints <username> <points>")
        return

    admin_id = update.message.from_user.id
    chat = await context.bot.get_chat_member(GROUP_ID, admin_id)

    # Überprüfung: Ist der Nutzer Admin oder höher?
    if chat.status not in [ChatMember.ADMINISTRATOR, ChatMember.OWNER]:
        await update.message.reply_text("⛔ You don't have permission to add points.")
        return

    username = context.args[0].replace("@", "")
    try:
        points_to_add = int(context.args[1])
    except ValueError:
        await update.message.reply_text("⛔ Invalid number of points.")
        return

    user_data = db.search(User.username == username)
    if user_data:
        new_total = user_data[0]["points"] + points_to_add
        db.update({"points": new_total}, User.username == username)
    else:
        new_total = points_to_add
        db.insert({"username": username, "points": new_total, "messages": 0})

    await update.message.reply_text(f"✅ {points_to_add} points added to @{username}. New total: {new_total}.")

# Automatische Community-Fragen posten
async def ask_community_question(context: CallbackContext) -> None:
    question = random.choice(questions)
    await context.bot.send_message(chat_id=CHANNEL_ID, text=f"👽 {question}")

# Bot starten
def main():
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("points", show_points))
    application.add_handler(CommandHandler("leaderboard", show_leaderboard))
    application.add_handler(CommandHandler("addwallet", add_wallet))
    application.add_handler(CommandHandler("addpoints", add_points))  # Neuer Befehl
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_new_member))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, reward_activity))

    # Automatische Fragen alle 6 Stunden
    application.job_queue.run_repeating(ask_community_question, interval=200, first=10)

    print("Bot is running...")
    application.run_polling()

if name == "main":
    main()
