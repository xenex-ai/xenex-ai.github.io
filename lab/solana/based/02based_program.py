import base58
import json
from nacl.signing import SigningKey

def parse_key_input(user_input):
    """
    Versucht, den eingegebenen Schlüssel zu parsen.
    Unterstützt:
      - Eine 64-Byte-Liste, z.B.:
        [109, 37, 199, 5, 218, 244, 52, 181, 74, 168, 197, 177, 148, 69, 254, 237,
         240, 143, 194, 252, 69, 175, 61, 83, 207, 145, 111, 192, 153, 210, 249, 18,
         8, 74, 182, 241, 147, 74, 216, 97, 2, 48, 105, 188, 114, 103, 200, 174,
         4, 123, 32, 167, 202, 224, 238, 150, 240, 78, 185, 90, 210, 124, 37, 92, 133]
      - Einen Hex‑String:
        • 32‑Byte (nur geheimer Schlüssel) – dann wird der öffentliche Schlüssel berechnet und
          mitverknüpft (ergibt den 64‑Byte Phantom Key)
        • 64‑Byte (vollständiger Phantom Key)
    """
    user_input = user_input.strip()
    
    # Falls Eingabe eine Liste ist:
    if user_input.startswith('[') and user_input.endswith(']'):
        try:
            key_list = json.loads(user_input)
            if not all(isinstance(x, int) for x in key_list):
                raise ValueError("Alle Elemente müssen ganze Zahlen sein.")
            key_bytes = bytes(key_list)
            if len(key_bytes) != 64:
                raise ValueError("Die Liste muss exakt 64 Byte enthalten, aktuell: " + str(len(key_bytes)))
            return key_bytes
        except Exception as e:
            raise ValueError("Fehler beim Parsen der Liste: " + str(e))
    else:
        # Andernfalls gehen wir von einem Hex-String aus.
        if user_input.lower().startswith("0x"):
            user_input = user_input[2:]
        user_input = user_input.replace(" ", "")
        try:
            key_bytes = bytes.fromhex(user_input)
        except Exception as e:
            raise ValueError("Fehler beim Parsen des Hex-Strings: " + str(e))
        
        if len(key_bytes) == 32:
            # 32 Byte = geheimer Schlüssel; ergänze den öffentlichen Schlüssel
            sk = SigningKey(key_bytes)
            vk = sk.verify_key
            full_key = sk.encode() + vk.encode()
            return full_key
        elif len(key_bytes) == 64:
            return key_bytes
        else:
            raise ValueError("Der Hex-String muss 32 oder 64 Byte enthalten, aktuell: " + str(len(key_bytes)))

def main():
    print("===========================================")
    print(" Phantom Wallet Key Converter für Solana")
    print("===========================================")
    print("Unterstützte Eingabeformate:")
    print(" 1) 64-Byte-Liste, z.B.:")
    print("    [109, 37, 199, 5, 218, 244, 52, 181, 74, 168, 197, 177, 148, 69, 254, 237,")
    print("     240, 143, 194, 252, 69, 175, 61, 83, 207, 145, 111, 192, 153, 210, 249, 18,")
    print("     8, 74, 182, 241, 147, 74, 216, 97, 2, 48, 105, 188, 114, 103, 200, 174,")
    print("     4, 123, 32, 167, 202, 224, 238, 150, 240, 78, 185, 90, 210, 124, 37, 92, 131]")
    print("")
    print(" 2) Hex-String:")
    print("    • 32-Byte (nur geheimer Schlüssel) z.B.:")
    print("       6d25c705daf434b54aa8c5b19445feedf08fc2fc45af3d53cf916fc099d2f9af")
    print("    • 64-Byte (vollständiger Phantom Key) z.B.:")
    print("       <64-Byte Hex-String>")
    print("")
    
    user_input = input("Bitte gib deinen privaten Schlüssel ein: ")

    try:
        key_bytes = parse_key_input(user_input)
    except ValueError as e:
        print("Fehler:", e)
        return

    base58_encoded = base58.b58encode(key_bytes).decode('utf-8')
    
    print("\nBase58-codierter privater Schlüssel (Phantom-kompatibel):")
    print(base58_encoded)

if __name__ == "__main__":
    main()
