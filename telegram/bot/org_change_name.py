import os
import random
from telegram import Bot
from telegram.ext import Application, CallbackContext
from telegram.ext import JobQueue
import asyncio

# Telegram Bot Token
BOT_TOKEN = "DEIN_BOT_TOKEN"

# Liste mit möglichen Namen
BOT_NAMES = ["Xenex AI", "Xenex X", "Xenex AI Bot", "Xenex Helper", "Xenex v2"]

# Liste mit möglichen Profilbildern (lokale Bilder)
BOT_IMAGES = ["image1.jpg", "image2.jpg", "image3.jpg"]

async def change_bot_name(context: CallbackContext):
    """Ändert den Namen des Bots zufällig."""
    new_name = random.choice(BOT_NAMES)
    bot = context.bot
    await bot.set_my_name(new_name)
    print(f"Bot-Name geändert zu: {new_name}")

async def change_bot_photo(context: CallbackContext):
    """Ändert das Profilbild des Bots zufällig."""
    new_image = random.choice(BOT_IMAGES)
    bot = context.bot
    with open(new_image, "rb") as photo:
        await bot.set_my_photo(photo=photo)
    print(f"Bot-Profilbild geändert zu: {new_image}")

async def main():
    """Startet den Bot mit automatischem Namens- und Bildwechsel."""
    app = Application.builder().token(BOT_TOKEN).build()

    job_queue = app.job_queue
    job_queue.run_repeating(change_bot_name, interval=86400, first=10)  # Name alle 24h ändern
    job_queue.run_repeating(change_bot_photo, interval=43200, first=20)  # Bild alle 12h ändern

    print("Bot läuft und ändert regelmäßig seinen Namen und sein Bild...")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
