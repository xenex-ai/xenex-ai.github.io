import os
import json
import time
import requests
from datetime import datetime

# Externe API-URLs
EXCHANGE_RATE_API = "https://api.exchangerate-api.com/v4/latest/USD"
UPLOAD_URL = "https://xenexai.com/connect/api_connect.php"

# Maximale Anzahl der Coin-JSONs (Chartdaten) zum Hochladen
MAX_UPLOAD_COINS = 10

# Lokale Ordnerstruktur
COIN_HISTORY_DIR = "coin_history"
MAIN_JSON_DIR = "main_json"

# Währungsumrechnung zwischenspeichern
exchange_rate = None
last_exchange_update = 0

def update_exchange_rate():
    """
    Aktualisiert den USD→EUR Wechselkurs.
    Aktualisierung erfolgt, wenn noch keiner vorhanden ist oder mehr als 5 Stunden vergangen sind.
    """
    global exchange_rate, last_exchange_update
    now = time.time()
    if exchange_rate is None or now - last_exchange_update > 18000:  # 5 Stunden = 18000 Sekunden
        try:
            response = requests.get(EXCHANGE_RATE_API, timeout=10)
            data = response.json()
            exchange_rate = data["rates"].get("EUR", None)
            last_exchange_update = now
            print(f"[{datetime.utcnow().isoformat()}] Wechselkurs aktualisiert: 1 USD = {exchange_rate:.4f} EUR")
        except Exception as e:
            print(f"[{datetime.utcnow().isoformat()}] Fehler beim Abrufen des Wechselkurses: {e}")

def save_json(filename, data, directory):
    """
    Speichert Daten als JSON in einem angegebenen Ordner.
    Falls der Ordner nicht existiert, wird er erstellt.
    Gibt den kompletten Dateipfad zurück.
    """
    os.makedirs(directory, exist_ok=True)
    file_path = os.path.join(directory, filename)
    try:
        with open(file_path, "w") as f:
            json.dump(data, f, indent=4)
        print(f"[{datetime.utcnow().isoformat()}] Datei '{file_path}' erfolgreich gespeichert (Größe: {os.path.getsize(file_path)} Bytes).")
    except Exception as e:
        print(f"[{datetime.utcnow().isoformat()}] Fehler beim Speichern von '{file_path}': {e}")
    return file_path

def upload_file(file_path):
    """
    Lädt eine Datei per POST an den externen Server (UPLOAD_URL) hoch.
    Gibt detaillierte Fortschrittsmeldungen aus, inklusive Dateigröße und Serverantwort.
    """
    try:
        file_size = os.path.getsize(file_path)
        print(f"[{datetime.utcnow().isoformat()}] Starte Upload der Datei '{file_path}' (Größe: {file_size} Bytes)...")
        with open(file_path, "rb") as f:
            files = {"file": (os.path.basename(file_path), f, "application/json")}
            response = requests.post(UPLOAD_URL, files=files, timeout=20)
            response.raise_for_status()
            result = response.json()
            print(f"[{datetime.utcnow().isoformat()}] Upload '{file_path}' erfolgreich: {result.get('message', 'keine Nachricht vom Server')}")
    except Exception as e:
        print(f"[{datetime.utcnow().isoformat()}] Fehler beim Hochladen von '{file_path}': {e}")

def main():
    # Wechselkurs aktualisieren
    update_exchange_rate()
    if exchange_rate is None:
        print("Kein Wechselkurs verfügbar. Abbruch!")
        return
    
    # Dummy-Daten (ersetze diese durch deine echten API-Aufrufe)
    coin_data = [
        {"id": "bitcoin", "price_usd": 65432.10},
        {"id": "ethereum", "price_usd": 3201.55},
        {"id": "solana", "price_usd": 180.75},
        {"id": "cardano", "price_usd": 0.78},
        {"id": "ripple", "price_usd": 0.62},
        {"id": "polkadot", "price_usd": 7.45},
        {"id": "litecoin", "price_usd": 82.31},
        {"id": "chainlink", "price_usd": 14.22},
        {"id": "dogecoin", "price_usd": 0.12},
        {"id": "avalanche", "price_usd": 25.90},
        {"id": "tron", "price_usd": 0.14},
    ]
    
    timestamp = datetime.utcnow().isoformat()
    main_data = []
    
    # Speichere für jeden Coin einen Eintrag und erzeuge die individuellen JSONs
    for coin in coin_data:
        price_eur = round(coin["price_usd"] * exchange_rate, 4)
        coin_entry = {
            "timestamp": timestamp,
            "price_usd": coin["price_usd"],
            "price_eur": price_eur,
        }
        main_data.append(coin_entry)
        coin_filename = f"{coin['id']}.json"
        save_json(coin_filename, coin_entry, COIN_HISTORY_DIR)
    
    # Speichere die aggregierten Daten als Hauptdatei
    main_json_path = save_json("main_data.json", main_data, MAIN_JSON_DIR)
    
    # Upload der Hauptdatei
    print(f"[{datetime.utcnow().isoformat()}] Starte Upload der aggregierten Datei '{main_json_path}'...")
    upload_file(main_json_path)
    
    # Upload der ersten 10 Coin-History-Dateien
    print(f"[{datetime.utcnow().isoformat()}] Starte Upload der ersten {MAX_UPLOAD_COINS} Coin-History-Dateien aus '{COIN_HISTORY_DIR}' ...")
    coin_files = sorted(os.listdir(COIN_HISTORY_DIR))[:MAX_UPLOAD_COINS]
    for file in coin_files:
        file_path = os.path.join(COIN_HISTORY_DIR, file)
        upload_file(file_path)
    
    print(f"[{datetime.utcnow().isoformat()}] Alle Daten erfolgreich verarbeitet und hochgeladen.")

if __name__ == "__main__":
    main()
