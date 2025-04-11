#!/usr/bin/env python3
import sys
import subprocess
import logging
import json
from pathlib import Path

# Automatische Installation fehlender Pakete
def install_and_import(package_name, import_name=None):
    """
    Versucht das Modul zu importieren und installiert es bei ImportError.
    :param package_name: Name des Paketes, wie es pip kennt.
    :param import_name: Name des Moduls zum Importieren (falls abweichend)
    """
    try:
        if import_name:
            __import__(import_name)
        else:
            __import__(package_name)
    except ImportError:
        print(f"Das Paket '{package_name}' wird installiert...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package_name])
    finally:
        if import_name:
            globals()[import_name] = __import__(import_name)
        else:
            globals()[package_name] = __import__(package_name)

# Benötigte Pakete: solana und colorama
install_and_import("solana")
install_and_import("colorama")

from solana.rpc.api import Client
from solana.keypair import Keypair
from solana.transaction import Transaction
from solana.system_program import TransferParams, transfer
from solana.rpc.types import TxOpts
from colorama import init as colorama_init, Fore, Style

# Initialisiere Colorama für farbige Konsolenausgaben
colorama_init(autoreset=True)

# Logging-Konfiguration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

def load_keypair(filename: str) -> Keypair:
    """
    Lädt den privaten Schlüssel aus einer JSON-Datei und erzeugt ein Keypair.
    Erwartetes Format: Eine JSON-Liste von Integern.
    """
    try:
        path = Path(filename)
        if not path.is_file():
            raise FileNotFoundError(f"Schlüsseldatei '{filename}' wurde nicht gefunden.")
        with open(filename, "r") as key_file:
            key_data = json.load(key_file)
        secret_key = bytes(key_data)
        keypair = Keypair.from_secret_key(secret_key)
        logging.info(f"{Fore.GREEN}Keypair erfolgreich geladen. Public Key: {keypair.public_key}{Style.RESET_ALL}")
        return keypair
    except Exception as e:
        logging.error(f"Fehler beim Laden des Keypairs: {e}")
        sys.exit(1)

def load_airdrop_data(filename: str) -> list:
    """
    Lädt die Airdrop-Daten (Empfänger und Betrag) aus einer JSON-Datei.
    Erwartetes Format:
    [
      {"address": "EmpfaengerAdresse1", "amount": 0.1},
      {"address": "EmpfaengerAdresse2", "amount": 0.2}
    ]
    """
    try:
        path = Path(filename)
        if not path.is_file():
            raise FileNotFoundError(f"Airdrop-Datei '{filename}' wurde nicht gefunden.")
        with open(filename, "r") as airdrop_file:
            data = json.load(airdrop_file)
        if not isinstance(data, list):
            raise ValueError("Airdrop-Daten sollten als Liste formatiert sein.")
        logging.info(f"{Fore.GREEN}Airdrop-Daten erfolgreich geladen. Anzahl Empfänger: {len(data)}{Style.RESET_ALL}")
        return data
    except Exception as e:
        logging.error(f"Fehler beim Laden der Airdrop-Daten: {e}")
        sys.exit(1)

def send_sol(client: Client, keypair: Keypair, recipient: str, amount_sol: float):
    """
    Sendet den angegebenen SOL-Betrag (in SOL) vom Konto des Keypairs an den Empfänger.
    """
    try:
        lamports = int(amount_sol * 1_000_000_000)
        txn = Transaction().add(
            transfer(
                TransferParams(
                    from_pubkey=keypair.public_key,
                    to_pubkey=recipient,
                    lamports=lamports
                )
            )
        )
        logging.info(f"Übermittle {Fore.CYAN}{amount_sol} SOL{Style.RESET_ALL} an {Fore.YELLOW}{recipient}{Style.RESET_ALL}...")
        response = client.send_transaction(txn, keypair, opts=TxOpts(skip_preflight=True))
        logging.info(f"{Fore.GREEN}Erfolgreich versendet! Transaktions-Response: {response}{Style.RESET_ALL}")
    except Exception as e:
        logging.error(f"{Fore.RED}Fehler beim Senden an {recipient}: {e}{Style.RESET_ALL}")

def main():
    # Verbindung zum Solana Devnet herstellen
    try:
        client = Client("https://api.devnet.solana.com")
        logging.info(f"{Fore.GREEN}Verbunden mit Solana Devnet.{Style.RESET_ALL}")
    except Exception as e:
        logging.error(f"{Fore.RED}Fehler beim Verbinden mit dem Solana Devnet: {e}{Style.RESET_ALL}")
        sys.exit(1)

    # Keypair und Airdrop-Daten laden
    keypair = load_keypair("key.json")
    airdrops = load_airdrop_data("airdrop.json")

    # Iteriere über alle Empfänger und sende die angegebenen Beträge
    for entry in airdrops:
        try:
            recipient_address = entry["address"]
            amount_sol = float(entry["amount"])
            send_sol(client, keypair, recipient_address, amount_sol)
        except KeyError as e:
            logging.error(f"{Fore.RED}Fehlender Schlüssel in Airdrop-Daten: {e}{Style.RESET_ALL}")
        except Exception as e:
            logging.error(f"{Fore.RED}Unerwarteter Fehler: {e}{Style.RESET_ALL}")

if __name__ == "__main__":
    logging.info(f"{Fore.MAGENTA}Starte Solana Airdrop Tool ...{Style.RESET_ALL}")
    main()
