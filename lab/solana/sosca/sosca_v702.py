import os
import json
import base58
import time
from nacl.signing import SigningKey
from tqdm import tqdm
from colorama import init, Fore, Style


# Requirements:
# base58
# pynacl
# tqdm
# colorama

# Initialisiere colorama (automatischer Reset bei jedem Print)
init(autoreset=True)


def ascii_intro():
    intro = f"""
{Fore.GREEN}{Style.BRIGHT}
 _______  _______  _______  _______  _______ 
(  ____ \\ (  ___  )(  ____ \\ (  ____ \\ (  ___  )
| (    \/| (   ) || (    \/| (    \/| (   ) |
| (_____ | |   | || (_____ | |      | (___) |
(_____  )| |   | |(_____  )| |      |  ___  |
      ) || |   | |      ) || |      | (   ) |
/\____) || (___) |/\____) || (____/\| )   ( |
\_______)(_______)\_______)(_______/|/     \|                                                            
 sosca v0.7.2
{Style.RESET_ALL}
    """
    print(intro)


def generate_address():
    """
    Generiert ein ed25519-Schlüsselpaar, encodiert den öffentlichen Schlüssel in Base58
    (entspricht der Solana-Adresse) und gibt Adresse, privaten Schlüssel (hex-formatiert)
    sowie einen 64-Byte Private Key (als Liste) zurück, der Phantom Wallet kompatibel ist.
    """
    sk = SigningKey.generate()
    vk = sk.verify_key
    public_key = vk.encode()
    address = base58.b58encode(public_key).decode("utf-8")
    private_key = sk.encode().hex()  # 32-Byte private key in hex

    # Erzeuge einen 64-Byte Private Key für Phantom (Konkatenation von private und public key)
    phantom_bytes = sk.encode() + vk.encode()
    phantom_private_key_list = list(phantom_bytes)

    # Umwandlung des 64-Byte Private Keys in Base58
    phantom_private_key_base58 = base58.b58encode(bytes(phantom_bytes)).decode("utf-8")

    return address, private_key, phantom_private_key_list, phantom_private_key_base58


def save_address(entry, filename="addresses.json"):
    """
    Speichert den gefundenen Eintrag (Adresse, privater Schlüssel und Phantom Private Key)
    in der Datei addresses.json. Existierende Einträge bleiben erhalten.
    """
    try:
        if os.path.exists(filename):
            with open(filename, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = []
    except (json.JSONDecodeError, IOError):
        data = []

    data.append(entry)

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


def main():
    ascii_intro()
    target = input(f"{Fore.CYAN}Bitte geben Sie das Zielwort (Suffix) ein, mit dem die Adresse enden soll (oder leer für alle): {Style.RESET_ALL}").strip()
    print(f"{Fore.YELLOW}Starte die Generierung und Überprüfung der Adressen...{Style.RESET_ALL}")

    pbar = tqdm(unit="Schlüssel", dynamic_ncols=True, desc="Generiere Keys")

    try:
        while True:
            address, private_key, phantom_list, phantom_base58 = generate_address()
            pbar.update(1)

            # Filter: Falls ein Suffix angegeben wurde, wird nur weitergearbeitet, wenn die Adresse damit endet.
            if target and not address.endswith(target):
                time.sleep(0.1)
                continue

            # Erfolgreicher Fund: Adresse passt zum gewünschten Suffix.
            pbar.write(f"{Fore.GREEN}{Style.BRIGHT}Erfolg! Passende Adresse gefunden!{Style.RESET_ALL}")
            pbar.write(f"{Fore.MAGENTA}Adresse: {Style.BRIGHT}{address}{Style.RESET_ALL}")
            pbar.write(f"{Fore.MAGENTA}Privater Schlüssel (Hex): {Style.BRIGHT}{private_key}{Style.RESET_ALL}")
            pbar.write(f"{Fore.MAGENTA}Phantom-kompatibler Private Key (64-Byte Liste): {Style.BRIGHT}{phantom_list}{Style.RESET_ALL}")
            pbar.write(f"{Fore.MAGENTA}Phantom-kompatibler Private Key (Base58): {Style.BRIGHT}{phantom_base58}{Style.RESET_ALL}")

            entry = {
                "address": address,
                "private_key_hex": private_key,
                "phantom_private_key": phantom_list,
                "phantom_private_key_base58": phantom_base58
            }
            save_address(entry)
            break

    except KeyboardInterrupt:
        pbar.write(f"{Fore.RED}Abbruch durch Benutzer.{Style.RESET_ALL}")
    finally:
        pbar.close()


if __name__ == "__main__":
    main()
