#!/usr/bin/env python3
import json
import logging
import sys
import time
import requests

from solana.publickey import PublicKey
from solana.keypair import Keypair
from solana.rpc.api import Client
from solana.transaction import Transaction
from solana.rpc.types import TxOpts

from spl.token.constants import TOKEN_PROGRAM_ID, ASSOCIATED_TOKEN_PROGRAM_ID
from spl.token.instructions import TransferCheckedParams, transfer_checked

# -------------------------------
# Konfiguration (anpassen!)
# -------------------------------
# URL zum Abrufen der JSON mit den Transaktionen (GET)
TRANSACTIONS_URL = "https://example.com/transactions_api.php"
# URL/Endpoint zum Entfernen eines Eintrags (DELETE oder POST)
REMOVE_TRANSACTION_URL = "https://example.com/transactions_api.php?action=delete"
# Solana Netzwerk RPC URL (z.B. Devnet, Testnet oder Mainnet)
SOLANA_RPC_URL = "https://api.devnet.solana.com"
# Dateiname des Keypair (Schlüssel muss als JSON-Array gespeichert sein)
KEYPAIR_FILE = "key.json"
# Wartezeit zwischen einzelnen Transaktionen (in Sekunden)
WAIT_SECONDS = 2
# Maximale Wiederholungsversuche für HTTP-Requests
MAX_RETRIES = 3
# Intervall für die Prüfung der JSON-Datei (alle 20 Sekunden)
CHECK_INTERVAL = 20

# Token spezifische Konfiguration
TOKEN_MINT_ADDRESS = "YourTokenMintAddressHere"  # Ersetze diesen String mit der tatsächlichen Token-Mint-Adresse
TOKEN_DECIMALS = 6  # Anzahl der Dezimalstellen des Tokens (z.B. 6 oder 9)

# Konfiguriere Logging
logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")


# -------------------------------
# Hilfsfunktionen
# -------------------------------

def load_keypair_from_file(filename: str) -> Keypair:
    """
    Lädt den Keypair aus einer JSON-Datei.
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
    Erwartet wird eine JSON-Liste im Format:
      [
        {"id": "trans1", "address": "EmpfaengerPubKey...", "amount": 100.0},
        {"id": "trans2", "address": "EmpfaengerPubKey...", "amount": 50.0}
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


def get_associated_token_address(owner: PublicKey, mint: PublicKey) -> PublicKey:
    """
    Berechnet das assoziierte Token-Konto für einen Inhaber und ein Token-Mint.
    """
    return PublicKey.find_program_address(
        [bytes(owner), bytes(TOKEN_PROGRAM_ID), bytes(mint)],
        ASSOCIATED_TOKEN_PROGRAM_ID
    )[0]


def send_token_transaction(client: Client, sender: Keypair, recipient_address: str, amount_token: float) -> str:
    """
    Sendet eine Token-Transaktion vom Sender an die Empfängeradresse.
    amount_token: Die Tokenmenge als Dezimalwert. Es wird in die kleinste Einheit (unter Berücksichtigung der TOKEN_DECIMALS) umgerechnet.
    Gibt die Transaktions-Signatur zurück oder wirft eine Exception.
    """
    try:
        mint_pubkey = PublicKey(TOKEN_MINT_ADDRESS)
        recipient_pubkey = PublicKey(recipient_address)
        
        # Berechne das assoziierte Token-Konto des Senders und des Empfängers
        sender_token_account = get_associated_token_address(sender.public_key, mint_pubkey)
        recipient_token_account = get_associated_token_address(recipient_pubkey, mint_pubkey)
        
        # Umrechnung in kleinste Einheit (z.B. wenn TOKEN_DECIMALS=6, dann 1 Token = 1_000_000 Einheiten)
        amount_in_smallest_unit = int(amount_token * (10 ** TOKEN_DECIMALS))
        
        # Erstelle die Transfer-Anweisung für SPL-Token (mit Überprüfung des Dezimalwertes)
        transfer_ix = transfer_checked(
            TransferCheckedParams(
                program_id=TOKEN_PROGRAM_ID,
                source=sender_token_account,
                mint=mint_pubkey,
                dest=recipient_token_account,
                owner=sender.public_key,
                amount=amount_in_smallest_unit,
                decimals=TOKEN_DECIMALS,
            )
        )
        
        txn = Transaction().add(transfer_ix)
        response = client.send_transaction(txn, sender, opts=TxOpts(skip_confirmation=False))
        if "result" in response:
            tx_signature = response["result"]
            logging.info(f"Token-Transaktion erfolgreich gesendet: {tx_signature}")
            return tx_signature
        else:
            raise Exception(f"Unerwartete Antwort: {response}")
    except Exception as e:
        logging.error(f"Fehler beim Senden der Token-Transaktion an {recipient_address}: {e}")
        raise


def remove_transaction_entry(entry_id: str) -> bool:
    """
    Entfernt den Eintrag mit der angegebenen ID vom externen Server.
    Hier erfolgt die Kommunikation per HTTP-POST (mit dem Parameter "action=delete").
    """
    params = {"id": entry_id}
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.post(REMOVE_TRANSACTION_URL, data=params, timeout=10)
            response.raise_for_status()
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
# Hauptlogik mit Endlosschleife
# -------------------------------

def main_loop():
    # Lade den Wallet-Keypair
    sender_keypair = load_keypair_from_file(KEYPAIR_FILE)
    logging.info(f"Keypair geladen. Absender-Adresse: {sender_keypair.public_key}")
    
    # Erstelle den Solana-Client
    client = Client(SOLANA_RPC_URL)
    
    while True:
        transactions = fetch_transactions(TRANSACTIONS_URL)
        if transactions:
            for entry in transactions:
                entry_id = entry.get("id")
                recipient_address = entry.get("address")
                amount_token = entry.get("amount")

                # Validierung der Eintragsdaten
                if not entry_id or not recipient_address or not amount_token:
                    logging.warning(f"Überspringe fehlerhaften Eintrag: {entry}")
                    continue

                logging.info(f"Bearbeite Eintrag {entry_id}: Sende {amount_token} Token an {recipient_address}")
                try:
                    tx_signature = send_token_transaction(client, sender_keypair, recipient_address, amount_token)
                    if remove_transaction_entry(entry_id):
                        logging.info(f"Eintrag {entry_id} erfolgreich entfernt.")
                    else:
                        logging.error(f"Eintrag {entry_id} konnte nicht entfernt werden.")
                except Exception as e:
                    logging.error(f"Fehler beim Verarbeiten des Eintrags {entry_id}: {e}")

                # Kurze Pause zwischen einzelnen Transaktionen
                time.sleep(WAIT_SECONDS)
        else:
            logging.info("Keine neuen Transaktionen gefunden.")
        
        logging.info("Warte auf den nächsten Prüfdurchlauf...")
        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main_loop()
