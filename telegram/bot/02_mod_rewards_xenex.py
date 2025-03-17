import os
from telegram import Update, ChatMember, ChatMemberUpdated
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
from telegram.ext import JobQueue
from tinydb import TinyDB, Query
import random
from datetime import datetime, timedelta

# Telegram Bot Token
BOT_TOKEN = "8079204532:AAHNL2AcUIxLxUQGw4JvXEodZNtQ2PWynOAxx"
CHANNEL_ID = "@xenexAi_official"
GROUP_ID = "-1002407420169"

# Databases
db = TinyDB("mod_rewards_xenex.json")
activity_db = TinyDB("mod_activity.json")
wallet_db = TinyDB("wallets.json")
User = Query()
Activity = Query()

# List of allowed admin usernames (only these admins can use /addpoints)
ALLOWED_ADMINS = ["w3kmdo", "Den_XNX"]  # Replace with actual usernames

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
    "🌌 Will AI play a major role in space exploration and resource mining?",
    "🌀 How can XenexAi leverage AI to create a more intuitive and immersive user experience?",
    "🌐 What do you think about the fusion of AI, blockchain, and the metaverse?",
    "⏳ What do you predict for AI and blockchain adoption in the next five years?",
    "How does XenexAi combine AI and blockchain to create a smarter cryptocurrency ecosystem?",
    "How does XenexAi's AI help in predicting cryptocurrency price movements?",
    "In what ways can XenexAi’s AI make decentralized finance (DeFi) more efficient?",
    "How do you think AI could reduce the risks in DeFi projects like XenexAi?",
    "What sets XenexAi apart from other AI-driven blockchain projects in the market?",
    "What role do you think XenexAi’s community will play in shaping the future of the platform?",
    "How important is decentralization in the development of XenexAi’s ecosystem?",
    "How can XenexAi’s AI help enhance transaction speeds and lower costs on the blockchain?",
    "How do you think XenexAi’s tokenomics will influence the adoption of $XNX?",
    "What innovations would you like to see in XenexAi’s AI-powered governance?",
    "How can XenexAi integrate with other blockchain platforms to create a more connected crypto ecosystem?",
    "How do you think XenexAi can improve user experience through AI-driven analytics?",
    "What challenges do you think XenexAi will face in implementing AI on the blockchain?",
    "What do you think about the potential of XenexAi in predicting market trends and risks for investors?",
    "How can XenexAi help improve privacy in blockchain-based applications?",
    "What role do you think XenexAi will play in enhancing the security of decentralized applications (dApps)?",
    "How can XenexAi’s AI prevent fraudulent transactions and malicious activity on the blockchain?",
    "How can XenexAi leverage AI to optimize its token's value and utility in the crypto market?",
    "How does XenexAi plan to ensure scalability as its blockchain grows in users and applications?",
    "What do you think about XenexAi’s approach to integrating AI in governance and decision-making processes?",
    "What are your thoughts on the role of AI in XenexAi’s community-driven innovations?",
    "How do you think XenexAi’s staking and burning mechanisms could impact the $XNX token supply?",
    "How important do you think AI-driven smart contract verification is for the success of XenexAi?",
    "How do you envision XenexAi evolving in the next 5 years?",
    "XenexAi combines the power of Artificial Intelligence and Blockchain technology to create smarter and more efficient crypto solutions.",
    "With AI-powered predictions, XenexAi helps users make informed decisions about cryptocurrency investments and market trends.",
    "XenexAi's decentralized platform focuses on creating a transparent, secure, and scalable environment for blockchain applications.",
    "AI in XenexAi helps reduce risks in decentralized finance (DeFi) by enhancing security, optimizing transactions, and ensuring better compliance.",
    "XenexAi's AI is designed to detect and prevent fraudulent activities, ensuring that blockchain transactions remain secure.",
    "XenexAi is working towards creating an ecosystem where AI can not only predict market movements but also optimize transactions and improve user experience.",
    "XenexAi’s staking and burning mechanisms are designed to enhance the value of $XNX while ensuring the stability of its ecosystem.",
    "With a focus on sustainability, XenexAi leverages energy-efficient blockchain protocols to minimize its environmental impact.",
    "The AI-powered security features of XenexAi ensure that users’ funds and data remain safe in an increasingly digital world.",
    "XenexAi is committed to creating a seamless and immersive user experience by integrating AI across all layers of its blockchain infrastructure.",
    "Through AI-driven analytics, XenexAi offers personalized recommendations to users, improving their engagement and participation in the ecosystem.",
    "XenexAi's approach to cross-chain interoperability ensures that it can work seamlessly with multiple blockchain platforms, expanding its reach and usability.",
    "The goal of XenexAi is to combine the best of blockchain and AI to provide innovative financial solutions for the future."
]

# Welcome new members
async def welcome_new_member(update: Update, context: CallbackContext) -> None:
    for member in update.message.new_chat_members:
        username = f"@{member.username}" if member.username else member.first_name
        welcome_message = (
            f"👋 Welcome {username} to the  Xenex AI Community ! 🚀\n\n"
            "Here, we discuss  AI, Blockchain & Web3 .\n"
            "💡 Join discussions, ask questions, and earn points for your activity!\n\n"
            "📌  Important Commands: \n"
            "/points - Check your current points\n"
            "/addwallet <Solana Wallet> - Link your wallet for rewards\n\n"
            "🔥  Tip : Stay active and earn rewards!\n"
            "Enjoy your time in the community! 🎉"
        )
        await update.message.reply_text(welcome_message, parse_mode="Markdown")

# Check if user is an allowed admin
async def is_allowed_admin(update: Update) -> bool:
    username = update.message.from_user.username
    return username in ALLOWED_ADMINS

# Log moderator activity
def log_activity(username):
    print(f"Logging activity for {username}")  # Debugging log
    activity_db.insert({"username": username, "timestamp": datetime.now().isoformat()})

# Get recent activity count
def get_recent_activity_count(username):
    now = datetime.now()
    timeframe = now - timedelta(hours=1)
    print(f"Checking activities for {username} after {timeframe}")  # Debugging log
    recent_activities = activity_db.search((Activity.username == username) & (Activity.timestamp >= timeframe.isoformat()))
    print(f"Recent activities for {username}: {len(recent_activities)}")  # Debugging log
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
    await context.bot.send_message(chat_id=GROUP_ID, text=f"🏆 @{username} received {total_points} points! Total: {new_points} points.")

# Show leaderboard
async def show_points(update: Update, context: CallbackContext) -> None:
    await send_points_summary(context.bot)

# Send leaderboard
async def send_points_summary(bot):
    leaderboard = sorted(db.all(), key=lambda x: x["points"], reverse=True)
    if not leaderboard:
        await bot.send_message(chat_id=GROUP_ID, text="No points have been awarded yet!")
        return

    message = "🏆  Current Leaderboard  🏆\n"
    for i, user in enumerate(leaderboard[:10], start=1):
        message += f"{i}. @{user['username']} - {user['points']} points\n"

    await bot.send_message(chat_id=GROUP_ID, text=message, parse_mode="Markdown")

# Auto-reward active moderators
async def auto_reward_mods(context: CallbackContext) -> None:
    mods = db.all()
    if not mods:
        print("No mods found in the database.")  # Debugging log
        return

    for mod in mods:
        username = mod["username"]
        activity_count = get_recent_activity_count(username)
        print(f"Activity count for {username}: {activity_count}")  # Debugging log

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
            await context.bot.send_message(chat_id=GROUP_ID, text=f"🎉 @{username} received {reward_points} points for activity! Total: {new_total} points.")
        else:
            print(f"No reward for {username} due to insufficient activity.")  # Debugging log

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

# Poll (interactive survey)
async def ask_poll(context: CallbackContext) -> None:
    questions_for_poll = [
        "What do you think about the future of XenexAi?",
        "How important is AI in the cryptocurrency space?",
        "What improvements would you like to see in XenexAi?",
    ]
    question = random.choice(questions_for_poll)
    await context.bot.send_poll(
        chat_id=GROUP_ID,
        question=question,
        options=["Strongly Agree", "Agree", "Neutral", "Disagree", "Strongly Disagree"],
        is_anonymous=True,
    )

# Bot startup
def main():
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("addpoints", add_points))
    application.add_handler(CommandHandler("points", show_points))
    application.add_handler(CommandHandler("addwallet", add_wallet))
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_new_member))

    # Automatic rewards, polls and community questions
    application.job_queue.run_repeating(auto_reward_mods, interval=7200, first=10)
    application.job_queue.run_repeating(ask_poll, interval=21600, first=10)  # Poll every 6 hours

    print("Bot is running...")
    application.run_polling()

if __name__ == "__main__":
    main()
