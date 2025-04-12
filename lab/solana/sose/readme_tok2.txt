Auto-Installation:

Zu Beginn des Skripts wird mit der Funktion install_if_missing geprüft, ob die Module requests, solana und spl.token (installiert als Paket spl-token) vorhanden sind. Falls nicht, wird per subprocess.check_call eine Installation über pip angestoßen.

Token-Transfer:

Der Code rechnet anhand der eingestellten TOKEN_DECIMALS den Betrag in die kleinste Einheit um und verwendet anschließend die SPL-Token-Anweisung transfer_checked.

Abfrage im Intervall:

Mittels Endlosschleife (while True) wird alle 20 Sekunden (über CHECK_INTERVAL) die externe JSON‑Datei abgefragt und gegebenenfalls verarbeitet.

Passe vor dem Einsatz insbesondere folgende Einstellungen an:

TRANSACTIONS_URL und REMOVE_TRANSACTION_URL

SOLANA_RPC_URL

KEYPAIR_FILE

TOKEN_MINT_ADDRESS und TOKEN_DECIMALS
