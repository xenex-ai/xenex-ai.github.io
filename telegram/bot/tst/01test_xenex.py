import os
import random
import asyncio
from datetime import datetime, timedelta
from tinydb import TinyDB, Query
from telegram import Bot
from telegram.ext import Application, CallbackContext, JobQueue

# Telegram Bot Token
BOT_TOKEN = "7761649059:AAEQtfHDd1FXeE5wH3rPIyuXzBXnqB4eP94"
GROUP_ID = -100173852517  # Deine Telegram-Gruppen-ID

# Datenbank für Benutzeraktivitäten
db = TinyDB("user_activity.json")
User = Query()

# Liste mit möglichen Namen
BOT_NAMES = ["Xenex AI", "Xenex X", "Xenex AI Bot", "Xenex Helper", "Xenex v2"]

# Liste mit möglichen Profilbildern (lokale Bilder)
BOT_IMAGES = ["car1.png", "car2.png", "car3.png","car4.png", "car5.png", "car6.png","car7.png", "car8.png"]

async def change_bot_name(context: CallbackContext):
    """Ändert den Namen des Bots zufällig."""
    new_name = random.choice(BOT_NAMES)
    await context.bot.set_my_name(new_name)
    print(f"[INFO] Bot-Name geändert zu: {new_name}")

async def change_bot_photo(context: CallbackContext):
    """Ändert das Profilbild des Bots zufällig."""
    new_image = random.choice(BOT_IMAGES)
    with open(new_image, "rb") as photo:
        await context.bot.set_my_photo(photo=photo)
    print(f"[INFO] Bot-Profilbild geändert zu: {new_image}")

async def track_user_activity(update, context):
    """Speichert die Aktivität eines Benutzers mit Zeitstempel."""
    username = update.message.from_user.username or update.message.from_user.first_name
    now = datetime.now().isoformat()

    # Falls der Nutzer schon existiert, aktualisieren
    if db.search(User.username == username):
        db.update({"last_active": now}, User.username == username)
    else:
        db.insert({"username": username, "last_active": now})

    print(f"[AKTIVITÄT] {username} hat eine Nachricht gesendet.")

async def welcome_back_inactive_users(context: CallbackContext):
    """Begrüßt Nutzer, die lange nicht aktiv waren."""
    now = datetime.now()
    inactive_threshold = now - timedelta(seconds=12)  # geht auch days 7 Tage inaktiv

    inactive_users = db.search(User.last_active < inactive_threshold.isoformat())

    for user in inactive_users:
        username = user["username"]
        await context.bot.send_message(chat_id=GROUP_ID, text=f"👋 Hey @{username}, wir haben dich vermisst! Komm zurück zur Xenex AI Community! 🚀")
        print(f"[WILLKOMMEN] @{username} wurde als inaktiv erkannt und begrüßt.")

async def main():
    """Startet den Bot mit allen geplanten Aktionen."""
    app = Application.builder().token(BOT_TOKEN).build()

    # Benutzeraktivität tracken
    app.add_handler(MessageHandler(filters.ALL, track_user_activity))

    # Job-Queue für geplante Aufgaben
    job_queue = app.job_queue
    job_queue.run_repeating(change_bot_name, interval=12, first=10)  # 86400 Name alle 24h ändern
    job_queue.run_repeating(change_bot_photo, interval=18, first=20)  # 43200 Bild alle 12h ändern
    job_queue.run_repeating(welcome_back_inactive_users, interval=30, first=30)  #86400 Inaktive Nutzer prüfen (täglich)

    print("[INFO] Bot gestartet und führt geplante Aufgaben aus...")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
