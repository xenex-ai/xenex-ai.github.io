# pip install pynacl base58 tqdm requests flask rich

import os
import json
import base58
import time
import threading
import requests
from flask import Flask, jsonify
from nacl.signing import SigningKey
from rich.live import Live
from rich.table import Table
from rich.panel import Panel
from rich.console import Console

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
console = Console()

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
        console.log(f"[red]Fehler beim Abfragen der SOL-Balance für {address}: {e}[/red]")
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
        console.log(f"[red]Fehler beim Abfragen der Token-Konten für {address}: {e}[/red]")
        return []

def save_success(entry, filename=SUCCESS_FILE):
    """
    Speichert den erfolgreichen Eintrag (Adresse, privater Schlüssel, SOL-Balance und Token-Konten)
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

def build_status_table(latest, total, successful):
    """
    Erstellt eine Rich-Tabelle, die den aktuellen Status anzeigt.
    """
    table = Table(title="Solana Adress Generator", expand=True)
    table.add_column("Parameter", style="bold cyan", justify="right")
    table.add_column("Wert", style="magenta")

    table.add_row("Letzte Adresse", latest.get("address", ""))
    table.add_row("SOL-Balance", f"{latest.get('sol_balance', 0):.4f} SOL")
    token_details = ""
    for token in latest.get("token_accounts", []):
        token_details += f"Mint: {token['mint']}, Amount: {token['amount']}\n"
    table.add_row("Token Accounts", token_details if token_details else "keine")
    table.add_row("Gesucht (Suffix)", latest.get("target", ""))
    table.add_row("Gesamt geprüft", str(total))
    table.add_row("Erfolgreich (Gespeichert)", str(successful))
    return table

def key_generator(target_suffix=""):
    """
    Generiert fortlaufend Adressen, prüft Kontostände und aktualisiert die visuelle Anzeige.
    Erfolgreiche Adressen werden gespeichert.
    """
    total_checked = 0
    successful_found = 0
    latest_status = {"address": "", "sol_balance": 0, "token_accounts": [], "target": target_suffix}

    with Live(Panel("Starte Generator ...", title="Status", border_style="green"), refresh_per_second=4, console=console) as live:
        try:
            while True:
                total_checked += 1
                address, private_key = generate_address()
                sol_balance = check_sol_balance(address)
                token_accounts = check_token_accounts(address)
                latest_status.update({
                    "address": address,
                    "sol_balance": sol_balance,
                    "token_accounts": token_accounts,
                })
                # Falls ein Suffix vorgegeben wurde, überspringe Adressen, die nicht damit enden.
                if target_suffix and not address.endswith(target_suffix):
                    live.update(Panel(build_status_table(latest_status, total_checked, successful_found), title="Status", border_style="green"))
                    continue

                # Wenn Guthaben vorhanden ist, Ausgabe, Speichern und Zähler erhöhen
                if sol_balance > 0 or token_accounts:
                    successful_found += 1
                    console.log(f"[bold green]+++ Erfolgreiche Adresse gefunden +++[/bold green]")
                    console.log(f"[yellow]Adresse:[/yellow] {address}")
                    console.log(f"[yellow]Privater Schlüssel:[/yellow] {private_key}")
                    console.log(f"[yellow]SOL-Balance:[/yellow] {sol_balance:.4f} SOL")
                    if token_accounts:
                        console.log("[yellow]Token Accounts:[/yellow]")
                        for token in token_accounts:
                            console.log(f"  Mint: {token['mint']} | Amount: {token['amount']}")
                    entry = {
                        "address": address,
                        "private_key": private_key,
                        "sol_balance": sol_balance,
                        "token_accounts": token_accounts
                    }
                    save_success(entry)
                    # Kurze Pause nach einem Treffer
                    time.sleep(5)
                live.update(Panel(build_status_table(latest_status, total_checked, successful_found), title="Status", border_style="green"))
                # Kurze Pause, um API-Rate Limits zu berücksichtigen
                time.sleep(0.2)
        except KeyboardInterrupt:
            console.log("[red]Key-Generator wurde manuell unterbrochen.[/red]")

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
    # Starte den Flask-Webserver; in Termux empfiehlt sich der Host 0.0.0.0
    app.run(host="0.0.0.0", port=5000)

if __name__ == "__main__":
    target = input("Bitte geben Sie das Zielwort (Suffix) ein, mit dem die Adresse enden soll (oder leer lassen): ").strip()
    
    # Starte den Key-Generator in einem Hintergrund-Thread
    generator_thread = threading.Thread(target=key_generator, args=(target,), daemon=True)
    generator_thread.start()
    
    console.log("Starte Webserver. Abruf unter http://localhost:5000/keys")
    start_flask()
