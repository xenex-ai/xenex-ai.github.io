import telegram
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackContext

BOT_TOKEN = "DEIN_BOT_TOKEN"

async def get_chat_id(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat_id
    await update.message.reply_text(f"Group ID: {chat_id}")

def main():
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("chatid", get_chat_id))
    application.run_polling()

if __name__ == "__main__":
    main()
