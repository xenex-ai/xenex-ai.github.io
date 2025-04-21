#!/usr/bin/env python3
import os
import json
import argparse
import requests
from base64 import b64decode
from dotenv import load_dotenv

from solders.keypair import Keypair
from solders.hash import Hash
from solders.message import Message
from solders.transaction import Transaction
from solders.pubkey import Pubkey
from solders.system_program import CreateAccountParams, create_account
from solders.instruction import Instruction, AccountMeta

from solana.rpc.api import Client
from spl.token.instructions import (
    initialize_mint, InitializeMintParams,
    get_associated_token_address,
    create_associated_token_account,
    mint_to, MintToParams
)
from spl.token.constants import TOKEN_PROGRAM_ID

from borsh_construct import (
    CStruct, U8, U16, U64, String, Option, Vec, Bool
)
from construct import Bytes as RawBytes

from github import Github

# Lade Umgebungsvariablen
load_dotenv()
RPC_URL       = os.getenv("SOLANA_RPC_URL",       "https://api.mainnet-beta.solana.com")
WALLET_PATH   = os.path.expanduser(os.getenv("WALLET_KEY_PATH", "~/solana/wallet_key.json"))
PINATA_KEY    = os.getenv("PINATA_API_KEY")
PINATA_SECRET = os.getenv("PINATA_SECRET_KEY")
GITHUB_TOKEN  = os.getenv("GITHUB_TOKEN")
GITHUB_OWNER  = os.getenv("GITHUB_OWNER")
GITHUB_REPO   = os.getenv("GITHUB_REPO")
GITHUB_PATH   = os.getenv("GITHUB_PATH")

# Metaplex Token Metadata Program ID
METADATA_PROGRAM_ID = Pubkey.from_string("metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s")

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
    print("Lade Bild zu Pinata hoch…")
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
    print("Erstelle Metadaten-JSON und lade zu Pinata hoch…")
    url = "https://api.pinata.cloud/pinning/pinJSONToIPFS"
    metadata = {
        "name": name,
        "symbol": symbol,
        "description": description,
        "image": image_url,
        "properties": {"files": [{"uri": image_url, "type": "image/png"}]}
    }
    headers = {
        "pinata_api_key": PINATA_KEY,
        "pinata_secret_api_key": PINATA_SECRET
    }
    resp = requests.post(url, json=metadata, headers=headers)
    resp.raise_for_status()
    return f"https://gateway.pinata.cloud/ipfs/{resp.json()['IpfsHash']}"

def create_spl_token_with_metadata(
    name: str,
    symbol: str,
    description: str,
    image_url: str,
    metadata_url: str,
    decimals: int,
    amount: int
) -> tuple[str, str]:
    print("Erstelle SPL‑Token und Metadaten auf Solana…")
    client = Client(RPC_URL)
    wallet = load_keypair()
    mint_kp = Keypair()

    # 1) Mint-Account anlegen
    rent = client.get_minimum_balance_for_rent_exemption(82).value
    ix_create = create_account(CreateAccountParams(
        from_pubkey=wallet.pubkey(),
        to_pubkey=mint_kp.pubkey(),
        lamports=rent,
        space=82,
        owner=Pubkey.from_string(str(TOKEN_PROGRAM_ID))
    ))
    # 2) Mint initialisieren
    ix_init = initialize_mint(InitializeMintParams(
        program_id=Pubkey.from_string(str(TOKEN_PROGRAM_ID)),
        mint=mint_kp.pubkey(),
        decimals=decimals,
        mint_authority=wallet.pubkey(),
        freeze_authority=wallet.pubkey()
    ))
    # 3) ATA erstellen
    ata = get_associated_token_address(wallet.pubkey(), mint_kp.pubkey())
    ix_ata = create_associated_token_account(
        payer=wallet.pubkey(),
        owner=wallet.pubkey(),
        mint=mint_kp.pubkey()
    )
    # 4) Token minten
    ix_mint = mint_to(MintToParams(
        program_id=Pubkey.from_string(str(TOKEN_PROGRAM_ID)),
        mint=mint_kp.pubkey(),
        dest=ata,
        amount=amount * (10 ** decimals),
        mint_authority=wallet.pubkey(),
        signers=[]
    ))

    # 5) Metaplex Metadata Instruction (CreateMetadataAccountV3)
    schema = CStruct(
        "discriminator" / U8,
        "data" / CStruct(
            "name"      / String,
            "symbol"    / String,
            "uri"       / String,
            "sellerFeeBasisPoints" / U16,
            "creators"  / Option(Vec(CStruct(
                "address"  / RawBytes(32),
                "verified" / Bool,
                "share"    / U8
            ))),
            "collection" / Option(CStruct(
                "verified" / Bool,
                "key"      / RawBytes(32)
            )),
            "uses" / Option(CStruct(
                "useMethod" / U8,
                "remaining" / U64,
                "total"     / U64
            )),
        ),
        "isMutable" / Bool,
        "collectionDetails" / Option(CStruct(
            "key"  / RawBytes(32),
            "size" / U64
        ))
    )
    instr_data = schema.build({
        "discriminator": 33,
        "data": {
            "name": name,
            "symbol": symbol,
            "uri": metadata_url,
            "sellerFeeBasisPoints": 500,
            "creators": [{
                "address": bytes(wallet.pubkey()),
                "verified": True,
                "share": 100
            }],
            "collection": None,
            "uses": None
        },
        "isMutable": True,
        "collectionDetails": None
    })

    metadata_pda, _ = Pubkey.find_program_address(
        [b"metadata", bytes(METADATA_PROGRAM_ID), bytes(mint_kp.pubkey())],
        METADATA_PROGRAM_ID
    )

    accounts = [
        AccountMeta(pubkey=metadata_pda, is_signer=False, is_writable=True),
        AccountMeta(pubkey=mint_kp.pubkey(), is_signer=False, is_writable=True),
        AccountMeta(pubkey=wallet.pubkey(), is_signer=True,  is_writable=False),
        AccountMeta(pubkey=wallet.pubkey(), is_signer=True,  is_writable=True),
        AccountMeta(pubkey=wallet.pubkey(), is_signer=False, is_writable=False),
        AccountMeta(pubkey=Pubkey.from_string("11111111111111111111111111111111"), is_signer=False, is_writable=False),
        AccountMeta(pubkey=Pubkey.from_string("SysvarRent111111111111111111111111111111111"), is_signer=False, is_writable=False),
    ]
    ix_metadata = Instruction(METADATA_PROGRAM_ID, instr_data, accounts)

    # 6) Transaktion bauen & senden
    blockhash = Hash.from_string(str(client.get_latest_blockhash().value.blockhash))
    msg = Message(
        instructions=[ix_create, ix_init, ix_ata, ix_mint, ix_metadata],
        payer=wallet.pubkey()
    )
    tx = Transaction([wallet, mint_kp], msg, blockhash)
    res = client.send_transaction(tx)
    sig = res.value  # SendTransactionResp.value enthält Signature
    print(f"→ Mint-Adresse: {mint_kp.pubkey()}")
    print(f"→ Metadata-PDA: {metadata_pda}")
    print(f"→ Transaktions-Sig: {sig}")
    return str(mint_kp.pubkey()), str(sig)


def publish_to_github(token_json: dict, filename: str) -> str:
    if not all([GITHUB_TOKEN, GITHUB_OWNER, GITHUB_REPO, GITHUB_PATH]):
        raise RuntimeError("GitHub-Credentials unvollständig.")
    print("Veröffentliche Metadaten auf GitHub…")
    gh   = Github(GITHUB_TOKEN)
    repo = gh.get_user(GITHUB_OWNER).get_repo(GITHUB_REPO)
    path = f"{GITHUB_PATH}/{filename}"
    content = json.dumps(token_json, indent=2)
    try:
        existing = repo.get_contents(path)
        repo.update_file(path, "Update token metadata", content, existing.sha)
    except Exception:
        repo.create_file(path, "Add new token metadata", content)
    return f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/blob/main/{path}"


def main():
    parser = argparse.ArgumentParser(
        description="Erstelle und veröffentliche einen SPL‑Token mit Metaplex‑Metadata."
    )
    parser.add_argument("--name",        required=True, help="Name des Tokens")
    parser.add_argument("--symbol",      required=True, help="Symbol des Tokens")
    parser.add_argument("--description", required=True, help="Beschreibung")
    parser.add_argument("--image",       required=True, help="Pfad zur Bilddatei")
    parser.add_argument("--decimals",    type=int, required=True, help="Dezimalstellen")
    parser.add_argument("--amount",      type=int, required=True, help="Anzahl")
    args = parser.parse_args()

    img_url  = upload_file_to_pinata(args.image)
    meta_url = upload_json_metadata(args.name, args.symbol, args.description, img_url)
    mint_address, tx_sig = create_spl_token_with_metadata(
        args.name, args.symbol, args.description,
        img_url, meta_url, args.decimals, args.amount
    )

    token_json = {
        "name":        args.name,
        "symbol":      args.symbol,
        "description": args.description,
        "image":       img_url,
        "metadata":    meta_url,
        "mint":        mint_address,
        "tx_sig":      str(tx_sig),  # Serialisierbarer String
    }
    filename = f"{args.symbol}_{mint_address}.json"
    gh_url = publish_to_github(token_json, filename)
    print("Fertig! GitHub URL:", gh_url)

if __name__ == "__main__":
    main()

