import requests
import json
import time
from datetime import datetime

def fetch_market_data(vs_currency, per_page=250):
    """
    Ruft Marktdaten von CoinGecko für eine bestimmte Währung ab.
    
    Parameter:
      - vs_currency: Die Zielwährung ("usd" oder "eur").
      - per_page: Anzahl der Coins pro Seite (maximal 250).
      
    Die Funktion iteriert über alle Seiten, bis keine weiteren Daten mehr kommen.
    Rückgabe:
      - Eine Liste mit Dictionaries, in denen u.a. der aktuelle Preis enthalten ist.
    """
    all_coins = []  # Liste, um alle Coins zu sammeln
    page = 1
    while True:
        # URL für die aktuelle Seite
        url = (f"https://api.coingecko.com/api/v3/coins/markets?"
               f"vs_currency={vs_currency}&order=market_cap_desc&per_page={per_page}&page={page}&sparkline=false")
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()  # Überprüft, ob die HTTP-Anfrage erfolgreich war
            data = response.json()
            if not data:
                # Wenn keine Daten mehr zurückgegeben werden, beenden wir die Schleife
                break
            all_coins.extend(data)
            page += 1
        except requests.RequestException as e:
            print(f"Fehler beim Abrufen von Daten (Währung: {vs_currency}, Seite: {page}): {e}")
            break
    return all_coins

def merge_data(usd_data, eur_data):
    """
    Führt zwei Datensätze (USD und EUR) basierend auf der Coin-ID zusammen.
    
    Es wird ein Dictionary erzeugt, in dem jeder Coin mit den folgenden Informationen
    enthalten ist:
      - Name, Symbol
      - Preis in USD und Preis in EUR
      - Market Cap (aus der USD-Abfrage)
      - Letzte Aktualisierung
    """
    # Erzeuge ein Dictionary aus den EUR-Daten, in dem die Coin-ID als Schlüssel dient.
    eur_dict = {coin['id']: coin for coin in eur_data}
    
    merged = {}
    for coin in usd_data:
        coin_id = coin['id']
        merged[coin_id] = {
            'name': coin.get('name'),
            'symbol': coin.get('symbol'),
            'usd_price': coin.get('current_price'),
            # Falls die EUR-Daten für diesen Coin vorhanden sind, wird der Preis übernommen.
            'eur_price': eur_dict.get(coin_id, {}).get('current_price'),
            'market_cap': coin.get('market_cap'),
            'last_updated': coin.get('last_updated')
        }
    return merged

def save_to_json(data, filename="token_price.json"):
    """
    Speichert das übergebene Dictionary in einer JSON-Datei.
    
    Parameter:
      - data: Das Dictionary, das gespeichert werden soll.
      - filename: Der Name der Datei (Standard: token_price.json).
    """
    try:
        with open(filename, "w") as f:
            json.dump(data, f, indent=4)
        print(f"[{datetime.utcnow().isoformat()}Z] Die Daten wurden erfolgreich in '{filename}' gespeichert.")
    except IOError as e:
        print(f"Fehler beim Schreiben der Datei: {e}")

def main():
    """
    Hauptfunktion:
      - Holt alle Marktdaten in USD und EUR.
      - Führt beide Datensätze zusammen.
      - Fügt einen Zeitstempel hinzu.
      - Speichert das Ergebnis in einer JSON-Datei.
      - Wiederholt den Vorgang alle 2 Minuten.
    """
    while True:
        try:
            print("Hole Marktdaten in USD ...")
            usd_data = fetch_market_data("usd")
            print("Hole Marktdaten in EUR ...")
            eur_data = fetch_market_data("eur")
            print("Führe die Daten zusammen ...")
            merged = merge_data(usd_data, eur_data)
            
            # Erzeuge das finale Dictionary inklusive Zeitstempel
            output = {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "data": merged
            }
            
            # Speichere das Ergebnis in token_price.json
            save_to_json(output)
        except Exception as e:
            print(f"Allgemeiner Fehler: {e}")
        
        # Warte 2 Minuten (120 Sekunden) bis zur nächsten Aktualisierung
        time.sleep(120)

if __name__ == "__main__":
    main()
