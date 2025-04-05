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
    intro = f"""
{Fore.GREEN}{Style.BRIGHT}
   ____        _            _       
  / ___|  __ _| | ___ _   _| | __ _ 
  \___ \ / _` | |/ __| | | | |/ _` |
   ___) | (_| | | (__| |_| | | (_| |
  |____/ \__,_|_|\___|\__,_|_|\__,_|
                                    
         Solana Scanner v0.3
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

def save_address(entry, filename="addresses.json"):
    """
    Speichert den gefundenen Eintrag (Adresse und privater Schlüssel)
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
            address, private_key = generate_address()
            pbar.update(1)
            
            # Filter: Falls ein Suffix angegeben wurde, wird nur weitergearbeitet, wenn die Adresse damit endet.
            if target and not address.endswith(target):
                continue
            
            # Erfolgreicher Fund: Adresse passt zum gewünschten Suffix.
            pbar.write(f"{Fore.GREEN}{Style.BRIGHT}Erfolg! Passende Adresse gefunden!{Style.RESET_ALL}")
            pbar.write(f"{Fore.MAGENTA}Adresse: {Style.BRIGHT}{address}{Style.RESET_ALL}")
            pbar.write(f"{Fore.MAGENTA}Privater Schlüssel: {Style.BRIGHT}{private_key}{Style.RESET_ALL}")
            
            entry = {
                "address": address,
                "private_key": private_key
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
