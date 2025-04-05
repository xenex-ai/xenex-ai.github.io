# pip install pynacl base58 tqdm requests flask

import os
import json
import base58
import time
import threading
import requests
from flask import Flask, jsonify, send_file, abort
from nacl.signing import SigningKey
from tqdm import tqdm

# Solana RPC Endpoint (Mainnet Beta)
SOLANA_RPC_URL = "https://api.mainnet-beta.solana.com"

# Dateiname für erfolgreiche Adressen
SUCCESS_FILE = "suc_address.json"

# Sicherstellen, dass die Datei existiert
if not os.path.exists(SUCCESS_FILE):
    with open(SUCCESS_FILE, "w") as f:
        json.dump([], f)

# Flask-App initialisieren
app = Flask(__name__)

def generate_address():
    """
    Generiert ein ed25519-Schlüsselpaar, encodiert den öffentlichen Schlüssel in Base58
    (entspricht der Solana-Adresse) und gibt Adresse sowie privaten Schlüssel (hex-formatiert) zurück.
    """
    sk = SigningKey.generate()
    vk = sk.verify_key
    public_key = vk.encode()
    address = base58.b58encode(public_key).decode("utf-8")
    private_key = sk.encode().hex()
    return address, private_key

def check_sol_balance(address):
    """
    Überprüft den SOL-Bestand (in SOL) der Adresse über die Solana JSON-RPC API.
    """
    headers = {"Content-Type": "application/json"}
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getBalance",
        "params": [address]
    }
    try:
        response = requests.post(SOLANA_RPC_URL, headers=headers, json=payload, timeout=10)
        result = response.json()
        if "result" in result and result["result"]:
            lamports = result["result"]["value"]
            sol = lamports / 1e9  # 1 SOL = 10^9 Lamports
            return sol
        return 0.0
    except Exception as e:
        print(f"Fehler beim Abfragen der SOL-Balance für {address}: {e}")
        return 0.0

def check_token_accounts(address):
    """
    Überprüft, ob für die Adresse Token-Konten existieren, die einen Wert (größer 0) besitzen.
    """
    headers = {"Content-Type": "application/json"}
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getTokenAccountsByOwner",
        "params": [
            address,
            {"programId": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"},
            {"encoding": "jsonParsed"}
        ]
    }
    tokens_with_balance = []
    try:
        response = requests.post(SOLANA_RPC_URL, headers=headers, json=payload, timeout=10)
        result = response.json()
        if "result" in result and result["result"]:
            accounts = result["result"].get("value", [])
            for account in accounts:
                token_info = account.get("account", {}).get("data", {}).get("parsed", {}).get("info", {})
                token_amount = token_info.get("tokenAmount", {})
                amount = float(token_amount.get("uiAmount", 0))
                if amount > 0:
                    tokens_with_balance.append({
                        "mint": token_info.get("mint", ""),
                        "amount": amount
                    })
        return tokens_with_balance
    except Exception as e:
        print(f"Fehler beim Abfragen der Token-Konten für {address}: {e}")
        return []

def save_success(entry, filename=SUCCESS_FILE):
    """
    Speichert den gefundenen erfolgreichen Eintrag (Adresse, privater Schlüssel, SOL-Balance und Token-Konten)
    in der Datei SUCCESS_FILE. Existierende Einträge bleiben erhalten.
    """
    if os.path.exists(filename):
        with open(filename, "r") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                data = []
    else:
        data = []
    data.append(entry)
    with open(filename, "w") as f:
        json.dump(data, f, indent=4)

def key_generator(target_suffix=""):
    """
    Generiert fortlaufend Adressen, prüft den Kontostand und gibt aktuelle Infos im Terminal aus.
    Bei einem "Erfolg" (Guthaben > 0 SOL oder Token-Konten mit Wert) wird die Adresse in SUCCESS_FILE gespeichert.
    """
    pbar = tqdm(unit="Schlüssel", dynamic_ncols=True)
    try:
        while True:
            address, private_key = generate_address()
            sol_balance = check_sol_balance(address)
            token_accounts = check_token_accounts(address)
            # Aktualisiere die Fortschrittsbeschreibung mit den aktuellen Werten
            pbar.set_description(f"{address[-6:]} | SOL: {sol_balance:.4f}")
            pbar.update(1)
            
            # Falls ein Suffix vorgegeben wurde, überspringe Adressen, die nicht damit enden.
            if target_suffix and not address.endswith(target_suffix):
                continue
            
            # Wenn Guthaben vorhanden ist, Ausgabe und speichern
            if sol_balance > 0 or token_accounts:
                pbar.write("+++ Erfolgreiche Adresse gefunden +++")
                pbar.write(f"Adresse: {address}")
                pbar.write(f"Privater Schlüssel: {private_key}")
                pbar.write(f"SOL-Balance: {sol_balance} SOL")
                if token_accounts:
                    pbar.write("Token-Konten:")
                    for token in token_accounts:
                        pbar.write(f"  Mint: {token['mint']}, Amount: {token['amount']}")
                entry = {
                    "address": address,
                    "private_key": private_key,
                    "sol_balance": sol_balance,
                    "token_accounts": token_accounts
                }
                save_success(entry)
                # Hier kannst du entscheiden: entweder weitersuchen oder kurz pausieren
                time.sleep(5)
            
            # Kurze Pause, um API-Rate Limits zu berücksichtigen
            time.sleep(0.2)
    except KeyboardInterrupt:
        pbar.write("Key-Generator wurde manuell unterbrochen.")
    finally:
        pbar.close()

# Flask-Route, um die Datei mit den erfolgreichen Schlüsseln abzurufen
@app.route("/keys", methods=["GET"])
def get_keys():
    if os.path.exists(SUCCESS_FILE):
        try:
            with open(SUCCESS_FILE, "r") as f:
                data = json.load(f)
            return jsonify(data)
        except Exception as e:
            return jsonify({"error": f"Fehler beim Laden der Datei: {str(e)}"}), 500
    else:
        return jsonify({"error": "Datei nicht gefunden."}), 404

def start_flask():
    # Starte die Flask-App; für Termux empfiehlt sich der Host 0.0.0.0
    app.run(host="0.0.0.0", port=5000)

if __name__ == "__main__":
    # Optional: Benutzer kann ein Ziel-Suffix definieren, falls gewünscht.
    target = input("Bitte geben Sie das Zielwort (Suffix) ein, mit dem die Adresse enden soll (oder leer lassen): ").strip()
    
    # Starte den Key-Generator in einem Hintergrund-Thread
    generator_thread = threading.Thread(target=key_generator, args=(target,), daemon=True)
    generator_thread.start()
    
    # Starte den Flask-Webserver, um die erfolgreichen Keys unter /keys abrufbar zu machen.
    print("Starte Webserver. Abruf unter http://localhost:5000/keys")
    start_flask()
