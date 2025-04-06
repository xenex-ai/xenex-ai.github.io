--------------------------------------------------
**Solana Address Generator (SAG) – a xenexAi product**

**Overview:**  
This Python program continuously generates ed25519 key pairs, converts the public key into a Base58-encoded Solana address, and then checks the SOL balance as well as (optionally) any token accounts via the Solana JSON-RPC API. Successful finds—i.e., addresses with a positive balance or with tokens—are stored in the file `suc_address.json`.

**Key Features:**  
- **Address Generation:**  
  Generates Solana wallets (ed25519) in real-time and converts the public key into the standard Base58 format.
  
- **Balance and Token Check:**  
  Checks the SOL balance (in lamports, converted to SOL) as well as any token accounts (if enabled) for each address using the Solana Mainnet Beta RPC Endpoint.

- **Suffix Search:**  
  Allows the input of a target suffix, so that only addresses ending with the desired suffix are considered.

- **Multithreading for High Speed:**  
  Uses a dedicated generator thread and a pool of worker threads (configurable, e.g., 16 workers) to generate and check approximately 900 keys/addresses per second.

- **Live Status Display:**  
  Displays real-time status information (last address, total checked, errors, etc.) in the terminal using the Rich library.

- **Flask Web Server:**  
  Provides a web API (available at `http://localhost:5000/keys`) to retrieve all successful addresses along with their private keys, SOL balance, and token accounts.

- **Data Persistence:**  
  Saves all successful entries in the JSON file `suc_address.json`, ensuring that no successful results are lost.

**Dependencies:**  
- Python 3  
- Flask  
- Requests  
- PyNaCl  
- base58  
- Rich

**Usage:**  
1. Run the program.  
2. Enter a desired suffix (or leave the field empty).  
3. Choose whether to also check token accounts (y/n).  
4. The generator will start and continuously display the current status.  
5. Successful addresses can be retrieved via the local web server.

--------------------------------------------------
