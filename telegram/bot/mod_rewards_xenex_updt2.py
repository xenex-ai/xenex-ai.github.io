from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackContext
from tinydb import TinyDB, Query
import random
from datetime import datetime, timedelta

# Telegram Bot Token
BOT_TOKEN = "8079204532:AAHNL2AcUIxLxUQGw4JvXEodZNtQ2PWynOA"
CHANNEL_ID = "@xenexAi_official"
GROUP_ID = "-1002407420169"  # Ersetze mit deiner Gruppen-ID

# Datenbanken
db = TinyDB("mod_rewards_xenex.json")
activity_db = TinyDB("mod_activity.json")
User = Query()
Activity = Query()

# Fragen für die Community
questions = [
   "🔮 What are your thoughts on the future of AI-driven cryptocurrencies?",
    "🚀 How do you think XenexAi can revolutionize the crypto market?",
    "🛠️ What features would you like to see in XenexAi's ecosystem?",
    "🤖 How do you imagine the role of AI in decentralized finance (DeFi)?",
    "🌍 What would make you more engaged with the XenexAi community?",
    "⚡ What is the biggest challenge you see in the AI and blockchain industry?",
    "🔐 How can AI improve the security of blockchain networks?",
    "📲 What role do you think AI will play in the development of decentralized applications (dApps)?",
    "🔗 How do you see the integration of AI in existing cryptocurrencies and blockchain platforms?",
    "🎯 What would you suggest to make XenexAi more user-friendly?",
    "🚀 What are some exciting innovations you're hoping to see in the crypto space?",
    "📊 What is your opinion on the potential of AI in predicting market trends in the crypto world?",
    "🕵️‍♂️ How do you think AI and blockchain can work together to enhance privacy and data protection?",
    "💡 Do you think AI-driven tokens like $XNX will become mainstream in the future? Why or why not?",
    "🤝 How important is community engagement for the success of a cryptocurrency project?",
    "⚖️ What are your thoughts on the ethical implications of AI in crypto?",
    "🌠 What do you think is the next big trend in AI and blockchain integration?",
    "⚙️ What impact do you think AI can have on the scalability of blockchain networks?",
    "🌟 How can XenexAi differentiate itself from other AI-driven blockchain projects?",
    "💎 In your opinion, what is the most promising use case for AI in the cryptocurrency market?",
    "🛡️ How can AI enhance fraud detection and risk management in the crypto space?",
    "🏦 What do you think about AI-powered automated trading systems?",
    "📈 Can AI help reduce market manipulation and increase transparency in the crypto world?",
    "🧠 How can XenexAi’s AI adapt to market conditions and optimize user experience?",
    "🔥 What innovative staking and burning mechanisms would you like to see in XenexAi?",
    "🛰️ How do you think AI can improve smart contract auditing and security?",
    "🚦 Will AI play a crucial role in regulatory compliance for blockchain projects?",
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

# Function to log moderator activity
def log_activity(username):
    activity_db.insert({"username": username, "timestamp": datetime.now().isoformat()})

# Function to calculate activity in the last 60 minutes
def get_recent_activity_count(username):
    now = datetime.now()
    timeframe = now - timedelta(hours=1)
    recent_activities = activity_db.search((Activity.username == username) & (Activity.timestamp >= timeframe.isoformat()))
    return len(recent_activities)

# Function to manually add points
async def add_points(update: Update, context: CallbackContext) -> None:
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /addpoints <@username> <points>")
        return

    username = context.args[0].replace("@", "")
    points = int(context.args[1])

    # Log activity
    log_activity(username)

    # Activity-based point system
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

# Function to display the leaderboard
async def show_points(update: Update, context: CallbackContext) -> None:
    leaderboard = sorted(db.all(), key=lambda x: x["points"], reverse=True)
    if not leaderboard:
        await update.message.reply_text("No points have been awarded yet!")
        return

    message = "🏆 Top Moderators 🏆\n"
    for i, user in enumerate(leaderboard[:10], start=1):
        message += f"{i}. @{user['username']} - {user['points']} points\n"

    await update.message.reply_text(message, parse_mode="Markdown")

# Function to automatically reward moderators based on activity
async def auto_reward_mods(context: CallbackContext) -> None:
    mods = db.all()
    if not mods:
        return

    for mod in mods:
        username = mod["username"]
        activity_count = get_recent_activity_count(username)
        
        # Reward points based on activity level
        if activity_count > 5:
            reward_points = 10
        elif activity_count > 2:
            reward_points = 5
        elif activity_count > 0:
            reward_points = 1
        else:
            reward_points = 0  # No activity, no reward

        if reward_points > 0:
            new_total = mod["points"] + reward_points
            db.update({"points": new_total}, User.username == username)
            await context.bot.send_message(chat_id=GROUP_ID, text=f"🎉 @{username} received **{reward_points} points** for activity! Total: {new_total} points.")

# Function to ask a community question
async def ask_question(context: CallbackContext) -> None:
    question = random.choice(questions)
    await context.bot.send_message(chat_id=CHANNEL_ID, text=f"👽 {question}")

# Bot startup function
def main():
    application = Application.builder().token(BOT_TOKEN).build()

    # Register commands
    application.add_handler(CommandHandler("addpoints", add_points))
    application.add_handler(CommandHandler("points", show_points))

    # Automatic rewards and community questions
    application.job_queue.run_repeating(auto_reward_mods, interval=7500, first=10)
    application.job_queue.run_repeating(ask_question, interval=7200, first=10)

    print("Bot is running...")
    application.run_polling()

if __name__ == "__main__":
    main()


