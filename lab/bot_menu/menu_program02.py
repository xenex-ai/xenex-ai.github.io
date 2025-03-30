#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Erweiterter Telegram-Bot mit verschiedenen Menü-Elementen

Dieser Code zeigt, wie man neben Inline-Tastaturen auch ein Reply-Keyboard
und verschachtelte Menüs in einem Telegram-Bot einsetzt.
Stelle sicher, dass die Bibliothek "python-telegram-bot" installiert ist:
    pip install python-telegram-bot

Ersetze 'DEIN_BOT_TOKEN' durch deinen eigenen Bot-Token.
"""

import logging
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
)
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, CallbackContext, MessageHandler, Filters

# Logging konfigurieren
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = '823556168:AAExXQu7T_-olKcPkcm5sJ8Z0DDmYKC7GbE'


def start(update: Update, context: CallbackContext) -> None:
    """
    Start-Funktion: Zeigt sowohl ein Inline-Menü als auch ein Reply-Keyboard.
    """
    # Nachrichtentext
    welcome_text = (
        "Willkommen beim erweiterten Telegram-Bot!\n\n"
        "Wähle eine Option aus dem Inline-Menü oder dem Reply-Keyboard:"
    )
    
    # Inline-Tastatur (für Callback-Buttons)
    inline_keyboard = [
        [InlineKeyboardButton("Inline Option 1", callback_data='inline1')],
        [InlineKeyboardButton("Inline Option 2", callback_data='inline2')],
        # Verschachteltes Inline-Menü als Beispiel:
        [InlineKeyboardButton("Mehr Optionen", callback_data='more_options')]
    ]
    inline_markup = InlineKeyboardMarkup(inline_keyboard)
    
    # Reply-Keyboard (Buttons erscheinen dauerhaft im Chat)
    reply_keyboard = [
        [KeyboardButton("Reply Option A"), KeyboardButton("Reply Option B")],
        [KeyboardButton("Reply Option C")]
    ]
    reply_markup = ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True)
    
    # Senden der Nachricht mit beiden Tastaturtypen
    update.message.reply_text(welcome_text, reply_markup=reply_markup)
    update.message.reply_text("Hier ist das Inline-Menü:", reply_markup=inline_markup)


def button_handler(update: Update, context: CallbackContext) -> None:
    """
    Callback-Handler für Inline-Tastatur-Buttons.
    Verarbeitet die Callback-Daten und zeigt entsprechende Antworten.
    """
    query = update.callback_query
    query.answer()
    option = query.data

    if option == 'inline1':
        text = "Du hast Inline Option 1 gewählt."
    elif option == 'inline2':
        text = "Du hast Inline Option 2 gewählt."
    elif option == 'more_options':
        # Zeige ein weiteres verschachteltes Inline-Menü
        text = "Wähle eine weitere Option:"
        new_keyboard = [
            [InlineKeyboardButton("Sub-Option 1", callback_data='sub1')],
            [InlineKeyboardButton("Sub-Option 2", callback_data='sub2')],
            [InlineKeyboardButton("Zurück", callback_data='back')]
        ]
        new_markup = InlineKeyboardMarkup(new_keyboard)
        query.edit_message_text(text=text, reply_markup=new_markup)
        return
    elif option == 'sub1':
        text = "Du hast Sub-Option 1 gewählt."
    elif option == 'sub2':
        text = "Du hast Sub-Option 2 gewählt."
    elif option == 'back':
        # Zurück zum Hauptmenü
        text = "Zurück zum Hauptmenü."
        main_keyboard = [
            [InlineKeyboardButton("Inline Option 1", callback_data='inline1')],
            [InlineKeyboardButton("Inline Option 2", callback_data='inline2')],
            [InlineKeyboardButton("Mehr Optionen", callback_data='more_options')]
        ]
        main_markup = InlineKeyboardMarkup(main_keyboard)
        query.edit_message_text(text=text, reply_markup=main_markup)
        return
    else:
        text = "Unbekannte Option gewählt."

    query.edit_message_text(text=text)


def reply_handler(update: Update, context: CallbackContext) -> None:
    """
    Handler für Nachrichten, die vom Reply-Keyboard stammen.
    Erkennt den Text und sendet eine passende Antwort.
    """
    user_input = update.message.text
    if user_input == "Reply Option A":
        response = "Du hast Reply Option A gewählt."
    elif user_input == "Reply Option B":
        response = "Du hast Reply Option B gewählt."
    elif user_input == "Reply Option C":
        response = "Du hast Reply Option C gewählt."
    else:
        response = "Unbekannte Antwort. Bitte benutze die angebotenen Optionen."

    update.message.reply_text(response)


def help_command(update: Update, context: CallbackContext) -> None:
    """
    Hilfe-Befehl: Zeigt eine Übersicht der verfügbaren Befehle.
    """
    help_text = (
        "Verfügbare Befehle:\n"
        "/start - Startet den Bot und zeigt die Menüs an.\n"
        "/help - Zeigt diese Hilfenachricht an.\n"
        "/remove - Entfernt das Reply-Keyboard."
    )
    update.message.reply_text(help_text)


def remove_keyboard(update: Update, context: CallbackContext) -> None:
    """
    Entfernt das Reply-Keyboard, falls der Benutzer es nicht mehr sehen möchte.
    """
    update.message.reply_text("Reply-Keyboard wird entfernt.", reply_markup=ReplyKeyboardRemove())


def main() -> None:
    """
    Initialisiert den Bot und registriert alle Handler.
    """
    updater = Updater(BOT_TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    # Registrieren der Befehle und Handler
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", help_command))
    dispatcher.add_handler(CommandHandler("remove", remove_keyboard))
    
    # Handler für Callback-Queries von Inline-Tastaturen
    dispatcher.add_handler(CallbackQueryHandler(button_handler))
    
    # Handler für Antworten vom Reply-Keyboard
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, reply_handler))

    updater.start_polling()
    logger.info("Erweiterter Bot startet...")
    updater.idle()


if __name__ == '__main__':
    main()
