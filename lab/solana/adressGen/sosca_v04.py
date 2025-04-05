#!/usr/bin/env python3
import os
import json
import base58
import time
import random
from nacl.signing import SigningKey
from tqdm import tqdm
from colorama import init, Fore, Style, Back
import pyfiglet

# Initialisiere farbige Terminalausgabe (automatischer Reset)
init(autoreset=True)

def ascii_intro():
    logo = pyfiglet.figlet_format("sosca v0.4", font="slant")
    intro_text = (
        f"{Fore.GREEN}{Style.BRIGHT}{logo}\n"
        f"{Fore.YELLOW}{'=' * 60}\n"
        f"{Fore.CYAN}Solana Address Generator & Scanner\n"
        f"{Fore.YELLOW}{'=' * 60}\n"
        f"{Fore.MAGENTA}Hacker Style Edition v0.4\n"
        f"{Fore.CYAN}Erstellt für alle Crypto-Enthusiasten!\n"
        f"{Fore.WHITE}{'=' * 60}\n"
    )
    print(intro_text)
    time.sleep(1)

def display_banner(message, color=Fore.CYAN):
    banner = f"*** {message} ***"
    line = "*" * len(banner)
    print(color + line)
    print(color + banner)
    print(color + line + Style.RESET_ALL)
    time.sleep(1)

def print_hacker_quote():
    quotes = [
        "Decoding the blockchain secrets...",
        "Hacking the matrix, one key at a time...",
        "Bypassing the cryptographic firewall...",
        "Infusing randomness into the algorithm...",
        "Decrypting digital pathways..."
    ]
    quote = random.choice(quotes)
    # Zufällige Farbauswahl für den Quote-Text
    colors = [Fore.LIGHTBLUE_EX, Fore.LIGHTCYAN_EX, Fore.LIGHTMAGENTA_EX]
    print(random.choice(colors) + "[sosca] " + quote)
    time.sleep(0.8)

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
    Speichert den gefundenen Eintrag (Adresse und privater Schlüssel) in der Datei addresses.json.
    Bestehende Einträge bleiben erhalten.
    """
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
    display_banner("Adresse erfolgreich gespeichert!", Fore.GREEN)

def main():
    ascii_intro()
    suffix = input(Fore.CYAN + "Bitte gib das Ziel-Suffix ein (oder leer für alle): " + Style.RESET_ALL).strip()
    if suffix:
        display_banner(f"Ziel-Suffix: {suffix}", Fore.BLUE)
    else:
        display_banner("Kein Ziel-Suffix gesetzt - alle Adressen werden akzeptiert.", Fore.BLUE)
    
    display_banner("Starte den Key Generator...", Fore.MAGENTA)
    
    pbar = tqdm(unit="Schlüssel", desc="Key-Scanner", dynamic_ncols=True)
    try:
        while True:
            print_hacker_quote()
            address, private_key = generate_address()
            pbar.update(1)
            if suffix and not address.endswith(suffix):
                continue
            
            display_banner("Passende Adresse gefunden!", Fore.GREEN)
            print(Fore.WHITE + "Adresse      : " + Fore.LIGHTYELLOW_EX + address)
            print(Fore.WHITE + "Privater Key : " + Fore.LIGHTYELLOW_EX + private_key)
            entry = {"address": address, "private_key": private_key}
            save_address(entry)
            break
            # time.sleep(0.2)  # Dieser sleep wird nicht erreicht, da wir nach dem Fund abbrechen.
    except KeyboardInterrupt:
        print(Fore.RED + "\n[!] Scan durch Benutzer abgebrochen.")
    finally:
        pbar.close()

if __name__ == "__main__":
    main()
