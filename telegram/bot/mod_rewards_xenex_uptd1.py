from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackContext
from tinydb import TinyDB, Query
import random
from datetime import datetime, timedelta

# Telegram Bot Token
BOT_TOKEN = "8079204532:AAI..."
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
    # ... (restliche Fragen)
]

# Funktion zum Protokollieren von Aktivitäten
def log_activity(username):
    activity_db.insert({"username": username, "timestamp": datetime.now().isoformat()})

# Funktion zur Berechnung der Aktivität in den letzten 60 Minuten
def get_recent_activity_count(username):
    now = datetime.now()
    timeframe = now - timedelta(hours=1)
    recent_activities = activity_db.search((Activity.username == username) & (Activity.timestamp >= timeframe.isoformat()))
    return len(recent_activities)

# Funktion zum manuellen Hinzufügen von Punkten
async def add_points(update: Update, context: CallbackContext) -> None:
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /addpoints <@username> <points>")
        return

    username = context.args[0].replace("@", "")
    points = int(context.args[1])

    # Aktivität protokollieren
    log_activity(username)

    # Aktivitätsbasiertes Punktesystem
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

    await update.message.reply_text(f"✅ {total_points} points (inkl. Bonus) an @{username} vergeben! Gesamt: {new_points} Punkte.")
    await context.bot.send_message(chat_id=GROUP_ID, text=f"🏆 @{username} erhielt **{total_points} Punkte**! Gesamt: {new_points} Punkte.")

# Funktion zur Anzeige des Punktestandes
async def show_points(update: Update, context: CallbackContext) -> None:
    leaderboard = sorted(db.all(), key=lambda x: x["points"], reverse=True)
    if not leaderboard:
        await update.message.reply_text("Noch keine Punkte vergeben!")
        return

    message = "**🏆 Top Moderatoren 🏆**\n"
    for i, user in enumerate(leaderboard[:10], start=1):
        message += f"{i}. @{user['username']} - {user['points']} Punkte\n"

    await update.message.reply_text(message, parse_mode="Markdown")

# Automatische Punktevergabe basierend auf Aktivität
async def auto_reward_mods(context: CallbackContext) -> None:
    mods = db.all()
    if not mods:
        return

    for mod in mods:
        username = mod["username"]
        activity_count = get_recent_activity_count(username)
        
        # Punkte basierend auf Aktivität vergeben
        if activity_count > 5:
            reward_points = 10
        elif activity_count > 2:
            reward_points = 5
        else:
            reward_points = 1

        new_total = mod["points"] + reward_points
        db.update({"points": new_total}, User.username == username)

        await context.bot.send_message(chat_id=GROUP_ID, text=f"🎉 @{username} erhielt **{reward_points} Punkte** für Aktivität! Gesamt: {new_total} Punkte.")

# Funktion zur Community-Frage
async def ask_question(context: CallbackContext) -> None:
    question = random.choice(questions)
    await context.bot.send_message(chat_id=CHANNEL_ID, text=f"👽 {question}")

# Startfunktion
def main():
    application = Application.builder().token(BOT_TOKEN).build()

    # Befehle registrieren
    application.add_handler(CommandHandler("addpoints", add_points))
    application.add_handler(CommandHandler("points", show_points))

    # Automatische Punktevergabe & Fragen
    application.job_queue.run_repeating(auto_reward_mods, interval=7500, first=10)
    application.job_queue.run_repeating(ask_question, interval=7200, first=10)

    print("Bot läuft...")
    application.run_polling()

if __name__ == "__main__":
    main()
