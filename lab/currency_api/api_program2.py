import os
import json
import time
import requests
from datetime import datetime

# Externe API-URLs
EXCHANGE_RATE_API = "https://api.exchangerate-api.com/v4/latest/USD"
UPLOAD_URL = "https://xenexai.com/connect/api_connect.php"

# Maximale Anzahl der Coin-Charts zum Hochladen
MAX_UPLOAD_COINS = 10

# Lokale Ordnerstruktur
COIN_HISTORY_DIR = "coin_history"
MAIN_JSON_DIR = "main_json"
UPLOAD_DIR = "api_uploads"

# Währungsumrechnung zwischenspeichern
exchange_rate = None
last_exchange_update = 0

# Funktion zum Abrufen des USD → EUR Wechselkurses
def update_exchange_rate():
    global exchange_rate, last_exchange_update
    now = time.time()
    if exchange_rate is None or now - last_exchange_update > 18000:  # Alle 5 Stunden aktualisieren
        try:
            response = requests.get(EXCHANGE_RATE_API)
            data = response.json()
            exchange_rate = data["rates"].get("EUR", None)
            last_exchange_update = now
            print(f"Wechselkurs aktualisiert: 1 USD = {exchange_rate:.4f} EUR")
        except Exception as e:
            print("Fehler beim Abrufen des Wechselkurses:", e)

# Funktion zum Speichern von JSON-Daten
def save_json(filename, data, directory):
    os.makedirs(directory, exist_ok=True)
    file_path = os.path.join(directory, filename)
    with open(file_path, "w") as f:
        json.dump(data, f, indent=4)
    return file_path

# Funktion zum Hochladen von Dateien mit Fortschrittsanzeige
def upload_file(file_path):
    try:
        file_size = os.path.getsize(file_path)
        with open(file_path, "rb") as f:
            files = {"file": f}
            response = requests.post(UPLOAD_URL, files=files)
            result = response.json()
            print(f"Upload {file_path} ({file_size} Bytes): {result['message']}")
    except Exception as e:
        print(f"Fehler beim Hochladen von {file_path}: {e}")

# Hauptprogramm
def main():
    update_exchange_rate()
    
    # Beispiel-Daten abrufen (Hier mit Dummy-Daten)
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
    
    # Daten speichern
    for coin in coin_data:
        price_eur = round(coin["price_usd"] * exchange_rate, 4) if exchange_rate else None
        coin_entry = {
            "timestamp": timestamp,
            "price_usd": coin["price_usd"],
            "price_eur": price_eur,
        }
        main_data.append(coin_entry)
        
        # Speichern in einzelne Coin-JSONs
        file_path = save_json(f"{coin['id']}.json", coin_entry, COIN_HISTORY_DIR)
        
    # Haupt-JSON speichern
    main_json_path = save_json("main_data.json", main_data, MAIN_JSON_DIR)
    
    # Hochladen der Hauptdatei
    upload_file(main_json_path)
    
    # Nur die ersten 10 Coins aus COIN_HISTORY_DIR hochladen
    coin_files = sorted(os.listdir(COIN_HISTORY_DIR))[:MAX_UPLOAD_COINS]
    for file in coin_files:
        upload_file(os.path.join(COIN_HISTORY_DIR, file))
    
    print("Daten erfolgreich verarbeitet und hochgeladen.")

if __name__ == "__main__":
    main()
