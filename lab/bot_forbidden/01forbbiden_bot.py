from datetime import datetime, timezone, timedelta
from telegram import ChatPermissions
# Falls noch nicht vorhanden, stelle sicher, dass ADMIN_USERS in der globalen Variablen definiert ist.

### Befehl: Benutzer bannen (Admins nur)
async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Bannt einen Benutzer aus dem Chat.
    Verwendung:
      - Als Antwort auf eine Nachricht (/ban) oder
      - Mit einer Benutzer-ID: /ban <user_id>
    """
    admin = update.effective_user
    if admin.username not in ADMIN_USERS:
        await update.message.reply_text("⛔ Du bist nicht berechtigt, diesen Befehl zu nutzen.")
        return

    target = None
    # Falls als Antwort, verwende den Absender der ursprünglichen Nachricht
    if update.message.reply_to_message:
        target = update.message.reply_to_message.from_user
    elif context.args:
        try:
            user_id = int(context.args[0])
            target_member = await context.bot.get_chat_member(update.effective_chat.id, user_id)
            target = target_member.user
        except Exception as e:
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


### Befehl: Benutzer stummschalten (mute) (Admins nur)
async def mute_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Schaltet einen Benutzer stumm.
    Verwendung:
      - Als Antwort auf eine Nachricht: /mute [Dauer in Minuten] 
      - Oder: /mute <user_id> <Dauer in Minuten>
    Ist keine Dauer angegeben, wird standardmäßig 10 Minuten genutzt.
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
            # Erwartet: /mute <user_id> <Dauer in Minuten>
            user_id = int(context.args[0])
            target_member = await context.bot.get_chat_member(update.effective_chat.id, user_id)
            target = target_member.user
            if len(context.args) >= 2:
                duration = int(context.args[1])
        except Exception as e:
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


### Befehl: Stummschaltung aufheben (unmute) (Admins nur)
async def unmute_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Hebt die Stummschaltung eines Benutzers auf.
    Verwendung:
      - Als Antwort auf eine Nachricht (/unmute) oder
      - Mit einer Benutzer-ID: /unmute <user_id>
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
        except Exception as e:
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


# --- Integration in den Bot (im main()-Bereich hinzufügen) ---
# app.add_handler(CommandHandler("ban", ban_user))
# app.add_handler(CommandHandler("mute", mute_user))
# app.add_handler(CommandHandler("unmute", unmute_user))
