import base58
import json

def parse_key_input(user_input):
    """
    Versucht, den eingegebenen Schlüssel zu parsen.
    Unterstützt:
      - Eine 64-Byte-Liste (z.B. [109, 37, 199, ...])
      - Einen Hex-String (z.B. 6d25c705daf434b54aa8c5b19445feedf08fc2fc45af3d53cf916fc099d2f9bc)
    """
    user_input = user_input.strip()
    
    # Prüfen, ob es sich um eine Liste handelt (beginnt mit '[' und endet mit ']')
    if user_input.startswith('[') and user_input.endswith(']'):
        try:
            # JSON-Parsing wandelt die Eingabe in eine Liste um
            key_list = json.loads(user_input)
            if isinstance(key_list, list) and all(isinstance(x, int) for x in key_list):
                return bytes(key_list)
            else:
                raise ValueError("Die Eingabe ist keine gültige Liste von ganzen Zahlen.")
        except Exception as e:
            raise ValueError("Fehler beim Parsen der Liste: " + str(e))
    else:
        # Andernfalls behandeln wir es als Hex-String.
        # Entferne ein mögliches "0x" Präfix und Leerzeichen.
        if user_input.lower().startswith("0x"):
            user_input = user_input[2:]
        user_input = user_input.replace(" ", "")
        try:
            return bytes.fromhex(user_input)
        except Exception as e:
            raise ValueError("Fehler beim Parsen des Hex-Strings: " + str(e))

def main():
    print("===========================================")
    print("   Base58-Konverter für private Schlüssel   ")
    print("===========================================")
    print("Unterstützte Formate:")
    print("  1) 64-Byte-Liste, z.B.:")
    print("     [109, 37, 199, 5, 218, 244, 52, 181, 74, 168, 197, 177, 148, 69, 254, 237,")
    print("      240, 143, 194, 252, 69, 175, 61, 83, 207, 145, 111, 192, 153, 210, 249, 18,")
    print("      8, 74, 182, 241, 147, 74, 216, 97, 2, 48, 105, 188, 114, 103, 200, 174,")
    print("      4, 123, 32, 167, 202, 224, 238, 150, 240, 78, 185, 90, 210, 124, 37, 92, 131]")
    print("")
    print("  2) Hex-String (32 Byte), z.B.:")
    print("6d25c705daf434b54aa8c5b19445feedf08fc2fc45af3d53cf916fc099d2f9ad")
    print("")
    
    user_input = input("Bitte gib deinen privaten Schlüssel ein: ")

    try:
        key_bytes = parse_key_input(user_input)
    except ValueError as e:
        print("Fehler:", e)
        return

    base58_encoded = base58.b58encode(key_bytes).decode('utf-8')
    
    print("\nBase58-codierter privater Schlüssel:")
    print(base58_encoded)

if __name__ == "__main__":
    main()
