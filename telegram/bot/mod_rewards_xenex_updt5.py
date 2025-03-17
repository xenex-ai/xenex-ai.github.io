import os
from telegram import Update, ChatMember, ChatMemberUpdated
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
from tinydb import TinyDB, Query
import random
from datetime import datetime, timedelta

# Telegram Bot Token
BOT_TOKEN = "8079204532:AAHNL2AcUIxLxUQGw4JvXEodZNtQ2PWynOAXX"
CHANNEL_ID = "@xenexAi_official"
GROUP_ID = "-1002407420169"

# Databases
db = TinyDB("mod_rewards_xenex.json")
activity_db = TinyDB("mod_activity.json")
wallet_db = TinyDB("wallets.json")
User = Query()
Activity = Query()

# List of allowed admin usernames (only these admins can use /addpoints)
ALLOWED_ADMINS = ["admin_username1", "admin_username2"]  # Replace with actual usernames

# Community Questions
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

# Welcome new members
async def welcome_new_member(update: Update, context: CallbackContext) -> None:
    for member in update.message.new_chat_members:
        username = f"@{member.username}" if member.username else member.first_name
        welcome_message = (
            f"👋 Welcome {username} to the **Xenex AI Community**! 🚀\n\n"
            "Here, we discuss **AI, Blockchain & Web3**.\n"
            "💡 Join discussions, ask questions, and earn points for your activity!\n\n"
            "📌 **Important Commands:**\n"
            "/points - Check your current points\n"
            "/addwallet <Solana Wallet> - Link your wallet for rewards\n\n"
            "🔥 **Tip**: Stay active and earn rewards!\n"
            "Enjoy your time in the community! 🎉"
        )
        await update.message.reply_text(welcome_message, parse_mode="Markdown")

# Check if user is an allowed admin
async def is_allowed_admin(update: Update) -> bool:
    username = update.message.from_user.username
    return username in ALLOWED_ADMINS

# Log moderator activity
def log_activity(username):
    activity_db.insert({"username": username, "timestamp": datetime.now().isoformat()})

# Get recent activity count
def get_recent_activity_count(username):
    now = datetime.now()
    timeframe = now - timedelta(hours=1)
    recent_activities = activity_db.search((Activity.username == username) & (Activity.timestamp >= timeframe.isoformat()))
    return len(recent_activities)

# Add points (Only for specific admins)
async def add_points(update: Update, context: CallbackContext) -> None:
    if not await is_allowed_admin(update):
        await update.message.reply_text("❌ You don't have permission to use this command.")
        return

    if len(context.args) < 2:
        await update.message.reply_text("Usage: /addpoints <@username> <points>")
        return

    username = context.args[0].replace("@", "")
    try:
        points = int(context.args[1])
    except ValueError:
        await update.message.reply_text("Please enter a valid number of points.")
        return

    log_activity(username)
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

# Show leaderboard
async def show_points(update: Update, context: CallbackContext) -> None:
    await send_points_summary(context.bot)

# Send leaderboard
async def send_points_summary(bot):
    leaderboard = sorted(db.all(), key=lambda x: x["points"], reverse=True)
    if not leaderboard:
        await bot.send_message(chat_id=GROUP_ID, text="No points have been awarded yet!")
        return

    message = "🏆 **Current Leaderboard** 🏆\n"
    for i, user in enumerate(leaderboard[:10], start=1):
        message += f"{i}. @{user['username']} - {user['points']} points\n"

    await bot.send_message(chat_id=GROUP_ID, text=message, parse_mode="Markdown")

# Auto-reward active moderators
async def auto_reward_mods(context: CallbackContext) -> None:
    mods = db.all()
    if not mods:
        return

    for mod in mods:
        username = mod["username"]
        activity_count = get_recent_activity_count(username)

        if activity_count > 5:
            reward_points = 10
        elif activity_count > 2:
            reward_points = 5
        elif activity_count > 0:
            reward_points = 1
        else:
            reward_points = 0  

        if reward_points > 0:
            new_total = mod["points"] + reward_points
            db.update({"points": new_total}, User.username == username)
            await context.bot.send_message(chat_id=GROUP_ID, text=f"🎉 @{username} received **{reward_points} points** for activity! Total: {new_total} points.")

# Ask community questions
async def ask_question(context: CallbackContext) -> None:
    now = datetime.now()
    timeframe = now - timedelta(hours=3)
    recent_activities = activity_db.search(Activity.timestamp >= timeframe.isoformat())

    if not recent_activities:
        question = random.choice(questions)
        await context.bot.send_message(chat_id=CHANNEL_ID, text=f"👽 {question}")

# Add wallet
async def add_wallet(update: Update, context: CallbackContext) -> None:
    if len(context.args) < 1:
        await update.message.reply_text("Usage: /addwallet <Solana Wallet Address>")
        return

    wallet_address = context.args[0]
    user_data = db.search(User.username == update.message.from_user.username)
    
    if user_data:
        username = user_data[0]["username"]
        wallet_db.update({"wallet_address": wallet_address}, User.username == username)
        await update.message.reply_text(f"✅ Wallet address for @{username} saved successfully!")
    else:
        await update.message.reply_text("User not found in database. Please ensure you're registered first.")

# Bot startup
def main():
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("addpoints", add_points))
    application.add_handler(CommandHandler("points", show_points))
    application.add_handler(CommandHandler("addwallet", add_wallet))
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_new_member))

    application.run_polling()

if __name__ == "__main__":
    main()
