import requests
import json
import time
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
                coins[coin_id] = {
                    'name': coin.get('name'),
                    'symbol': coin.get('symbol'),
                    'usd_price': usd_price,
                    'eur_price': eur_price,
                    'market_cap': coin.get('market_cap'),
                    'last_updated': coin.get('last_updated')
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
    URL: https://api.coinpaprika.com/v1/tickers
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
            coins[coin_id] = {
                'name': coin.get('name'),
                'symbol': coin.get('symbol'),
                'usd_price': usd_price,
                'eur_price': eur_price,
                'market_cap': coin.get('market_cap_usd'),
                'last_updated': coin.get('last_updated')
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
            coins[coin_id] = {
                'name': coin.get('name'),
                'symbol': coin.get('symbol'),
                'usd_price': usd_price,
                'eur_price': eur_price,
                'market_cap': coin.get('marketCapUsd'),
                'last_updated': coin.get('changePercent24Hr')  # Beispielhaft: hier kann auch ein anderes Feld stehen
            }
    except Exception as e:
        print(f"Fehler beim Abrufen von CoinCap-Daten: {e}")
    return coins

# --- Upload auf Core Webserver via PHP ---
def upload_to_server(filename="token_price.json"):
    """
    Lädt die JSON-Datei auf den Core Webserver hoch.
    Die Datei wird an die PHP-Datei (currency_connect.php) gesendet, die den Upload abwickelt.
    URL: https://corenetwork.io/xenexAi/connect/currency_connect.php

    Hinweis: Diese Funktion nutzt eine POST-Anfrage mit multipart/form-data.
    """
    upload_url = "https://corenetwork.io/xenexAi/connect/currency_connect.php"
    try:
        with open(filename, "rb") as f:
            files = {"file": (filename, f, "application/json")}
            response = requests.post(upload_url, files=files, timeout=10)
            response.raise_for_status()
        now = datetime.now(timezone.utc).isoformat()
        print(f"[{now}] Datei erfolgreich auf den Server hochgeladen: {upload_url}")
    except Exception as e:
        print(f"Fehler beim Hochladen der Datei: {e}")

# --- Speichern der Daten ---
def save_to_json(data, filename="token_price.json"):
    """
    Speichert das übergebene Dictionary in einer JSON-Datei und lädt diese Datei anschließend
    auf den Core Webserver hoch.
    Die Datei wird an https://corenetwork.io/xenexAi/connect/currency_connect.php gesendet,
    wo der Upload per PHP abgewickelt wird.
    """
    try:
        with open(filename, "w") as f:
            json.dump(data, f, indent=4)
        now = datetime.now(timezone.utc).isoformat()
        print(f"[{now}] Daten erfolgreich in '{filename}' gespeichert.")
        # Anschließender Upload der Datei auf den Webserver über die PHP-Datei
        upload_to_server(filename)
    except Exception as e:
        print(f"Fehler beim Schreiben der Datei: {e}")

# --- Update der Coin-Daten ---
def update_coin_data():
    """
    Holt Coin-Daten von CoinGecko, CoinPaprika und CoinCap parallel,
    berechnet den EUR-Wert anhand des aktuellen Wechselkurses und speichert
    die kombinierten Daten in 'token_price.json'.
    Ausführung: Alle 2 Minuten.
    """
    global usd_to_eur_rate
    if usd_to_eur_rate is None:
        print("Wechselkurs nicht verfügbar. Überspringe diesen Durchlauf.")
        return

    now = datetime.now(timezone.utc).isoformat()
    print(f"[{now}] Starte Aktualisierung der Coin-Daten ...")

    # Parallele Ausführung der API-Aufrufe
    results = {}
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            executor.submit(fetch_coingecko_data): "coingecko",
            executor.submit(fetch_coinpaprika_data): "coinpaprika",
            executor.submit(fetch_coincap_data): "coincap"
        }
        for future in as_completed(futures):
            key = futures[future]
            try:
                results[key] = future.result()
            except Exception as exc:
                print(f"Fehler bei {key}: {exc}")
                results[key] = {}

    output = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "exchange_rate_usd_to_eur": usd_to_eur_rate,
        "coingecko": results.get("coingecko", {}),
        "coinpaprika": results.get("coinpaprika", {}),
        "coincap": results.get("coincap", {})
    }
    save_to_json(output)

# --- Hauptprogramm mit Scheduler ---
def main():
    """
    Initialisiert den Scheduler:
      - Aktualisiert den Wechselkurs alle 5 Stunden.
      - Holt Coin-Daten (aus allen APIs) alle 2 Minuten.
    """
    scheduler = BackgroundScheduler(timezone=timezone.utc)

    # Wechselkurs sofort und alle 5 Stunden aktualisieren
    update_exchange_rate()
    scheduler.add_job(update_exchange_rate, 'interval', hours=5)

    # Coin-Daten alle 2 Minuten aktualisieren
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
