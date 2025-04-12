#!/usr/bin/env python3
import json
import logging
import sys
import time
from pathlib import Path

import requests
from solana.publickey import PublicKey
from solana.keypair import Keypair
from solana.rpc.api import Client
from solana.transaction import Transaction
from solana.system_program import TransferParams, transfer
from solana.rpc.types import TxOpts

# -------------------------------
# Konfiguration (anpassen!)
# -------------------------------
# URL zum Abrufen der JSON mit den Transaktionen (GET)
TRANSACTIONS_URL = "https://example.com/transactions_api.php"
# URL/Endpoint zum Entfernen eines Eintrags (DELETE oder POST)
REMOVE_TRANSACTION_URL = "https://example.com/transactions_api.php?action=delete"
# Solana Netzwerk RPC URL (z.B. Devnet, Testnet oder Mainnet)
SOLANA_RPC_URL = "https://api.devnet.solana.com"
# Dateiname des Keypair (Schlüssel muss als JSON Array gespeichert sein)
KEYPAIR_FILE = "key.json"
# Wartezeit zwischen einzelnen Versuchen/Transaktionen (in Sekunden)
WAIT_SECONDS = 2
# Maximale Wiederholungsversuche für HTTP-Requests
MAX_RETRIES = 3

# Konfiguriere Logging (kannst du anpassen, um z.B. in eine Datei zu loggen)
logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")


# -------------------------------
# Hilfsfunktionen
# -------------------------------

def load_keypair_from_file(filename: str) -> Keypair:
    """
    Lädt den Keypair aus einer JSON Datei.
    Die Datei sollte ein JSON-Array mit 64 Integer-Werten enthalten.
    """
    try:
        with open(filename, "r") as f:
            secret = json.load(f)
        keypair = Keypair.from_secret_key(bytes(secret))
        return keypair
    except Exception as e:
        logging.error(f"Fehler beim Laden des Keypairs aus {filename}: {e}")
        sys.exit(1)


def fetch_transactions(url: str) -> list:
    """
    Holt die Transaktionsliste von der externen URL.
    Erwartet eine JSON-Liste im Format:
      [
        {"id": "trans1", "address": "Fq...", "amount": 0.1},
        {"id": "trans2", "address": "Es...", "amount": 0.2}
      ]
    """
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            if isinstance(data, list):
                logging.info("Transaktionsliste erfolgreich abgerufen.")
                return data
            else:
                logging.error("Fehlerhafte Struktur der abgerufenen Daten.")
                break
        except Exception as e:
            logging.error(f"Versuch {attempt}: Fehler beim Abrufen der Transaktionen: {e}")
            time.sleep(1)
    return []


def send_sol_transaction(client: Client, sender: Keypair, to_address: str, amount_sol: float) -> str:
    """
    Sendet eine SOL-Transaktion vom Sender an die Zieladresse.
    amount_sol: Betrag in SOL (1 SOL = 1_000_000_000 Lamports).
    Gibt die Transaktions-Signatur zurück oder wirft eine Exception.
    """
    try:
        lamports = int(amount_sol * 1_000_000_000)
        receiver_pubkey = PublicKey(to_address)
        # Transfer-Anweisung erstellen
        transfer_instruction = transfer(
            TransferParams(
                from_pubkey=sender.public_key,
                to_pubkey=receiver_pubkey,
                lamports=lamports,
            )
        )
        txn = Transaction().add(transfer_instruction)
        response = client.send_transaction(txn, sender, opts=TxOpts(skip_confirmation=False))
        # Überprüfe, ob ein Ergebnis zurückkam
        if "result" in response:
            tx_signature = response["result"]
            logging.info(f"Transaktion erfolgreich gesendet: {tx_signature}")
            return tx_signature
        else:
            raise Exception(f"Unerwartete Antwort: {response}")
    except Exception as e:
        logging.error(f"Fehler beim Senden der Transaktion an {to_address}: {e}")
        raise


def remove_transaction_entry(entry_id: str) -> bool:
    """
    Entfernt den Eintrag mit der angegebenen ID vom externen Server.
    Hier wird entweder per HTTP DELETE oder per POST (mit dem Parameter "action=delete")
    kommuniziert, abhängig von der Server-Implementierung.
    """
    params = {"id": entry_id}
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            # Hier als POST: Falls der Server DELETE nicht unterstützt, ändere dies ab.
            response = requests.post(REMOVE_TRANSACTION_URL, data=params, timeout=10)
            response.raise_for_status()
            # Überprüfe den Server-Rückgabewert (hier wird angenommen, dass { "success": true } zurückkommt)
            result = response.json()
            if result.get("success") is True:
                logging.info(f"Eintrag {entry_id} erfolgreich entfernt.")
                return True
            else:
                logging.error(f"Server meldet Fehler beim Entfernen des Eintrags {entry_id}: {result}")
        except Exception as e:
            logging.error(f"Versuch {attempt}: Fehler beim Entfernen des Eintrags {entry_id}: {e}")
            time.sleep(1)
    return False


# -------------------------------
# Hauptlogik
# -------------------------------

def main():
    # Lade den Wallet-Keypair
    sender_keypair = load_keypair_from_file(KEYPAIR_FILE)
    logging.info(f"Keypair geladen. Absender-Adresse: {sender_keypair.public_key}")
    
    # Erstelle den Solana-Client
    client = Client(SOLANA_RPC_URL)

    # Hole die Liste der Transaktionen
    transactions = fetch_transactions(TRANSACTIONS_URL)
    if not transactions:
        logging.info("Keine Transaktionen vorhanden oder Fehler beim Abruf der Daten.")
        return

    # Verarbeite jeden gültigen Transaktionseintrag
    for entry in transactions:
        entry_id = entry.get("id")
        recipient_address = entry.get("address")
        amount_sol = entry.get("amount")

        # Validierung der Eintragsdaten
        if not entry_id or not recipient_address or not amount_sol:
            logging.warning(f"Überspringe fehlerhaften Eintrag: {entry}")
            continue

        logging.info(f"Bearbeite Eintrag {entry_id}: Sende {amount_sol} SOL an {recipient_address}")
        try:
            tx_signature = send_sol_transaction(client, sender_keypair, recipient_address, amount_sol)
            # Bestätige die Transaktion (optional: weitere Checks, falls nötig)
            # Beispiel: Warte kurz oder prüfe den Transaktionsstatus
            
            # Entferne den Eintrag auf dem Server
            if remove_transaction_entry(entry_id):
                logging.info(f"Eintrag {entry_id} entfernt.")
            else:
                logging.error(f"Eintrag {entry_id} konnte nicht entfernt werden.")
        except Exception as e:
            logging.error(f"Fehler beim Verarbeiten des Eintrags {entry_id}: {e}")

        # Kurze Pause, um z.B. Netzwerklasten zu reduzieren
        time.sleep(WAIT_SECONDS)


if __name__ == "__main__":
    main()
