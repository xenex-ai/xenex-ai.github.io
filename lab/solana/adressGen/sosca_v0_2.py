#!/usr/bin/env python3
import os
import json
import base58
import time
import requests
import random
import argparse
import logging
from datetime import datetime
from nacl.signing import SigningKey
from tqdm import tqdm
from colorama import init, Fore, Style
import pyfiglet

# Initialisiere farbige Terminalausgabe
init(autoreset=True)

# -------------------------------
# Konfiguration und Logging
# -------------------------------

# Standard-Konfigurationsdatei
CONFIG_FILE = "config.json"
DEFAULT_CONFIG = {
    "solana_rpc_url": "https://api.mainnet-beta.solana.com",
    "api_timeout": 10,
    "delay": 0.2,
    "log_file": "sosca_v0.2.log",
    "verbose": False
}

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                config = json.load(f)
            logging.info("Konfiguration aus config.json geladen.")
            return config
        except Exception as e:
            logging.error(f"Fehler beim Laden der Konfiguration: {e}")
    logging.info("Standardkonfiguration wird verwendet.")
    return DEFAULT_CONFIG

config = load_config()

# Logging-Setup
logging.basicConfig(
    level=logging.DEBUG if config.get("verbose") else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(config.get("log_file", "sosca_v0.2.log")),
        logging.StreamHandler()
    ]
)

# Solana RPC Endpoint und Session
SOLANA_RPC_URL = config.get("solana_rpc_url", DEFAULT_CONFIG["solana_rpc_url"])
session = requests.Session()
session.headers.update({"Content-Type": "application/json"})

# -------------------------------
# ASCII-Art Intro und Hacker-Quotes
# -------------------------------
HACKER_QUOTES = [
    "Infiltrating the blockchain matrix...",
    "Compiling cryptographic entropy...",
    "Decrypting Solana's secrets...",
    "Initializing quantum-safe protocols...",
    "Accessing decentralized backdoors...",
    "Mapping the digital frontier...",
    "Engaging secure channel..."
]

def display_intro():
    logo = pyfiglet.figlet_format("sosca v0.2", font="slant")
    intro_text = (
        f"{Fore.GREEN}{logo}\n"
        f"{Fore.YELLOW}{Style.BRIGHT}Professional Solana Crypto Address Scanner\n"
        f"{Fore.CYAN}{'-'*60}\n"
        f"{Fore.MAGENTA}   Real-time key generation | Wallet monitoring | Auto-logging\n"
        f"{Fore.CYAN}{'-'*60}{Style.RESET_ALL}\n"
        f"Startzeit: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    )
    print(intro_text)
    time.sleep(1)

def print_hacker_quote():
    quote = random.choice(HACKER_QUOTES)
    logging.debug(f"Hacker-Quote: {quote}")
    print(Fore.BLUE + "[sosca] " + quote)
    time.sleep(0.8)

# -------------------------------
# Hauptfunktionen: Keygen, Balance-Checks, Logging
# -------------------------------
def generate_address():
    sk = SigningKey.generate()
    vk = sk.verify_key
    public_key = vk.encode()
    address = base58.b58encode(public_key).decode("utf-8")
    private_key = sk.encode().hex()
    return address, private_key

def check_sol_balance(address):
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getBalance",
        "params": [address]
    }
    try:
        response = session.post(SOLANA_RPC_URL, json=payload, timeout=config.get("api_timeout"))
        result = response.json()
        if "result" in result and result["result"]:
            lamports = result["result"]["value"]
            sol = lamports / 1e9
            return sol
        return 0.0
    except Exception as e:
        logging.error(f"Fehler bei getBalance für {address}: {e}")
        print(Fore.RED + f"[ERROR] SOL-Balance-Check fehlgeschlagen: {e}")
        return 0.0

def check_token_accounts(address):
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
    tokens = []
    try:
        response = session.post(SOLANA_RPC_URL, json=payload, timeout=config.get("api_timeout"))
        result = response.json()
        if "result" in result and result["result"]:
            accounts = result["result"].get("value", [])
            for account in accounts:
                info = account.get("account", {}).get("data", {}).get("parsed", {}).get("info", {})
                amount = float(info.get("tokenAmount", {}).get("uiAmount", 0))
                if amount > 0:
                    tokens.append({
                        "mint": info.get("mint", "n/a"),
                        "amount": amount
                    })
        return tokens
    except Exception as e:
        logging.error(f"Fehler bei getTokenAccountsByOwner für {address}: {e}")
        print(Fore.RED + f"[ERROR] Token-Konten-Check fehlgeschlagen: {e}")
        return []

def save_address(entry, filename="sosca_addresses.json"):
    if os.path.exists(filename):
        try:
            with open(filename, "r") as f:
                data = json.load(f)
        except json.JSONDecodeError:
            data = []
    else:
        data = []
    data.append(entry)
    with open(filename, "w") as f:
        json.dump(data, f, indent=4)
    logging.info(f"Adresse gespeichert: {entry['address']}")

def display_found_address(address, private_key, sol_balance, tokens):
    print(Fore.GREEN + "\n>>> Adresse mit Guthaben gefunden! <<<")
    print(Fore.CYAN + f"Adresse      : {Fore.WHITE + Style.BRIGHT}{address}")
    print(Fore.CYAN + f"Privater Key : {Fore.WHITE + Style.BRIGHT}{private_key}")
    print(Fore.CYAN + f"SOL Balance  : {Fore.YELLOW + Style.BRIGHT}{sol_balance} SOL")
    if tokens:
        print(Fore.CYAN + "Token-Konten:")
        for token in tokens:
            print(Fore.MAGENTA + f"  - Mint: {token['mint']} | Amount: {token['amount']}")

# -------------------------------
# Hauptprogramm
# -------------------------------
def main():
    display_intro()
    parser = argparse.ArgumentParser(
        description="sosca v0.2 – Professioneller Solana Crypto Address Scanner"
    )
    parser.add_argument("-s", "--suffix", type=str, default="",
                        help="Optionales Suffix, mit dem die Adresse enden soll")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Aktiviere ausführliche Debug-Ausgaben")
    args = parser.parse_args()

    # Falls CLI-Parameter den Config-Wert überschreiben
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logging.debug("Verbose-Modus aktiviert.")

    target_suffix = args.suffix.strip()
    if target_suffix:
        print(Fore.LIGHTYELLOW_EX + f"> Ziel-Suffix: {target_suffix}")
    else:
        print(Fore.LIGHTYELLOW_EX + "> Kein Ziel-Suffix gesetzt, alle Adressen werden geprüft.")

    print(Fore.LIGHTGREEN_EX + "\n>> Starte den Address-Scanner...\n")
    logging.info("sosca v0.2 gestartet.")

    pbar = tqdm(unit="keys", desc="sosca engine", dynamic_ncols=True)
    try:
        while True:
            print_hacker_quote()
            address, private_key = generate_address()
            pbar.update(1)

            if target_suffix and not address.endswith(target_suffix):
                continue

            sol_balance = check_sol_balance(address)
            tokens = check_token_accounts(address)

            if sol_balance > 0 or tokens:
                display_found_address(address, private_key, sol_balance, tokens)
                entry = {
                    "address": address,
                    "private_key": private_key,
                    "sol_balance": sol_balance,
                    "token_accounts": tokens,
                    "timestamp": datetime.now().isoformat()
                }
                save_address(entry)
                break  # Falls nur ein Treffer benötigt wird, ansonsten entfernen.
            time.sleep(config.get("delay", 0.2))
    except KeyboardInterrupt:
        print(Fore.RED + "\n[!] Scan durch Benutzer abgebrochen.")
        logging.warning("Scan wurde durch den Benutzer unterbrochen.")
    finally:
        pbar.close()
        logging.info("sosca v0.2 beendet.")

if __name__ == "__main__":
    main()
