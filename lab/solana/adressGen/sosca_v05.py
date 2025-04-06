import os
import json
import base58
import time
from nacl.signing import SigningKey
from tqdm import tqdm
from colorama import init, Fore, Style

# Initialisiere colorama (automatischer Reset bei jedem Print)
init(autoreset=True)

def ascii_intro():
    banner = f"""
{Fore.GREEN}{Style.BRIGHT}
____        _            _       
/ ___|  __ _| | ___ _   _| | __ _ 
\___ \ / _` | |/ __| | | | |/ _` |
 ___) | (_| | | (__| |_| | | (_| |
|____/ \__,_|_|\___|\__,_|_|\__,_|
                                    
         sosca v.0.5
{Style.RESET_ALL}
    """
    print(banner)

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
    print(f"{Fore.YELLOW}Starte die Generierung und Überprüfung der Adressen...{Style.RESET_ALL}")
    
    pbar = tqdm(unit="Schlüssel", dynamic_ncols=True, desc="Generiere Keys")
    
    try:
        while True:
            address, private_key_hex, phantom_key = generate_address()
            pbar.update(1)
            
            # Filter: Falls ein Suffix angegeben wurde, wird nur weitergearbeitet, wenn die Adresse damit endet.
            if target and not address.endswith(target):
                continue
            
            # Erfolgreicher Fund: Adresse passt zum gewünschten Suffix.
            pbar.write(f"{Fore.GREEN}{Style.BRIGHT}Erfolg! Passende Adresse gefunden!{Style.RESET_ALL}")
            pbar.write(f"{Fore.BLUE}{Style.BRIGHT}sosca: Fund!{Style.RESET_ALL}")
            pbar.write(f"{Fore.MAGENTA}Adresse: {Style.BRIGHT}{address}{Style.RESET_ALL}")
            pbar.write(f"{Fore.MAGENTA}Privater Schlüssel (Hex): {Style.BRIGHT}{private_key_hex}{Style.RESET_ALL}")
            pbar.write(f"{Fore.MAGENTA}Phantom-kompatibler Key: {Style.BRIGHT}{phantom_key}{Style.RESET_ALL}")
            
            entry = {
                "address": address,
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
