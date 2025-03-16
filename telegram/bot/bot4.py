import random
import asyncio
import nest_asyncio
from telegram import Bot
from telegram.constants import ParseMode
from telegram.ext import Application, ApplicationBuilder

# 🔹 Activate nest_asyncio to correctly nest the event loop inside Termux
nest_asyncio.apply()

# 🔹 Insert Bot Tokens here (5 Bots)
BOT_TOKENS = [
    "7761649059:AAEQtfHDd1FXeE5wH3rPIyuXzBXnqB4eP94", 
    "823556168:AAExXQu7T_-olKcPkcm5sJ8Z0DDmYKC7GbE", 
    "880924640:AAHIKIvNOhj-un88fcUjq9HWoZLM_LsmBwA", 
    "709844911:AAGk_lrbNtpsIhH2BMZ-ucoPTUvvFJVMiF0", 
    "861490265:AAEkvp5xPixQ42fyb2_DArPxVhUuY2zvuj4"
]

# 🔹 Create Telegram Bot instances for 5 bots
async def send_message(bot: Bot):
    messages = [
    "Welcome to the XenexAi community! 🚀",
    "Staking for $XNX is coming soon – get ready! 💰",
    "Got any questions about XenexAi? Ask them here! 💬",
    "The XenexAi ecosystem is growing rapidly! 🌱",
    "Join us on this exciting journey! 🌍",
    "Did you know that $XNX will be available for staking soon? 🔥",
    "XenexAi is revolutionizing the future of blockchain technology! 🔮",
    "XenexAi is all about transparency and innovation. 🌟",
    "We're building the future of decentralized finance! 🔗",
    "Are you ready for the next big thing in crypto? 🪙",
    "XenexAi is growing every day. Be part of it! 📈",
    "The $XNX presale is coming soon. Stay informed! 📅",
    "Don't miss out on the opportunity to be a part of XenexAi! 🔥",
    "Have you checked out our latest updates? XenexAi is evolving! 💡",
    "Exciting things are happening at XenexAi. What do you think? 🚀",
    "Mass adoption is the goal! Are you in? 💎",
    "Big things are coming for XenexAi! Stay tuned. 🎯",
    "XenexAi will redefine the blockchain space! Get ready! ⚡",
    "Decentralization is the future. XenexAi is leading the way! 🏆",
    "Your support fuels XenexAi's success! 🚀",
    "The $XNX token is more than just a cryptocurrency—it's a movement! 💥",
    "What do you love most about XenexAi? Share your thoughts! 🗣️",
    "Long-term holders will be rewarded! Are you one of them? 🏦",
    "We are stronger together! Let’s push XenexAi to the moon! 🌕",
    "XenexAi isn't just a project, it's a revolution! 🔄",
    "Join the discussion! What excites you most about XenexAi? 💬",
    "Innovation never stops at XenexAi. 🚀",
    "Crypto moves fast—so does XenexAi! Stay ahead of the curve. 📊",
    "New partnerships coming soon! Who do you think it will be? 🔥",
    "Utility + Community = XenexAi! Let’s build the future! 🏗️",
    "The roadmap is clear. The vision is strong. XenexAi is unstoppable! 🌍",
    "If you're not staking, you're missing out! $XNX rewards are coming! 💰",
    "The presale is your chance to get in early. Don’t wait! ⏳",
    "Join the future of AI-driven crypto with XenexAi! 🤖",
    "Crypto whales are watching XenexAi. Are you? 🐋",
    "Why settle for ordinary when you can be part of something extraordinary? 🚀",
    "The countdown to XenexAi dominance has begun! ⏱️",
    "Which exchange do you want to see $XNX listed on first? 📈",
    "The community makes XenexAi stronger every day! 🔥",
    "If you're reading this, you're early! 🥇",
    "What’s your $XNX price prediction? Let’s discuss! 📊",
    "Bullish on XenexAi? Drop a 🚀 in the chat!",
    "New milestones are being achieved daily! Stay tuned for updates! 📢",
    "The revolution of decentralized AI is here. XenexAi leads the way! 💡",
    "Crypto isn’t just about gains, it’s about freedom! XenexAi delivers both! 🔗",
    "Dream big, build bigger—XenexAi is just getting started! 🏗️",
    "What would you like to see in the next XenexAi update? 💭",
    "$XNX holders are the real winners! Are you one of them? 🏆",
    "Every new member makes the community stronger! Welcome to XenexAi! 💙",
    "Your participation is what makes XenexAi unstoppable! 💪",
    "The metaverse, AI, and blockchain—XenexAi connects them all! 🌐",
    "Early adopters always win. Are you one of them? 🚀",
    "XenexAi is built for the future. Are you ready? 🔥",
    "We’re not just building a project, we’re building an empire! 👑",
    "A new era of crypto is coming. XenexAi is leading the charge! ⚡",
    "We’re setting new standards in DeFi. Join the movement! 💪",
    "Think long-term. Think XenexAi. 💎",
    "What would you do if $XNX hit $10? 🤔",
    "XenexAi isn’t just another project—it’s the future! 🌍",
    "Are you accumulating $XNX before the next big pump? 📈",
    "Crypto is a marathon, not a sprint. Stay strong, XenexAi believers! 🏃",
    "If you're reading this, you're already ahead of 99% of the world! 🚀",
    "XenexAi is about to break new records. Be part of history! 📜",
    "Are you staking your $XNX or holding? What’s your strategy? 🏦",
    "AI + Crypto = The perfect combination! XenexAi delivers both! 🤖",
    "This is just the beginning. The best is yet to come! 🎉",
    "What makes you most excited about XenexAi? Drop your thoughts below! 💬",
    "FOMO is real! Get in before it’s too late! ⏳",
    "XenexAi is bringing something unique to the market. Watch closely! 👀",
    "The foundation is solid. Now it’s time for liftoff! 🚀",
    "Trust the process. The vision is clear. XenexAi is unstoppable! 🏆",
    "Crypto is evolving, and XenexAi is at the forefront of this evolution! 🌍",
    "AI-driven financial freedom is the future! XenexAi is leading the way! 💡",
    "This is more than a project, it’s a movement! Join us now! 💎",
    "We don’t just talk about change—we build it! Welcome to XenexAi! 🏗️",
    "The $XNX community is growing stronger every day! 💪",
    "HODL tight! The best is yet to come! 📈",
    "Which crypto project do you think XenexAi should partner with? 🤝",
    "Big partnerships in the works! Who do you think it will be? 🔥",
    "XenexAi is bringing true utility to the crypto space. Are you ready? 💡",
    "What do you think about XenexAi’s long-term potential? 🚀",
    "Success doesn’t happen overnight, but we’re building something massive! 🌍",
    "The journey is just beginning. Thanks for being part of it! ❤️",
    "Every great movement starts with a community. Let’s grow together! 💪",
    "It’s not just about money, it’s about innovation! XenexAi is leading! 🚀",
    "What’s your dream price target for $XNX? Let’s manifest it! 🔥",
    "Blockchain technology is evolving, and XenexAi is at the heart of it! 🔗",
    "You are still early! Let’s make history together! ⏳",
    "The only way is up! Let’s push XenexAi to new heights! 📈"
] 
    message = random.choice(messages)
    try:
        # Send message to a group (replace with your own chat ID)
        await bot.send_message(chat_id="@xentst", text=message, parse_mode=ParseMode.MARKDOWN)
        print(f"✅ Sent by {bot.username}: {message}")
    except Exception as e:
        print(f"⚠️ Error sending from {bot.username}: {e}")

# 🔹 Function to send a message to each bot, with different delays
async def message_loop(app: Application, delay: int):
    await app.initialize()  # Initialize the application and the bot
    bot = app.bot  # Get the bot instance after initialization
    
    while True:
        await send_message(bot)
        await asyncio.sleep(delay)  # Wait for the specified time (e.g., random delay)

# 🔹 Start the Telegram Bot
async def start_bot():
    print("🚀 All bots are running...")

    # Start the message loop for all bots, with different delays
    tasks = []
    for idx, token in enumerate(BOT_TOKENS):
        app = ApplicationBuilder().token(token).build()
        # Random or sequential delay
        delay = random.randint(10, 20) + idx * 5  # Different delays for each bot
        tasks.append(message_loop(app, delay))
    
    # Wait for all bots to run
    await asyncio.gather(*tasks)

# 🔹 **Fix for Termux: Start event loop correctly**
def run_async():
    try:
        loop = asyncio.get_running_loop()
        print("🔄 Running event loop detected. Starting all bots as tasks...")
        loop.create_task(start_bot())  # Start as a task
    except RuntimeError:
        print("🆕 No running event loop found. Starting a new one...")
        asyncio.run(start_bot())  # Create a new event loop

# 🔹 Start all bots
run_async()

