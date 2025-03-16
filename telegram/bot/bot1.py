import random
import time
from telegram import Bot, ParseMode
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from threading import Thread

# Haupt-Bot-Token
MAIN_BOT_TOKEN = '7761649059:AAEQtfHDd1FXeE5wH3rPIyuXzBXnqB4eP94'
# Beispiel: https://t.me/botfather und dann Token erhalten

# Funktion, um einen neuen Bot zu erstellen (dies würde eine echte Bot-Erstellung simulieren)
def create_new_bot():
    bot_names = ["BotAlpha", "BotBeta", "BotGamma", "BotDelta", "BotEpsilon"]
    new_bot_name = random.choice(bot_names)
    bot = Bot(MAIN_BOT_TOKEN)
    return bot, new_bot_name

# Funktion, um mit anderen Bots zu kommunizieren
def simulate_bot_conversation(bot, bot_name):
    # Simuliere eine Nachricht
    messages = [
        f"Hi, {bot_name}! Wie geht's?",
        f"Hey, {bot_name}! Hast du schon von XenexAi gehört?",
        f"Was hältst du von der Staking-Funktion von $XNX, {bot_name}?"
    ]
    message = random.choice(messages)
    
    # Der Bot sendet die Nachricht in den Kanal
    bot.send_message(chat_id='@xentst', text=message, parse_mode=ParseMode.MARKDOWN)

# Funktion, die von den Bots aufgerufen wird, um miteinander zu kommunizieren
def bot_conversation_thread():
    bot, bot_name = create_new_bot()
    while True:
        simulate_bot_conversation(bot, bot_name)
        time.sleep(random.randint(5, 20))  # Simuliert zufällige Pausen zwischen den Nachrichten

# Haupt-Bot, der neue Bots erzeugt und sie zur Kommunikation anregt
def main():
    updater = Updater(MAIN_BOT_TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    # Starte Threads für die Kommunikation der Bots
    for _ in range(5):  # Anzahl der simulierten Bots, die gleichzeitig laufen
        thread = Thread(target=bot_conversation_thread)
        thread.start()

    updater.start_polling()

if __name__ == '__main__':
    main()
