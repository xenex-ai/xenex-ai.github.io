import os
import telebot               # Library für den Telegram-Bot
import tweepy                # Library für Twitter-API (X)
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler  # Für geplante Aufgaben

# --- Konfiguration ---

# Telegram-Bot Token (von BotFather erhalten)
TELEGRAM_BOT_TOKEN = "DEIN_TELEGRAM_BOT_TOKEN"

# Twitter API Zugangsdaten (von deinem Twitter Developer Account)
TWITTER_API_KEY = "dein_api_key"
TWITTER_API_SECRET = "dein_api_secret"
TWITTER_ACCESS_TOKEN = "dein_access_token"
TWITTER_ACCESS_SECRET = "dein_access_secret"

# --- Initialisierung ---

# Telegram Bot initialisieren
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# Scheduler für geplante Aufgaben starten
scheduler = BackgroundScheduler()
scheduler.start()

# Twitter API initialisieren (über Tweepy)
auth = tweepy.OAuthHandler(TWITTER_API_KEY, TWITTER_API_SECRET)
auth.set_access_token(TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_SECRET)
twitter_api = tweepy.API(auth)

# Liste, um geplante Posts zu speichern (zur Übersicht und Debugging)
# Jedes Element ist ein Tupel: (text, post_time, platform)
scheduled_posts = []

# --- Bot-Handler und Funktionen ---

@bot.message_handler(commands=['start'])
def send_welcome(message):
    """
    Begrüßt den Nutzer und erklärt, wie Beiträge geplant werden.
    """
    welcome_text = (
        "Willkommen beim Social Media Auto-Poster Bot!\n\n"
        "Verwende den Befehl /post, um einen Beitrag zu planen.\n"
        "Das Format lautet:\n"
        "/post Nachricht | Datum (YYYY-MM-DD HH:MM) | Plattform (twitter, instagram, facebook)\n\n"
        "Hinweis: Für Instagram und Facebook ist hier aktuell nur ein Platzhalter implementiert. "
        "Für Twitter wird der Beitrag automatisch über Tweepy gepostet."
    )
    bot.reply_to(message, welcome_text)

@bot.message_handler(commands=['post'])
def schedule_post(message):
    """
    Erwartet vom Nutzer einen Text im Format:
    /post Nachricht | Datum (YYYY-MM-DD HH:MM) | Plattform
    und plant den Beitrag zur Veröffentlichung.
    """
    try:
        # Zerlege die Nachricht anhand des Trennzeichens '|'
        parts = message.text.split('|')
        if len(parts) < 3:
            error_msg = (
                "Ungültiges Format.\n"
                "Bitte benutze:\n"
                "/post Nachricht | Datum (YYYY-MM-DD HH:MM) | Plattform"
            )
            bot.reply_to(message, error_msg)
            return
        
        # Der erste Teil enthält den Befehl und die Nachricht;
        # entferne '/post' und trimme Leerzeichen
        text = parts[0].replace('/post', '').strip()
        if not text:
            bot.reply_to(message, "Die Nachricht darf nicht leer sein!")
            return
        
        # Lese das Datum und die Uhrzeit aus
        date_str = parts[1].strip()
        post_time = datetime.strptime(date_str, "%Y-%m-%d %H:%M")
        
        # Lese und normalisiere die Plattform (in Kleinbuchstaben)
        platform = parts[2].strip().lower()
        if platform not in ["twitter", "instagram", "facebook"]:
            bot.reply_to(message, "Plattform muss entweder 'twitter', 'instagram' oder 'facebook' sein.")
            return

        # Speichere den geplanten Post in der Liste
        scheduled_posts.append((text, post_time, platform))
        
        # Plane die Ausführung des Posts zur angegebenen Zeit
        scheduler.add_job(post_to_social_media, 'date', run_date=post_time, args=[text, platform])
        
        confirmation_msg = f"Beitrag geplant für {post_time} auf {platform}."
        bot.reply_to(message, confirmation_msg)
    except Exception as e:
        bot.reply_to(message, f"Fehler: {str(e)}")

def post_to_social_media(text, platform):
    """
    Leitet den Post an die jeweilige Plattform-Funktion weiter.
    """
    if platform == "twitter":
        post_to_twitter(text)
    elif platform == "instagram":
        post_to_instagram(text)
    elif platform == "facebook":
        post_to_facebook(text)
    else:
        print(f"Unbekannte Plattform: {platform}")

def post_to_twitter(text):
    """
    Postet den Text auf Twitter (X) mithilfe der Tweepy-API.
    """
    try:
        twitter_api.update_status(status=text)
        print(f"[Twitter] Beitrag gepostet: {text}")
    except Exception as e:
        print(f"[Twitter] Fehler beim Posten: {e}")

def post_to_instagram(text):
    """
    Platzhalter-Funktion für Instagram. Hier müsste die Instagram API integriert werden.
    """
    print(f"[Instagram] Simuliert Posten: {text}")
    # Integration mit Instagram (z.B. über Facebook Graph API) hier implementieren.

def post_to_facebook(text):
    """
    Platzhalter-Funktion für Facebook. Hier müsste die Facebook Graph API integriert werden.
    """
    print(f"[Facebook] Simuliert Posten: {text}")
    # Integration mit der Facebook Graph API hier implementieren.

# --- Start des Bots ---

# Der Bot startet nun mit Polling, um kontinuierlich auf Nachrichten zu reagieren.
bot.polling()
