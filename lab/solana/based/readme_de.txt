based v.1.0 [DE]

---

# Phantom Wallet Key Converter für Solana

Dieses Python-Programm konvertiert private Schlüssel in ein Format, das von Phantom Wallet für Solana genutzt werden kann. Es unterstützt folgende Eingabeformate:

- **64-Byte-Liste:**  
  Beispiel:
  ```json
  [109, 37, 199, 5, ... , 37, 92, 133]
  ```
  Die Liste muss exakt 64 Byte enthalten.

- **Hex-String:**  
  - **32 Byte:** Nur der geheime Schlüssel wird eingegeben. Das Programm berechnet den öffentlichen Schlüssel (mit `nacl.signing`) und erstellt so den 64-Byte Phantom Key.
  - **64 Byte:** Der vollständige Phantom Key wird direkt verwendet.

**Ablauf:**

1. **Eingabe verarbeiten:**  
   Die Funktion `parse_key_input()` erkennt, ob die Eingabe eine Liste oder ein Hex-String ist, und wandelt sie in ein Byte-Array um.  
   Bei einem 32-Byte Hex-String wird automatisch der zugehörige öffentliche Schlüssel ergänzt.

2. **Base58-Kodierung:**  
   Das resultierende 64-Byte-Konstrukt wird mit der `base58`‑Bibliothek in einen Base58-codierten String umgewandelt. Dieser String entspricht dem Phantom-kompatiblen privaten Schlüssel.

3. **Ausgabe:**  
   Nach der Eingabe wird der Base58-codierte Schlüssel im Terminal ausgegeben.

**Ausführung:**  
Starte das Programm mit:
```bash
python <dateiname>.py
```
Folge der Eingabeaufforderung und gib deinen privaten Schlüssel in einem der unterstützten Formate ein. Anschließend wird der Phantom-kompatible, Base58-codierte Schlüssel angezeigt.

---
