import os
import json
import requests
from base64 import b64decode
from dotenv import load_dotenv

from solders.keypair import Keypair
from solders.hash import Hash
from solders.message import Message
from solders.transaction import Transaction
from solders.pubkey import Pubkey
from solders.system_program import CreateAccountParams, create_account

from solana.rpc.api import Client
from spl.token.instructions import (
    initialize_mint, InitializeMintParams,
    get_associated_token_address,
    create_associated_token_account,
    mint_to
)
from spl.token.constants import TOKEN_PROGRAM_ID, ASSOCIATED_TOKEN_PROGRAM_ID

from github import Github

# .env laden
load_dotenv()
RPC_URL       = os.getenv("SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com")
WALLET_PATH   = os.path.expanduser(os.getenv("WALLET_KEY_PATH", "~/solana/wallet_key.json"))
PINATA_KEY    = os.getenv("PINATA_API_KEY")
PINATA_SECRET = os.getenv("PINATA_SECRET_KEY")
GITHUB_TOKEN  = os.getenv("GITHUB_TOKEN")
GITHUB_OWNER  = os.getenv("GITHUB_OWNER")
GITHUB_REPO   = os.getenv("GITHUB_REPO")
GITHUB_PATH   = os.getenv("GITHUB_PATH")


def load_keypair(path: str = WALLET_PATH) -> Keypair:
    path = os.path.expanduser(path)
    with open(path, "r") as f:
        secret = json.load(f)
    if isinstance(secret, list):
        return Keypair.from_bytes(bytes(secret))
    if isinstance(secret, dict) and "secretKey" in secret:
        return Keypair.from_bytes(b64decode(secret["secretKey"]))
    raise ValueError("Unbekanntes Keypair-Format.")


def upload_file_to_pinata(filepath: str) -> str:
    url = "https://api.pinata.cloud/pinning/pinFileToIPFS"
    with open(filepath, "rb") as fp:
        files = {"file": fp}
        headers = {
            "pinata_api_key": PINATA_KEY,
            "pinata_secret_api_key": PINATA_SECRET
        }
        resp = requests.post(url, files=files, headers=headers)
    resp.raise_for_status()
    return f"https://gateway.pinata.cloud/ipfs/{resp.json()['IpfsHash']}"


def upload_json_metadata(name: str, symbol: str, description: str, image_url: str) -> str:
    url = "https://api.pinata.cloud/pinning/pinJSONToIPFS"
    metadata = {
        "name": name,
        "symbol": symbol,
        "description": description,
        "image": image_url,
        "properties": {
            "files": [{"uri": image_url, "type": "image/png"}]
        }
    }
    headers = {
        "pinata_api_key": PINATA_KEY,
        "pinata_secret_api_key": PINATA_SECRET
    }
    resp = requests.post(url, json=metadata, headers=headers)
    resp.raise_for_status()
    return f"https://gateway.pinata.cloud/ipfs/{resp.json()['IpfsHash']}"


def create_spl_token(decimals: int, amount: int) -> tuple[str, str]:
    client = Client(RPC_URL)
    wallet = load_keypair()
    mint_kp = Keypair()

    # 1) Lamports für Rent-Exemption ermitteln
    lamports_resp = client.get_minimum_balance_for_rent_exemption(82)
    # je nach Version im Dict im Feld "result" oder ".value"
    lamports = lamports_resp.get("result", getattr(lamports_resp, "value", None))

    # 2) Account anlegen
    ix_create = create_account(CreateAccountParams(
        from_pubkey=wallet.pubkey(),
        to_pubkey=mint_kp.pubkey(),                  # korrekt benannt
        lamports=lamports,
        space=82,
        program_id=Pubkey.from_string(TOKEN_PROGRAM_ID)  # String → Pubkey
    ))

    # 3) Mint initialisieren
    ix_init = initialize_mint(InitializeMintParams(
        program_id=Pubkey.from_string(TOKEN_PROGRAM_ID),
        mint=mint_kp.pubkey(),
        decimals=decimals,
        mint_authority=wallet.pubkey(),
        freeze_authority=wallet.pubkey()
    ))

    # 4) Associated Token Account erstellen
    ata = get_associated_token_address(wallet.pubkey(), mint_kp.pubkey())
    ix_ata = create_associated_token_account(
        payer=wallet.pubkey(),
        owner=wallet.pubkey(),
        mint=mint_kp.pubkey()
    )

    # 5) Tokens minten
    ix_mint = mint_to(
        program_id=Pubkey.from_string(TOKEN_PROGRAM_ID),
        mint=mint_kp.pubkey(),
        dest=ata,
        authority=wallet.pubkey(),
        amount=amount * (10 ** decimals),
        signers=[]
    )

    # 6) Transaktion zusammensetzen und absenden
    instructions = [ix_create, ix_init, ix_ata, ix_mint]
    bh_resp = client.get_latest_blockhash()
    blockhash_str = bh_resp["result"]["value"]["blockhash"]
    blockhash = Hash.from_string(blockhash_str)

    message = Message(instructions=instructions, payer=wallet.pubkey())
    tx = Transaction([wallet, mint_kp], message, blockhash)
    sig = client.send_transaction(tx)["result"]
    return str(mint_kp.pubkey()), sig


def publish_to_github(token_json: dict, filename: str) -> str:
    if not all([GITHUB_TOKEN, GITHUB_OWNER, GITHUB_REPO, GITHUB_PATH]):
        raise RuntimeError("GitHub-Credentials unvollständig.")
    gh = Github(GITHUB_TOKEN)
    repo = gh.get_user(GITHUB_OWNER).get_repo(GITHUB_REPO)
    path = f"{GITHUB_PATH}/{filename}"
    content = json.dumps(token_json, indent=2)
    try:
        existing = repo.get_contents(path)
        repo.update_file(path, "Update token metadata", content, existing.sha)
    except Exception:
        repo.create_file(path, "Add new token metadata", content)
    return f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/blob/main/{path}"

