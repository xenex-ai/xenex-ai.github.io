import os
import json
import base58
import time
import threading
import queue
import requests
from flask import Flask, jsonify
from nacl.signing import SigningKey
from rich.live import Live
from rich.table import Table
from rich.panel import Panel
from rich.console import Console
from concurrent.futures import ThreadPoolExecutor

# install
# pip install flask pynacl rich requests base58
# pkg update
# pkg install python clang libffi openssl
# pip install --upgrade pip


#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
 ___ _____  ___  _____ ___ 
|  _/  ___|/ _ \|  __ \_  |
| | \ `--./ /_\ \ |  \/ | |
| |  `--. \  _  | | __  | |
| | /\__/ / | | | |_\ \ | |
| |_\____/\_| |_/\____/_| |
|___|                 |___|
[S]olana[A]dress[G]enerator
     a xenexAi product
     
"""

# Solana RPC Endpoint (Mainnet Beta)
SOLANA_RPC_URL = "https://api.mainnet-beta.solana.com"

# Datei für erfolgreiche Adressen
SUCCESS_FILE = "suc_address.json"

# Sicherstellen, dass die Datei existiert
if not os.path.exists(SUCCESS_FILE):
    with open(SUCCESS_FILE, "w") as f:
        json.dump([], f)

# Flask-App initialisieren
app = Flask(__name__)
console = Console()

# Globale Variablen und Locks
address_queue = queue.Queue(maxsize=10000)
total_checked = 0
successful_found = 0
error_count = 0
last_error = ""
latest_status = {"address": "", "sol_balance": 0, "token_accounts": [], "target": ""}
counter_lock = threading.Lock()
error_lock = threading.Lock()
running = True

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
    global error_count, last_error
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
        with error_lock:
            error_count += 1
            last_error = str(e)
        console.log(f"[red]Fehler beim Abfragen der SOL-Balance für {address}: {e}[/red]")
        return 0.0

def check_token_accounts(address):
    """
    Überprüft, ob für die Adresse Token-Konten existieren, die einen Wert (größer 0) besitzen.
    """
    global error_count, last_error
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
        with error_lock:
            error_count += 1
            last_error = str(e)
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

def build_status_table(total, successful, latest, errors, last_err):
    """
    Erstellt eine Rich-Tabelle, die den aktuellen Status anzeigt.
    """
    table = Table(title="xenexAi [SAG] v.1", expand=True)
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
    table.add_row("[red]Fehleranzahl[/red]", f"[red]{errors}[/red]")
    table.add_row("[red]Letzte Fehlerinfo[/red]", f"[red]{last_err}[/red]" if last_err else "[red]keine[/red]")
    return table

def generator_thread():
    """
    Generator-Thread: Erzeugt Schlüssel so schnell wie möglich und legt sie in eine Queue.
    """
    while running:
        if address_queue.full():
            time.sleep(0.001)
            continue
        address, private_key = generate_address()
        address_queue.put((address, private_key))

def worker_task(target_suffix, token_check_enabled):
    """
    Worker-Task: Holt einen Schlüssel aus der Queue, prüft Balance und ggf. Token und aktualisiert den Status.
    """
    global total_checked, successful_found
    while running:
        try:
            address, private_key = address_queue.get(timeout=1)
        except queue.Empty:
            continue

        sol_balance = check_sol_balance(address)
        token_accounts = []
        if token_check_enabled:
            token_accounts = check_token_accounts(address)
        # Aktualisiere den letzten Adressen-Parameter
        with counter_lock:
            latest_status.update({
                "address": address,
                "sol_balance": sol_balance,
                "token_accounts": token_accounts,
                "target": target_suffix
            })
        # Falls ein Suffix angegeben wurde, überspringen
        if target_suffix and not address.endswith(target_suffix):
            with counter_lock:
                total_checked += 1
            continue

        if sol_balance > 0 or token_accounts:
            with counter_lock:
                successful_found += 1
                total_checked += 1
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
        else:
            with counter_lock:
                total_checked += 1

def status_updater():
    """
    Aktualisiert kontinuierlich die Rich Live-Anzeige.
    """
    global error_count, last_error
    with Live(Panel("Starte Generator ...", title="Status", border_style="green"), refresh_per_second=4, console=console) as live:
        while running:
            with counter_lock, error_lock:
                total = total_checked
                successful = successful_found
                latest = latest_status.copy()
                errors = error_count
                last_err = last_error
            live.update(Panel(build_status_table(total, successful, latest, errors, last_err), title="Status", border_style="green"))
            time.sleep(0.2)

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
    # ASCII-Art-Header ausgeben
    header = r"""
 ___ _____  ___  _____ ___ 
|  _/  ___|/ _ \|  __ \_  |
| | \ `--./ /_\ \ |  \/ | |
| |  `--. \  _  | | __  | |
| | /\__/ / | | | |_\ \ | |
| |_\____/\_| |_/\____/_| |
|___|                 |___|
[S]olana[A]dress[G]enerator
     a xenexAi product
     
    """
    console.print(header, style="bold blue")
    
    target = input("Bitte geben Sie das Zielwort (Suffix) ein, mit dem die Adresse enden soll (oder leer lassen): ").strip()
    latest_status["target"] = target
    token_input = input("Sollen auch Token-Konten geprüft werden? (j/n): ").strip().lower()
    token_check_enabled = token_input == "j"
    
    # Starte Flask-Webserver in einem separaten Thread
    flask_thread = threading.Thread(target=start_flask, daemon=True)
    flask_thread.start()
    console.log("Starte Webserver. Abruf unter http://localhost:5000/keys")
    
    # Starte den Generator-Thread
    gen_thread = threading.Thread(target=generator_thread, daemon=True)
    gen_thread.start()
    
    # Für ca. 900 Schlüssel/Adressen pro Sekunde nutzen wir einen kleineren Pool (z.B. 50 Worker)
    worker_count = 16
    executor = ThreadPoolExecutor(max_workers=worker_count)
    for _ in range(worker_count):
        executor.submit(worker_task, target, token_check_enabled)
    
    # Starte den Status-Updater in einem separaten Thread
    status_thread = threading.Thread(target=status_updater, daemon=True)
    status_thread.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        console.log("[red]Key-Generator wurde manuell unterbrochen.[/red]")
        running = False
        executor.shutdown(wait=False)
