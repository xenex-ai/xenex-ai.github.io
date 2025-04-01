import json
import os
from datetime import datetime, timezone, timedelta
from telegram import ChatPermissions, Update
from telegram.ext import ContextTypes

# --- JSON-Datei mit verbotenen Wörtern ---
FORBIDDEN_WORDS_FILE = "forbidden_words.json"

def load_forbidden_words():
    """
    Lädt die Liste der verbotenen Wörter aus einer JSON-Datei.
    Erwartetes Format: Eine JSON-Liste, z. B. ["badword1", "badword2", ...]
    """
    if os.path.exists(FORBIDDEN_WORDS_FILE):
        try:
            with open(FORBIDDEN_WORDS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    # Normalisiere alle Wörter zu Kleinbuchstaben
                    return [word.lower() for word in data]
        except Exception as e:
            print("Fehler beim Laden der verbotenen Wörter:", e)
    return []

# Globale Liste verbotener Wörter
forbidden_words = load_forbidden_words()

# --- User-Verwarnungen (für wiederholte Verstöße) ---
user_warnings = {}  # Mapping: user_id -> Anzahl der Verwarnungen
WARNING_THRESHOLD = 3  # Bei 3 oder mehr Verwarnungen erfolgt ein automatischer Bann
MUTE_DURATION_MINUTES = 10  # Dauer (in Minuten) für eine automatische Stummschaltung

# --- Automatische Moderation ---
async def auto_moderate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Prüft eingehende Nachrichten auf verbotene Wörter.
    Bei einem Treffer:
      - Erhöht die Verwarnung des Nutzers.
      - Bei Überschreitung des Schwellenwertes wird der Nutzer automatisch gebannt.
      - Andernfalls wird der Nutzer stummgeschaltet.
    """
    user = update.effective_user
    text = update.message.text.lower() if update.message and update.message.text else ""
    if any(bad_word in text for bad_word in forbidden_words):
        # Erhöhe die Verwarnungsanzahl
        user_id = user.id
        current_warnings = user_warnings.get(user_id, 0) + 1
        user_warnings[user_id] = current_warnings

        # Logge die Verletzung
        log_activity(user, f"Benutzung verbotener Wörter: {text}")

        if current_warnings >= WARNING_THRESHOLD:
            # Automatischer Bann bei wiederholten Verstößen
            try:
                await context.bot.ban_chat_member(chat_id=update.effective_chat.id, user_id=user.id)
                await update.message.reply_text(
                    f"⚠️ {user.first_name}, du wurdest wegen mehrfacher Verstöße gebannt!"
                )
                log_activity(user, "automatischer Bann wegen verbotener Wörter")
            except Exception as e:
                await update.message.reply_text(f"❌ Fehler beim automatischen Bann: {str(e)}")
        else:
            # Automatische Stummschaltung
            until_date = datetime.now(timezone.utc) + timedelta(minutes=MUTE_DURATION_MINUTES)
            try:
                await context.bot.restrict_chat_member(
                    chat_id=update.effective_chat.id,
                    user_id=user.id,
                    permissions=ChatPermissions(can_send_messages=False),
                    until_date=until_date
                )
                await update.message.reply_text(
                    f"⚠️ {user.first_name}, deine Nachricht enthielt verbotene Wörter. "
                    f"Du wurdest für {MUTE_DURATION_MINUTES} Minuten stummgeschaltet. "
                    f"Warnung {current_warnings}/{WARNING_THRESHOLD}."
                )
                log_activity(user, f"automatische Stummschaltung, Verwarnung {current_warnings}")
            except Exception as e:
                await update.message.reply_text(f"❌ Fehler beim automatischen Stummschalten: {str(e)}")

# --- Erweiterter Nachrichten-Handler ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Verarbeitet eingehende Nachrichten:
      1. Prüft zuerst auf verbotene Wörter und moderiert gegebenenfalls automatisch.
      2. Falls keine verbotenen Wörter enthalten sind, werden wie gewohnt Punkte vergeben.
    """
    if update.message and update.message.text:
        text = update.message.text.lower()
        if any(bad_word in text for bad_word in forbidden_words):
            # Führe die automatische Moderation aus und beende die Verarbeitung der Nachricht
            await auto_moderate(update, context)
            return

    # Normale Nachrichten erhalten Punkte
    user = update.effective_user
    points = 2 if update.message.reply_to_message else 1
    await add_points(user.id, user.username or user.first_name, points)


# --- Erweiterte Admin-Befehle (Bannen, Stummschalten, Aufheben) ---
async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Bannt einen Benutzer aus dem Chat.
    Verwendung:
      - Als Antwort auf eine Nachricht (/ban) oder
      - Mit einer Benutzer-ID: /ban <user_id>
    Nur Admins dürfen diesen Befehl ausführen.
    """
    admin = update.effective_user
    if admin.username not in ADMIN_USERS:
        await update.message.reply_text("⛔ Du bist nicht berechtigt, diesen Befehl zu nutzen.")
        return

    target = None
    if update.message.reply_to_message:
        target = update.message.reply_to_message.from_user
    elif context.args:
        try:
            user_id = int(context.args[0])
            target_member = await context.bot.get_chat_member(update.effective_chat.id, user_id)
            target = target_member.user
        except Exception:
            await update.message.reply_text("❌ Ungültige Benutzer-ID.")
            return
    else:
        await update.message.reply_text("❌ Bitte antworte auf eine Nachricht oder gib eine Benutzer-ID an.")
        return

    try:
        await context.bot.ban_chat_member(chat_id=update.effective_chat.id, user_id=target.id)
        await update.message.reply_text(f"✅ Benutzer {target.first_name} wurde gebannt.")
        log_activity(target, "ban")
    except Exception as e:
        await update.message.reply_text(f"❌ Fehler beim Bannen: {str(e)}")


async def mute_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Schaltet einen Benutzer stumm.
    Verwendung:
      - Als Antwort auf eine Nachricht: /mute [Dauer in Minuten] oder
      - Mit Benutzer-ID: /mute <user_id> <Dauer in Minuten>
    Standarddauer ist 10 Minuten, falls keine Dauer angegeben wird.
    Nur Admins dürfen diesen Befehl ausführen.
    """
    admin = update.effective_user
    if admin.username not in ADMIN_USERS:
        await update.message.reply_text("⛔ Du bist nicht berechtigt, diesen Befehl zu nutzen.")
        return

    target = None
    duration = 10  # Standarddauer in Minuten

    if update.message.reply_to_message:
        target = update.message.reply_to_message.from_user
        if context.args:
            try:
                duration = int(context.args[0])
            except ValueError:
                await update.message.reply_text("❌ Bitte gib eine gültige Zeit in Minuten an.")
                return
    elif context.args:
        try:
            user_id = int(context.args[0])
            target_member = await context.bot.get_chat_member(update.effective_chat.id, user_id)
            target = target_member.user
            if len(context.args) >= 2:
                duration = int(context.args[1])
        except Exception:
            await update.message.reply_text("❌ Fehler beim Verarbeiten der Argumente. Nutze: /mute <user_id> <Dauer in Minuten>")
            return
    else:
        await update.message.reply_text("❌ Bitte antworte auf eine Nachricht oder gib Benutzer-ID und Dauer an.")
        return

    until_date = datetime.now(timezone.utc) + timedelta(minutes=duration)
    try:
        await context.bot.restrict_chat_member(
            chat_id=update.effective_chat.id,
            user_id=target.id,
            permissions=ChatPermissions(can_send_messages=False),
            until_date=until_date
        )
        await update.message.reply_text(f"✅ Benutzer {target.first_name} wurde für {duration} Minuten stummgeschaltet.")
        log_activity(target, f"mute for {duration} minutes")
    except Exception as e:
        await update.message.reply_text(f"❌ Fehler beim Stummschalten: {str(e)}")


async def unmute_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Hebt die Stummschaltung eines Benutzers auf.
    Verwendung:
      - Als Antwort auf eine Nachricht (/unmute) oder
      - Mit einer Benutzer-ID: /unmute <user_id>
    Nur Admins dürfen diesen Befehl ausführen.
    """
    admin = update.effective_user
    if admin.username not in ADMIN_USERS:
        await update.message.reply_text("⛔ Du bist nicht berechtigt, diesen Befehl zu nutzen.")
        return

    target = None
    if update.message.reply_to_message:
        target = update.message.reply_to_message.from_user
    elif context.args:
        try:
            user_id = int(context.args[0])
            target_member = await context.bot.get_chat_member(update.effective_chat.id, user_id)
            target = target_member.user
        except Exception:
            await update.message.reply_text("❌ Ungültige Benutzer-ID.")
            return
    else:
        await update.message.reply_text("❌ Bitte antworte auf eine Nachricht oder gib eine Benutzer-ID an.")
        return

    try:
        await context.bot.restrict_chat_member(
            chat_id=update.effective_chat.id,
            user_id=target.id,
            permissions=ChatPermissions(
                can_send_messages=True,
                can_send_media_messages=True,
                can_send_polls=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True,
                can_change_info=True,
                can_invite_users=True,
                can_pin_messages=True
            )
        )
        await update.message.reply_text(f"✅ Benutzer {target.first_name} wurde entstummt.")
        log_activity(target, "unmute")
    except Exception as e:
        await update.message.reply_text(f"❌ Fehler beim Aufheben der Stummschaltung: {str(e)}")


# --- Hinweise zur Integration ---
# 1. Füge die neuen CommandHandler in deinem main()-Bereich hinzu:
#    app.add_handler(CommandHandler("ban", ban_user))
#    app.add_handler(CommandHandler("mute", mute_user))
#    app.add_handler(CommandHandler("unmute", unmute_user))
#
# 2. Ersetze den bestehenden handle_message-Handler durch den obigen, der jetzt zuerst
#    auf verbotene Wörter prüft und automatisch moderiert.
#
# 3. Erstelle oder erweitere deine "forbidden_words.json" mit den Wörtern, die verboten sein sollen.
#
# 4. Stelle sicher, dass die Funktion log_activity (wie in deinem Originalcode definiert) verfügbar ist.
