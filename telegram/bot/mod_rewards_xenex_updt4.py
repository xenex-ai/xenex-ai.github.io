import os
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackContext
from tinydb import TinyDB, Query
import random
from datetime import datetime, timedelta

# Telegram Bot Token aus der Umgebungsvariablen
BOT_TOKEN = "8079204532:AAHNL2AcUIxLxUQGw4JvXEodZNtQ2PWynOAXX"  # Stelle sicher, dass der Token als Umgebungsvariable gesetzt ist
CHANNEL_ID = "@xenexAi_official"
GROUP_ID = "-1002407420169"  # Ersetze mit deiner Gruppen-ID

# Datenbanken
db = TinyDB("mod_rewards_xenex.json")
activity_db = TinyDB("mod_activity.json")
wallet_db = TinyDB("wallets.json")
User = Query()
Activity = Query()

# Fragen für die Community
questions = [
    "🔮 What are your thoughts on the future of AI-driven cryptocurrencies?",
    "💡 How do you see AI improving blockchain technology in the next five years?",
    "🚀 What’s your opinion on decentralized AI models? Are they the future?",
    "🤖 How can AI help improve cybersecurity in Web3?",
    "🌍 In what ways can AI contribute to global sustainability efforts?",
    "🔗 Should blockchain projects integrate AI to stay competitive?",
    "💰 How do you think AI could influence crypto trading strategies?",
    "📉 What risks do you see in using AI for financial decision-making?",
    "🎭 Can AI-generated content become a new form of digital art ownership?",
    "🌌 Will AI play a major role in space exploration and resource mining?"
]

# Funktion, um Moderator-Aktivitäten zu protokollieren
def log_activity(username):
    activity_db.insert({"username": username, "timestamp": datetime.now().isoformat()})

# Funktion, um Aktivitäten der letzten 60 Minuten zu berechnen
def get_recent_activity_count(username):
    now = datetime.now()
    timeframe = now - timedelta(hours=1)
    recent_activities = activity_db.search((Activity.username == username) & (Activity.timestamp >= timeframe.isoformat()))
    return len(recent_activities)

# Funktion, um Punkte manuell hinzuzufügen
async def add_points(update: Update, context: CallbackContext) -> None:
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /addpoints <@username> <points>")
        return

    username = context.args[0].replace("@", "")
    try:
        points = int(context.args[1])
    except ValueError:
        await update.message.reply_text("Please enter a valid number of points.")
        return

    # Logge Aktivität
    log_activity(username)

    # Aktivitätsbasierte Punktesystem
    activity_count = get_recent_activity_count(username)
    bonus_points = 5 if activity_count > 5 else 2 if activity_count > 2 else 0
    total_points = points + bonus_points

    user_data = db.search(User.username == username)
    if user_data:
        new_points = user_data[0]["points"] + total_points
        db.update({"points": new_points}, User.username == username)
    else:
        new_points = total_points
        db.insert({"username": username, "points": total_points})

    await update.message.reply_text(f"✅ {total_points} points (including bonus) awarded to @{username}! Total: {new_points} points.")
    await context.bot.send_message(chat_id=GROUP_ID, text=f"🏆 @{username} received **{total_points} points**! Total: {new_points} points.")

# Funktion, um den Leaderboard anzuzeigen
async def show_points(update: Update, context: CallbackContext) -> None:
    await send_points_summary(context.bot)

# Funktion, um automatisch die Punkteliste an die Gruppe zu senden
async def send_points_summary(bot):
    leaderboard = sorted(db.all(), key=lambda x: x["points"], reverse=True)
    if not leaderboard:
        await bot.send_message(chat_id=GROUP_ID, text="No points have been awarded yet!")
        return

    message = "🏆 **Current Leaderboard** 🏆\n"
    for i, user in enumerate(leaderboard[:10], start=1):
        message += f"{i}. @{user['username']} - {user['points']} points\n"

    await bot.send_message(chat_id=GROUP_ID, text=message, parse_mode="Markdown")

# Funktion, um automatisch Moderatoren basierend auf Aktivitäten zu belohnen (alle 2 Std)
async def auto_reward_mods(context: CallbackContext) -> None:
    mods = db.all()
    if not mods:
        return

    for mod in mods:
        username = mod["username"]
        activity_count = get_recent_activity_count(username)
        
        # Belohnung basierend auf der Aktivitätsstufe
        if activity_count > 5:
            reward_points = 10
        elif activity_count > 2:
            reward_points = 5
        elif activity_count > 0:
            reward_points = 1
        else:
            reward_points = 0  # Keine Aktivität, keine Belohnung

        if reward_points > 0:
            new_total = mod["points"] + reward_points
            db.update({"points": new_total}, User.username == username)
            await context.bot.send_message(chat_id=GROUP_ID, text=f"🎉 @{username} received **{reward_points} points** for activity! Total: {new_total} points.")

# Funktion, um eine Community-Frage zu stellen (alle 3 Stunden, wenn keine Aktivität war)
async def ask_question(context: CallbackContext) -> None:
    now = datetime.now()
    timeframe = now - timedelta(hours=3)
    recent_activities = activity_db.search(Activity.timestamp >= timeframe.isoformat())

    if not recent_activities:
        question = random.choice(questions)
        await context.bot.send_message(chat_id=CHANNEL_ID, text=f"👽 {question}")

# Funktion, um Solana Wallet hinzuzufügen
async def add_wallet(update: Update, context: CallbackContext) -> None:
    if len(context.args) < 1:
        await update.message.reply_text("Usage: /addwallet <Solana Wallet Address>")
        return

    wallet_address = context.args[0]

    # Überprüfen, ob die Wallet-Adresse bereits existiert
    user_data = db.search(User.username == update.message.from_user.username)
    if user_data:
        username = user_data[0]["username"]
        wallet_db.update({"wallet_address": wallet_address}, User.username == username)
        await update.message.reply_text(f"✅ Wallet address for @{username} saved successfully!")
    else:
        await update.message.reply_text("User not found in database. Please ensure you're registered first.")

# Bot-Startfunktion
def main():
    application = Application.builder().token(BOT_TOKEN).build()

    # Befehle registrieren
    application.add_handler(CommandHandler("addpoints", add_points))
    application.add_handler(CommandHandler("points", show_points))
    application.add_handler(CommandHandler("addwallet", add_wallet))

    # Automatische Belohnungen alle 2 Stunden (unverändert)
    application.job_queue.run_repeating(auto_reward_mods, interval=7200, first=10)

    # Automatische Fragen alle 3 Stunden, wenn keine Aktivität
    application.job_queue.run_repeating(ask_question, interval=10800, first=10)

    # Leaderboard-Update alle 4 Stunden
    application.job_queue.run_repeating(lambda context: send_points_summary(context.bot), interval=14400, first=20)

    print("Bot is running...")
    application.run_polling()

if __name__ == "__main__":
    main()

