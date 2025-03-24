import requests

async def upload_points(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Sendet die Datei tst_point.json an den Server (https://corenetwork.io/xenexai/json.php).
    Nur Admins können diesen Befehl ausführen.
    """
    user = update.message.from_user
    if user.username not in ADMIN_USERS:
        await update.message.reply_text("❌ Du bist nicht berechtigt, diesen Befehl auszuführen.")
        return

    url = "https://corenetwork.io/xenexai/json.php"
    files = {"file": open("tst_point.json", "rb")}
    
    try:
        response = requests.post(url, files=files)
        if response.status_code == 200:
            await update.message.reply_text("✅ Datei erfolgreich hochgeladen!")
        else:
            await update.message.reply_text(f"⚠️ Fehler beim Hochladen: {response.status_code}")
    except Exception as e:
        await update.message.reply_text(f"❌ Fehler: {str(e)}")

# 📜 Befehl in den Bot einfügen
app.add_handler(CommandHandler("upload_points", upload_points))
