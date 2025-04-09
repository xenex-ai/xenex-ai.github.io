import time
import requests
import subprocess
from datetime import datetime

# URL des Servers, an den die Daten gesendet werden sollen
SERVER_URL = "http://example.com/clipboard"  # Ersetze dies mit der tatsächlichen URL

def send_clipboard_data(data):
    """
    Verpackt den Clipboard-Inhalt mit einem Zeitstempel in ein JSON-Objekt 
    und sendet es per HTTP POST an den Server.
    """
    payload = {
        "text": data,
        "timestamp": datetime.utcnow().isoformat()  # ISO-Format, UTC-Zeit
    }
    try:
        response = requests.post(SERVER_URL, json=payload)
        if response.status_code == 200:
            print(f"[{datetime.now()}] Daten erfolgreich gesendet.")
        else:
            print(f"[{datetime.now()}] Fehler: Statuscode {response.status_code}")
    except Exception as e:
        print(f"[{datetime.now()}] Exception beim Senden: {e}")

def get_clipboard():
    """
    Ruft den aktuellen Inhalt der Zwischenablage über 'termux-clipboard-get' ab.
    """
    try:
        clipboard = subprocess.check_output(["termux-clipboard-get"]).decode("utf-8")
        return clipboard
    except Exception as e:
        print(f"[{datetime.now()}] Fehler beim Abrufen der Zwischenablage: {e}")
        return ""

def main():
    print("Clipboard-Überwachung gestartet. Drücke Strg+C zum Beenden.")
    last_clipboard = None

    while True:
        try:
            # Den aktuellen Inhalt der Zwischenablage abrufen
            current_clipboard = get_clipboard()
            # Wenn sich der Inhalt geändert hat und nicht leer ist, den neuen Inhalt senden
            if current_clipboard != last_clipboard and current_clipboard.strip():
                last_clipboard = current_clipboard
                print(f"[{datetime.now()}] Neuer Inhalt erkannt: {current_clipboard}")
                send_clipboard_data(current_clipboard)
            time.sleep(0.5)  # kurze Pause, um die CPU-Last gering zu halten
        except KeyboardInterrupt:
            print("Beende Clipboard-Überwachung...")
            break
        except Exception as e:
            print(f"[{datetime.now()}] Unerwarteter Fehler: {e}")
            time.sleep(1)

if __name__ == "__main__":
    main()

