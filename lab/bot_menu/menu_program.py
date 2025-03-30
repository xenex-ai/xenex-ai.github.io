#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Beispiel: Telegram-Bot mit verschiedenen Menü-Elementen

Dieser Code demonstriert, wie man einen Telegram-Bot mit Python erstellt, der 
verschiedene Menüs anzeigt. Wir nutzen dafür die Bibliothek "python-telegram-bot".
Achte darauf, dass du die Bibliothek installierst, z.B. via:
    pip install python-telegram-bot

Bevor du den Code ausführst, musst du deinen eigenen Bot-Token von BotFather 
bei Telegram anfordern und im Code eintragen.
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, CallbackContext

# Aktivieren des Loggings, um Fehler und wichtige Informationen zu protokollieren.
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Ersetze 'DEIN_BOT_TOKEN' mit dem tatsächlichen Token deines Bots!
BOT_TOKEN = '823556168:AAExXQu7T_-olKcPkcm5sJ8Z0DDmYKC7GbE'


def start(update: Update, context: CallbackContext) -> None:
    """
    Start-Handler: Wird aufgerufen, wenn der Benutzer den /start Befehl sendet.
    Erzeugt eine Inline-Tastatur mit mehreren Menü-Elementen.
    """
    # Begrüßungsnachricht, die dem Benutzer angezeigt wird.
    welcome_text = (
        "Willkommen beim Telegram-Bot!\n\n"
        "Bitte wähle eine Option aus dem Menü unten:"
    )
    
    # Erstellung einer Inline-Tastatur (InlineKeyboardMarkup) mit Buttons.
    # Jeder Button hat einen Text und einen Callback-Datenwert, der später im Callback-Handler verarbeitet wird.
    keyboard = [
        [InlineKeyboardButton("Option 1", callback_data='option1')],
        [InlineKeyboardButton("Option 2", callback_data='option2')],
        [InlineKeyboardButton("Option 3", callback_data='option3')],
        # Mehrere Buttons in einer Zeile:
        [
            InlineKeyboardButton("Option A", callback_data='optionA'),
            InlineKeyboardButton("Option B", callback_data='optionB')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Senden der Nachricht mit der Inline-Tastatur an den Benutzer.
    update.message.reply_text(welcome_text, reply_markup=reply_markup)


def button_handler(update: Update, context: CallbackContext) -> None:
    """
    Callback-Handler für Inline-Tastatur-Buttons.
    Diese Funktion wird aufgerufen, wenn der Benutzer einen Button drückt.
    """
    query = update.callback_query
    # Es ist wichtig, den Callback zu "acknowledgen", damit Telegram weiß, dass der Button verarbeitet wurde.
    query.answer()
    
    # Ermittlung der gedrückten Option anhand der Callback-Daten.
    option = query.data
    response_text = ""
    
    # Überprüfen der Option und Setzen einer entsprechenden Antwort.
    if option == 'option1':
        response_text = "Du hast Option 1 gewählt."
    elif option == 'option2':
        response_text = "Du hast Option 2 gewählt."
    elif option == 'option3':
        response_text = "Du hast Option 3 gewählt."
    elif option == 'optionA':
        response_text = "Du hast Option A gewählt."
    elif option == 'optionB':
        response_text = "Du hast Option B gewählt."
    else:
        response_text = "Unbekannte Option gewählt."
    
    # Antwort senden – hier wird die ursprüngliche Nachricht (mit der Tastatur) editiert,
    # um dem Benutzer das Ergebnis seiner Auswahl anzuzeigen.
    query.edit_message_text(text=response_text)


def help_command(update: Update, context: CallbackContext) -> None:
    """
    Help-Handler: Wird aufgerufen, wenn der Benutzer den /help Befehl sendet.
    Zeigt dem Benutzer eine Hilfenachricht.
    """
    help_text = (
        "Verfügbare Befehle:\n"
        "/start - Startet den Bot und zeigt das Menü an.\n"
        "/help - Zeigt diese Hilfenachricht an."
    )
    update.message.reply_text(help_text)


def main() -> None:
    """
    Die Main-Funktion initialisiert den Bot und startet den Dispatcher.
    Hier werden die Handler (z.B. für /start, /help und Button-Callbacks) registriert.
    """
    # Erstellen eines Updater-Objekts, das die Verbindung zu Telegram herstellt.
    updater = Updater(BOT_TOKEN, use_context=True)

    # Zugriff auf den Dispatcher, der die eingehenden Nachrichten verarbeitet.
    dispatcher = updater.dispatcher

    # Handler für den /start Befehl registrieren.
    dispatcher.add_handler(CommandHandler("start", start))
    
    # Handler für den /help Befehl registrieren.
    dispatcher.add_handler(CommandHandler("help", help_command))
    
    # Handler für Callback-Queries von Inline-Tastaturen registrieren.
    dispatcher.add_handler(CallbackQueryHandler(button_handler))

    # Starten des Bots: Er beginnt, Nachrichten abzurufen und zu verarbeiten.
    updater.start_polling()
    logger.info("Bot startet...")

    # Der Bot läuft, bis er manuell gestoppt wird (z.B. mit Strg+C).
    updater.idle()


if __name__ == '__main__':
    main()
