import os
import json
import base58
import time
import requests
from nacl.signing import SigningKey
from tqdm import tqdm
from colorama import init, Fore, Style

# Initialisiere colorama (automatischer Reset bei jedem Print)
init(autoreset=True)

# Solana RPC Endpoint (Mainnet Beta)
SOLANA_RPC_URL = "https://api.mainnet-beta.solana.com"

# HTTP Session für persistente Verbindungen
session = requests.Session()
session.headers.update({"Content-Type": "application/json"})

def ascii_intro():
    intro = f"""
{Fore.GREEN}{Style.BRIGHT}
   ____        _            _       
  / ___|  __ _| | ___ _   _| | __ _ 
  \___ \ / _` | |/ __| | | | |/ _` |
   ___) | (_| | | (__| |_| | | (_| |
  |____/ \__,_|_|\___|\__,_|_|\__,_|
                                    
         Solana Scanner v1.0
{Style.RESET_ALL}
    """
    print(intro)

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
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getBalance",
        "params": [address]
    }
    try:
        response = session.post(SOLANA_RPC_URL, json=payload, timeout=10)
        result = response.json()
        if "result" in result and result["result"]:
            lamports = result["result"]["value"]
            sol = lamports / 1e9  # 1 SOL = 10^9 Lamports
            return sol
        return 0.0
    except Exception as e:
        print(f"{Fore.RED}Fehler beim Abfragen der SOL-Balance für {address}:{Style.RESET_ALL} {e}")
        return 0.0

def check_token_accounts(address):
    """
    Überprüft, ob für die Adresse Token-Konten existieren, die einen Wert (größer 0) besitzen.
    """
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
        response = session.post(SOLANA_RPC_URL, json=payload, timeout=10)
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
        print(f"{Fore.RED}Fehler beim Abfragen der Token-Konten für {address}:{Style.RESET_ALL} {e}")
        return []

def save_address(entry, filename="addresses.json"):
    """
    Speichert den gefundenen Eintrag (Adresse, privater Schlüssel, Guthaben und Token-Konten)
    in der Datei addresses.json. Existierende Einträge bleiben erhalten.
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

def main():
    ascii_intro()
    # Optional: Benutzerdefiniertes Suffix für die Adresse
    target = input(f"{Fore.CYAN}Bitte geben Sie das Zielwort (Suffix) ein, mit dem die Adresse enden soll (oder leer für alle): {Style.RESET_ALL}").strip()
    print(f"{Fore.YELLOW}Starte die Generierung und Überprüfung der Adressen...{Style.RESET_ALL}")
    
    pbar = tqdm(unit="Schlüssel", dynamic_ncols=True, desc="Generiere Keys")
    
    try:
        while True:
            address, private_key = generate_address()
            pbar.update(1)
            
            # Filter: Falls Suffix angegeben, überspringe Adressen, die nicht damit enden.
            if target and not address.endswith(target):
                continue
            
            # Überprüfe SOL-Balance und Token-Konten
            sol_balance = check_sol_balance(address)
            token_accounts = check_token_accounts(address)
            
            # Ausgabe und Speicherung, wenn Guthaben vorhanden ist.
            if sol_balance > 0 or token_accounts:
                pbar.write(f"{Fore.GREEN}{Style.BRIGHT}Gefundene Adresse mit Guthaben!{Style.RESET_ALL}")
                pbar.write(f"{Fore.MAGENTA}Adresse: {Style.BRIGHT}{address}{Style.RESET_ALL}")
                pbar.write(f"{Fore.MAGENTA}Privater Schlüssel: {Style.BRIGHT}{private_key}{Style.RESET_ALL}")
                pbar.write(f"{Fore.BLUE}SOL Balance: {Style.BRIGHT}{sol_balance} SOL{Style.RESET_ALL}")
                if token_accounts:
                    pbar.write(f"{Fore.BLUE}Token Accounts:")
                    for token in token_accounts:
                        pbar.write(f"  Mint: {token['mint']}, Amount: {token['amount']}")
                entry = {
                    "address": address,
                    "private_key": private_key,
                    "sol_balance": sol_balance,
                    "token_accounts": token_accounts
                }
                save_address(entry)
                # Optional: Entweder weitersuchen oder beenden. Hier beenden wir.
                break
            
            # Kurze Pause, um API-Rate-Limiting zu vermeiden
            time.sleep(0.2)
    except KeyboardInterrupt:
        pbar.write(f"{Fore.RED}Abbruch durch Benutzer.{Style.RESET_ALL}")
    finally:
        pbar.close()

if __name__ == "__main__":
    main()
