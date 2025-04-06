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

def ascii_intro():
    banner = f"""
{Fore.GREEN}{Style.BRIGHT}
  ____   ___  ____   ___ 
 / ___| / _ \\|  _ \\ / _ \\
 \\___ \\| | | | |_) | | | |
  ___) | |_| |  __/| |_| |
 |____/ \\___/|_|    \\___/
         v.0.5
{Style.RESET_ALL}
    """
    print(banner)

def get_balance(address):
    """
    Ruft über den Solana Mainnet RPC (https://api.mainnet-beta.solana.com)
    das Guthaben (in Lamports) des übergebenen Kontos ab.
    """
    url = "https://api.mainnet-beta.solana.com"
    headers = {"Content-Type": "application/json"}
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getBalance",
        "params": [address]
    }
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        data = response.json()
        balance = data.get("result", {}).get("value", 0)
        return balance
    except Exception as e:
        print(f"{Fore.RED}Fehler beim Abrufen des Guthabens: {e}{Style.RESET_ALL}")
        return 0

def generate_address():
    """
    Generiert ein ed25519-Schlüsselpaar, encodiert den öffentlichen Schlüssel in Base58
    (entspricht der Solana-Adresse) und gibt folgende Formate zurück:
      - address: Base58-encodierte Adresse (Public Key)
      - private_key_hex: 32-Byte Private Key im Hex-Format
      - phantom_key: 64-Byte Secret Key als JSON-Array (Private Key + Public Key),
                     kompatibel mit Phantom Wallet
    """
    sk = SigningKey.generate()
    vk = sk.verify_key

    # Adresse aus öffentlichem Schlüssel (Base58)
    public_key = vk.encode()
    address = base58.b58encode(public_key).decode("utf-8")

    # 32-Byte Private Key als Hex
    private_key_hex = sk.encode().hex()

    # 64-Byte Secret Key: Private Key (32 Byte) + Public Key (32 Byte)
    secret_key = sk.encode() + vk.encode()
    phantom_key = list(secret_key)

    return address, private_key_hex, phantom_key

def save_address(entry, filename="addresses.json"):
    """
    Speichert den gefundenen Eintrag (Adresse, hex. private_key und phantom_key)
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
    
    target = input(f"{Fore.CYAN}Bitte geben Sie das Zielwort (Suffix) ein, mit dem die Adresse enden soll (oder leer für alle): {Style.RESET_ALL}").strip()
    min_balance_input = input(f"{Fore.CYAN}Geben Sie das gewünschte Mindestguthaben in SOL ein (leer = 0 SOL): {Style.RESET_ALL}").strip()
    try:
        min_balance_sol = float(min_balance_input) if min_balance_input else 0.0
    except ValueError:
        min_balance_sol = 0.0
    # 1 SOL = 1e9 Lamports
    min_balance = int(min_balance_sol * 1e9)
    
    print(f"{Fore.YELLOW}Starte die Generierung und Überprüfung der Adressen...{Style.RESET_ALL}")
    
    pbar = tqdm(unit="Schlüssel", dynamic_ncols=True, desc="Generiere Keys")
    
    try:
        while True:
            address, private_key_hex, phantom_key = generate_address()
            pbar.update(1)
            
            # Filter: Falls ein Suffix angegeben wurde, wird nur weitergearbeitet, wenn die Adresse damit endet.
            if target and not address.endswith(target):
                continue
            
            # Guthaben prüfen:
            balance = get_balance(address)
            # Für Debug: Balance in SOL (Lamports/1e9)
            balance_sol = balance / 1e9
            
            # Nur wenn das Guthaben >= gewünschtes Mindestguthaben ist, gilt es als Treffer.
            if balance < min_balance:
                pbar.write(f"{Fore.YELLOW}Adresse {address} hat {balance_sol:.9f} SOL - nicht ausreichend.{Style.RESET_ALL}")
                continue
            
            # Erfolgreicher Fund: Adresse passt zum gewünschten Suffix und Guthabenbedingung.
            pbar.write(f"{Fore.GREEN}{Style.BRIGHT}Erfolg! Passende Adresse gefunden!{Style.RESET_ALL}")
            pbar.write(f"{Fore.BLUE}{Style.BRIGHT}sosca: Fund!{Style.RESET_ALL}")
            pbar.write(f"{Fore.MAGENTA}Adresse: {Style.BRIGHT}{address}{Style.RESET_ALL}")
            pbar.write(f"{Fore.MAGENTA}Guthaben: {Style.BRIGHT}{balance_sol:.9f} SOL{Style.RESET_ALL}")
            pbar.write(f"{Fore.MAGENTA}Privater Schlüssel (Hex): {Style.BRIGHT}{private_key_hex}{Style.RESET_ALL}")
            pbar.write(f"{Fore.MAGENTA}Phantom-kompatibler Key: {Style.BRIGHT}{phantom_key}{Style.RESET_ALL}")
            
            entry = {
                "address": address,
                "balance_lamports": balance,
                "private_key_hex": private_key_hex,
                "phantom_key": phantom_key
            }
            save_address(entry)
            break
            
            # Kurze Pause, um die CPU nicht zu überlasten
            time.sleep(0.2)
    except KeyboardInterrupt:
        pbar.write(f"{Fore.RED}Abbruch durch Benutzer.{Style.RESET_ALL}")
    finally:
        pbar.close()

if __name__ == "__main__":
    main()
