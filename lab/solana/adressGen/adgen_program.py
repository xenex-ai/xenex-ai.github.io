import os
import json
import base58
from nacl.signing import SigningKey
from tqdm import tqdm

def generate_address():
    """
    Generiert ein ed25519-Schlüsselpaar, encodiert den öffentlichen Schlüssel in Base58
    (entspricht der Solana-Adresse) und gibt Adresse sowie privaten Schlüssel (hex-formatiert) zurück.
    """
    sk = SigningKey.generate()
    vk = sk.verify_key
    public_key = vk.encode()
    address = base58.b58encode(public_key).decode("utf-8")
    private_key = sk.encode().hex()
    return address, private_key

def save_address(address, private_key, filename="addresses.json"):
    """
    Speichert die gefundene Adresse samt privatem Schlüssel in einer JSON-Datei.
    Falls die Datei bereits existiert, wird der Eintrag angehängt.
    """
    entry = {"address": address, "private_key": private_key}
    # Vorhandene Daten laden (falls Datei existiert)
    if os.path.exists(filename):
        with open(filename, "r") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                data = []
    else:
        data = []
    # Neuen Eintrag hinzufügen
    data.append(entry)
    # Daten zurück in die Datei schreiben
    with open(filename, "w") as f:
        json.dump(data, f, indent=4)
        
def main():
    # Benutzerabfrage: Welches Wort soll die Adresse am Ende haben?
    target = input("Bitte geben Sie das Zielwort (Suffix) ein, mit dem die Adresse enden soll: ").strip()
    print(f"Suche nach einer Adresse, die mit '{target}' endet...")

    # Fortschrittsbalken initialisieren (ohne festes Gesamtziel, deshalb dynamic_ncols)
    pbar = tqdm(unit="Schlüssel", dynamic_ncols=True)
    
    try:
        while True:
            address, private_key = generate_address()
            pbar.update(1)
            # Überprüfe, ob die Adresse mit dem Zielwort endet (Groß-/Kleinschreibung beachten ggf. anpassen)
            if address.endswith(target):
                pbar.write("Passende Adresse gefunden!")
                pbar.write(f"Adresse: {address}")
                pbar.write(f"Privater Schlüssel: {private_key}")
                save_address(address, private_key)
                break
    except KeyboardInterrupt:
        pbar.write("Abbruch durch Benutzer.")
    finally:
        pbar.close()

if __name__ == "__main__":
    main()
