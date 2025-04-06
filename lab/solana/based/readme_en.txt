---

based v.1.0 [EN]

---

# Phantom Wallet Key Converter for Solana

This Python program converts private keys into a format that can be used by Phantom Wallet for Solana. It supports the following input formats:

- **64-Byte List:**  
  Example:
  ```json
  [109, 37, 199, 5, ... , 37, 92, 133]
  ```
  The list must contain exactly 64 bytes.

- **Hex String:**  
  - **32 Byte:** Only the private key is provided. The program calculates the public key (using `nacl.signing`) and creates the 64-byte Phantom Key.
  - **64 Byte:** The complete Phantom Key is used directly.

**Process:**

1. **Input Processing:**  
   The `parse_key_input()` function determines whether the input is a list or a hex string and converts it into a byte array.  
   For a 32-byte hex string, the corresponding public key is automatically appended.

2. **Base58 Encoding:**  
   The resulting 64-byte construct is converted into a Base58-encoded string using the `base58` library. This string corresponds to the Phantom-compatible private key.

3. **Output:**  
   After processing the input, the Base58-encoded key is displayed in the terminal.

**Execution:**  
Start the program with:
```bash
python <filename>.py
```
Follow the prompt to enter your private key in one of the supported formats. The Phantom-compatible, Base58-encoded key will then be displayed.

---
