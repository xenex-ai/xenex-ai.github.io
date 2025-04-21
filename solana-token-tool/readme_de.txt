=== Solana Token Tool (by xenexAi) ===

Dieses Tool erstellt SPL-Tokens auf Solana inklusive Metadaten & Bild über Pinata.

VORAUSSETZUNGEN:
----------------
- Python 3.10 oder 3.11 (nicht 3.12!)
- Solana-CLI installiert
- Zugang zu Pinata (API Key + Secret)
- Optional: GitHub Token für Metadaten-Publikation

INSTALLATION:
-------------
1. Projekt klonen:
   git clone https://github.com/dein-user/solana-token-tool.git
   cd solana-token-tool

2. Python-Umgebung einrichten:
   python3.11 -m venv xenex
   source xenex/bin/activate
   pip install -r requirements.txt

3. Datei `.env` anlegen und füllen:
   PINATA_API_KEY=dein_api_key
   PINATA_SECRET_API_KEY=dein_secret
   GITHUB_TOKEN=ghp_xxx
   GITHUB_REPO=dein-user/token-metadata-repo
   GITHUB_BRANCH=main

VORBEREITUNG:
-------------
- Wallet erstellen:
    solana-keygen new
- Devnet wählen:
    solana config set --url https://api.devnet.solana.com
- Optional: Devnet SOL über https://faucet.solana.com

TOKEN ERSTELLEN:
----------------
Beispiel:

    python3 app.py \
      --name "XenTest" \
      --symbol "XTS" \
      --description "xenexAi SPL test-token (xenexAi.com)" \
      --image "tokenlogo.png" \
      --decimals 9 \
      --amount 1000

SCHRITTE:
---------
1. Bild wird zu Pinata hochgeladen
2. JSON-Metadaten erstellt und hochgeladen
3. SPL-Token erstellt (Mint-Adresse & Metadata)
4. Optional: Metadaten auf GitHub veröffentlicht

AUSGABE:
--------
→ Mint-Adresse: [mint_pubkey]
→ Metadata-PDA: [pda]
→ Transaktions-Signatur: [tx_signature]
→ Metadaten-URL: https://gateway.pinata.cloud/ipfs/...

HINWEISE:
---------
- Bildgröße unter 1MB empfohlen (PNG oder JPG)
- decimals = 9 entspricht Standard bei Solana
- Fehler mit "Signature is not JSON serializable" ist behoben

Support & Projektseite:
-----------------------
https://xenexAi.com

