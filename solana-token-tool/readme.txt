=== Solana Token Tool (by xenexAi) ===

This tool creates SPL tokens on the Solana blockchain,
including metadata and token image uploaded via Pinata.

--------------------------------------------------------
REQUIREMENTS:
--------------------------------------------------------
- Python 3.10 or 3.11 (NOT 3.12!)
- Solana CLI installed
- Pinata account with API Key + Secret
- Optional: GitHub Token for metadata publishing

--------------------------------------------------------
INSTALLATION:
--------------------------------------------------------
1. Clone the project:
   git clone https://github.com/your-user/solana-token-tool.git
   cd solana-token-tool

2. Set up a Python virtual environment:
   python3.11 -m venv xenex
   source xenex/bin/activate
   pip install -r requirements.txt

3. Create a `.env` file and add your credentials:
   PINATA_API_KEY=your_api_key
   PINATA_SECRET_API_KEY=your_secret
   GITHUB_TOKEN=ghp_xxx
   GITHUB_REPO=your-user/token-metadata-repo
   GITHUB_BRANCH=main

--------------------------------------------------------
PREPARATION:
--------------------------------------------------------
- Create a wallet:
    solana-keygen new

- Switch to Devnet:
    solana config set --url https://api.devnet.solana.com

- Optional: Get free Devnet SOL from:
    https://faucet.solana.com

--------------------------------------------------------
TOKEN CREATION EXAMPLE:
--------------------------------------------------------
   python3 app.py \
     --name "XenTest" \
     --symbol "XTS" \
     --description "xenexAi SPL test-token (xenexAi.com)" \
     --image "tokenlogo.png" \
     --decimals 9 \
     --amount 1000

--------------------------------------------------------
PROCESS OVERVIEW:
--------------------------------------------------------
1. Uploads image to Pinata
2. Creates and uploads metadata JSON to Pinata
3. Creates SPL token (Mint address and Metadata)
4. Optionally publishes metadata to GitHub

--------------------------------------------------------
OUTPUT:
--------------------------------------------------------
→ Mint Address:       [mint_pubkey]
→ Metadata PDA:       [metadata_pda]
→ Transaction Sig:    [tx_signature]
→ Metadata URL:       https://gateway.pinata.cloud/ipfs/...

--------------------------------------------------------
NOTES:
--------------------------------------------------------
- Use image files < 1MB (PNG or JPG)
- "decimals=9" is standard for Solana tokens
- Error "Signature is not JSON serializable" is fixed

--------------------------------------------------------
PROJECT & SUPPORT:
--------------------------------------------------------
Visit: https://xenexAi.com
