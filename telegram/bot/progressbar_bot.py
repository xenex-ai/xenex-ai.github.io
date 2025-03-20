import time
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext

# Bot-Token hier einfügen
TOKEN = "DEIN_BOT_TOKEN"

# Funktion zur Erstellung einer Progressbar
def get_progressbar(progress, total, length=10):
    percentage = progress / total
    filled_length = int(length * percentage)
    bar = "█" * filled_length + "░" * (length - filled_length)
    return f"[{bar}] {int(percentage * 100)}%"

# /progress Befehl
def progress_command(update: Update, context: CallbackContext) -> None:
    chat_id = update.effective_chat.id
    message = context.bot.send_message(chat_id=chat_id, text="Starte Fortschritt...")

    total_steps = 10  # Anzahl der Schritte

    for i in range(total_steps + 1):
        progressbar = get_progressbar(i, total_steps)
        context.bot.edit_message_text(chat_id=chat_id, message_id=message.message_id, text=progressbar)
        time.sleep(1)  # Verzögerung für Animation

    context.bot.send_message(chat_id=chat_id, text="✅ Fortschritt abgeschlossen!")

# Hauptfunktion zum Starten des Bots
def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("progress", progress_command))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
