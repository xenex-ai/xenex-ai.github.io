from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

# Dein Bot-Token hier einfügen
TOKEN = "DEIN_BOT_TOKEN"

def start(update: Update, context: CallbackContext):
    """Antwortet auf /start mit einer Begrüßung und zeigt die User-ID an"""
    user_id = update.message.chat_id
    update.message.reply_text(f"Hallo! Deine Telegram User-ID ist: {user_id}")

def echo(update: Update, context: CallbackContext):
    """Gibt die User-ID zurück, wenn der Benutzer eine Nachricht sendet"""
    user_id = update.message.chat_id
    update.message.reply_text(f"Deine Telegram User-ID: {user_id}")

def main():
    """Startet den Bot"""
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    # Befehle und Nachrichtenhandler
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, echo))

    # Bot starten
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
