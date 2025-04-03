import requests
import json
import time
import os
from datetime import datetime, timezone
from apscheduler.schedulers.background import BackgroundScheduler
from concurrent.futures import ThreadPoolExecutor, as_completed

# Globaler Wechselkurs (USD -> EUR)
usd_to_eur_rate = None

# --- ExchangeRate API ---
def update_exchange_rate():
    """
    Aktualisiert den globalen USD->EUR-Wechselkurs mithilfe der ExchangeRate-API.
    URL: https://api.exchangerate-api.com/v4/latest/USD
    Ausführung: Alle 5 Stunden.
    """
    global usd_to_eur_rate
    try:
        url = "https://api.exchangerate-api.com/v4/latest/USD"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        rate = data['rates']['EUR']
        usd_to_eur_rate = rate
        now = datetime.now(timezone.utc).isoformat()
        print(f"[{now}] Wechselkurs aktualisiert: 1 USD = {usd_to_eur_rate} EUR")
    except Exception as e:
        print(f"Fehler beim Aktualisieren des Wechselkurses: {e}")

# --- CoinGecko API ---
def fetch_coingecko_data():
    """
    Ruft Marktdaten von CoinGecko ab (Preis in USD) und berechnet den EUR-Wert.
    Iteriert über alle Seiten (max. 250 Coins pro Seite).
    Zusätzlich wird ein Feld 'market_data' hinzugefügt, das weitere Kennzahlen enthält.
    Rückgabe:
        Ein Dictionary mit Coin-ID als Schlüssel und relevanten Daten als Wert.
    """
    coins = {}
    page = 1
    per_page = 250
    while True:
        url = (f"https://api.coingecko.com/api/v3/coins/markets?"
               f"vs_currency=usd&order=market_cap_desc&per_page={per_page}&page={page}&sparkline=false")
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            if not data:
                break
            for coin in data:
                coin_id = coin.get('id')
                usd_price = coin.get('current_price')
                eur_price = round(usd_price * usd_to_eur_rate, 4) if usd_price is not None and usd_to_eur_rate else None
                market_data = {
                    "price_change_percentage_24h": coin.get("price_change_percentage_24h"),
                    "total_volume": coin.get("total_volume")
                }
                coins[coin_id] = {
                    'name': coin.get('name'),
                    'symbol': coin.get('symbol'),
                    'usd_price': usd_price,
                    'eur_price': eur_price,
                    'market_cap': coin.get('market_cap'),
                    'last_updated': coin.get('last_updated'),
                    'market_data': market_data
                }
            page += 1
        except Exception as e:
            print(f"Fehler bei CoinGecko (Seite {page}): {e}")
            break
    return coins

# --- CoinPaprika API ---
def fetch_coinpaprika_data():
    """
    Ruft Ticker-Daten von CoinPaprika ab (Preis in USD) und berechnet den EUR-Wert.
    Zusätzlich werden weitere Marktdaten (z. B. Volumen, Prozentänderungen) extrahiert.
    Rückgabe:
        Ein Dictionary mit Coin-ID als Schlüssel und relevanten Daten als Wert.
    """
    coins = {}
    url = "https://api.coinpaprika.com/v1/tickers"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        for coin in data:
            coin_id = coin.get('id')
            usd_info = coin.get('quotes', {}).get('USD', {})
            usd_price = usd_info.get('price')
            eur_price = round(usd_price * usd_to_eur_rate, 4) if usd_price is not None and usd_to_eur_rate else None
            market_data = {
                "volume_24h": usd_info.get("volume_24h"),
                "percent_change_24h": usd_info.get("percent_change_24h"),
                "percent_change_7d": usd_info.get("percent_change_7d")
            }
            coins[coin_id] = {
                'name': coin.get('name'),
                'symbol': coin.get('symbol'),
                'usd_price': usd_price,
                'eur_price': eur_price,
                'market_cap': coin.get('market_cap_usd'),
                'last_updated': coin.get('last_updated'),
                'market_data': market_data
            }
    except Exception as e:
        print(f"Fehler beim Abrufen von CoinPaprika-Daten: {e}")
    return coins

# --- CoinCap API ---
def fetch_coincap_data():
    """
    Ruft Daten von CoinCap ab.
    URL: https://api.coincap.io/v2/assets
    Erwartet wird ein JSON-Objekt, das unter anderem den USD-Preis (priceUsd) enthält.
    Zusätzlich werden weitere Marktdaten wie 24h-Änderung und Volumen extrahiert.
    Rückgabe:
        Ein Dictionary mit Coin-ID als Schlüssel und relevanten Daten als Wert.
    """
    coins = {}
    url = "https://api.coincap.io/v2/assets"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json().get('data', [])
        for coin in data:
            coin_id = coin.get('id')
            try:
                usd_price = float(coin.get('priceUsd'))
            except (TypeError, ValueError):
                usd_price = None
            eur_price = round(usd_price * usd_to_eur_rate, 4) if usd_price is not None and usd_to_eur_rate else None
            market_data = {
                "change_percent_24hr": coin.get("changePercent24Hr"),
                "volume_usd_24hr": coin.get("volumeUsd24Hr"),
                "vwap_24hr": coin.get("vwap24Hr")
            }
            coins[coin_id] = {
                'name': coin.get('name'),
                'symbol': coin.get('symbol'),
                'usd_price': usd_price,
                'eur_price': eur_price,
                'market_cap': coin.get('marketCapUsd'),
                'last_updated': coin.get('changePercent24Hr'),
                'market_data': market_data
            }
    except Exception as e:
        print(f"Fehler beim Abrufen von CoinCap-Daten: {e}")
    return coins

# --- Upload einer Datei auf externen Server via PHP ---
def upload_file_to_server(filename):
    """
    Lädt die angegebene Datei auf den externen Server hoch.
    Die Datei wird an die PHP-Datei (api_connect.php) gesendet.
    Hinweis: Diese Funktion nutzt eine POST-Anfrage mit multipart/form-data.
    """
    upload_url = "https://xenexai.com/connect/api_connect.php"
    try:
        print(f"Starte Upload der Datei '{filename}' ...")
        with open(filename, "rb") as f:
            files = {"file": (filename, f, "application/json")}
            response = requests.post(upload_url, files=files, timeout=10)
            response.raise_for_status()
        now = datetime.now(timezone.utc).isoformat()
        print(f"[{now}] Datei '{filename}' erfolgreich hochgeladen. Serverantwort: {response.text}")
    except Exception as e:
        now = datetime.now(timezone.utc).isoformat()
        print(f"[{now}] Fehler beim Hochladen der Datei '{filename}': {e}")

# --- Upload der aggregierten Datei token_price.json ---
def upload_to_server(filename="token_price.json"):
    """
    Lädt die aggregierte JSON-Datei auf den externen Server hoch.
    """
    upload_file_to_server(filename)

# --- Upload einzelner History-Dateien ohne ZIP ---
def upload_history_files(folder="coin_history"):
    """
    Durchläuft den Ordner coin_history und lädt jede JSON-Datei einzeln hoch.
    """
    if not os.path.exists(folder):
        print(f"Ordner '{folder}' existiert nicht. Kein History-Upload notwendig.")
        return

    print(f"Starte Upload der History-Dateien aus dem Ordner '{folder}' ...")
    for file in os.listdir(folder):
        if file.endswith(".json"):
            file_path = os.path.join(folder, file)
            upload_file_to_server(file_path)
    print("Upload der History-Dateien abgeschlossen.")

# --- Speichern der aggregierten Daten ---
def save_to_json(data, filename="token_price.json"):
    """
    Speichert das übergebene Dictionary in einer JSON-Datei und lädt diese Datei anschließend
    auf den externen Server hoch.
    """
    try:
        with open(filename, "w") as f:
            json.dump(data, f, indent=4)
        now = datetime.now(timezone.utc).isoformat()
        print(f"[{now}] Aggregierte Daten in '{filename}' gespeichert.")
        upload_to_server(filename)
    except Exception as e:
        now = datetime.now(timezone.utc).isoformat()
        print(f"[{now}] Fehler beim Schreiben der Datei '{filename}': {e}")

# --- Aktualisieren der einzelnen Coin-History-Dateien ---
def update_coin_history(source, coin_id, price_usd, price_eur, timestamp, folder="coin_history"):
    """
    Aktualisiert (oder erstellt) für einen Coin eine JSON-Datei, die bei jedem Update
    einen neuen Eintrag (price_usd, price_eur, timestamp) anhängt.
    Der Dateiname wird als <source>_<coin_id>.json angelegt.
    """
    try:
        if not os.path.exists(folder):
            os.makedirs(folder)
        filename = os.path.join(folder, f"{source}_{coin_id}.json")
        if os.path.exists(filename):
            with open(filename, "r") as f:
                history = json.load(f)
        else:
            history = []
        entry = {
            "price_usd": price_usd,
            "price_eur": price_eur,
            "timestamp": timestamp
        }
        history.append(entry)
        with open(filename, "w") as f:
            json.dump(history, f, indent=4)
        print(f"History für {source} '{coin_id}' aktualisiert.")
    except Exception as e:
        now = datetime.now(timezone.utc).isoformat()
        print(f"[{now}] Fehler beim Aktualisieren der History für {source} '{coin_id}': {e}")

# --- Update der Coin-Daten ---
def update_coin_data():
    """
    Holt Coin-Daten von CoinGecko, CoinPaprika und CoinCap parallel,
    berechnet den EUR-Wert anhand des aktuellen Wechselkurses und speichert
    die kombinierten Daten in 'token_price.json'.
    Zusätzlich wird für jeden Coin in einer eigenen JSON-Datei (pro Quelle) ein
    Eintrag (price_usd, price_eur, timestamp) angehängt.
    """
    global usd_to_eur_rate
    if usd_to_eur_rate is None:
        print("Wechselkurs nicht verfügbar. Überspringe diesen Durchlauf.")
        return

    current_timestamp = datetime.now(timezone.utc).isoformat()
    print(f"[{current_timestamp}] Starte Aktualisierung der Coin-Daten ...")

    results = {}
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            executor.submit(fetch_coingecko_data): "coingecko",
            executor.submit(fetch_coinpaprika_data): "coinpaprika",
            executor.submit(fetch_coincap_data): "coincap"
        }
        for future in as_completed(futures):
            source = futures[future]
            try:
                results[source] = future.result()
            except Exception as exc:
                now = datetime.now(timezone.utc).isoformat()
                print(f"[{now}] Fehler bei {source}: {exc}")
                results[source] = {}

    output = {
        "timestamp": current_timestamp,
        "exchange_rate_usd_to_eur": usd_to_eur_rate,
        "coingecko": results.get("coingecko", {}),
        "coinpaprika": results.get("coinpaprika", {}),
        "coincap": results.get("coincap", {})
    }
    save_to_json(output)

    # Aktualisiere die History-Dateien für jeden Coin
    for source, coins in results.items():
        for coin_id, coin_data in coins.items():
            update_coin_history(
                source=source,
                coin_id=coin_id,
                price_usd=coin_data.get("usd_price"),
                price_eur=coin_data.get("eur_price"),
                timestamp=current_timestamp
            )
    # Lade alle History-Dateien einzeln hoch
    upload_history_files()

# --- Hauptprogramm mit Scheduler ---
def main():
    """
    Initialisiert den Scheduler:
      - Aktualisiert den Wechselkurs alle 5 Stunden.
      - Holt Coin-Daten (aus allen APIs) alle 2 Minuten.
    """
    scheduler = BackgroundScheduler(timezone=timezone.utc)

    update_exchange_rate()
    scheduler.add_job(update_exchange_rate, 'interval', hours=5)
    scheduler.add_job(update_coin_data, 'interval', minutes=2)

    scheduler.start()
    print("Scheduler gestartet. Drücke STRG+C zum Beenden.")

    try:
        while True:
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        print("Scheduler wird beendet ...")
        scheduler.shutdown()

if __name__ == "__main__":
    main()
