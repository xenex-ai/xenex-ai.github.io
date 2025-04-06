Hier ist ein kurzer Text, den du als readme.txt verwenden kannst:

---

**sosca v0.7.1 – Phantom Wallet Key Converter für Solana**

Dieses Python-Programm generiert ein ed25519-Schlüsselpaar und wandelt den privaten Schlüssel in mehrere Formate um, die mit Phantom Wallet kompatibel sind:

- **Solana-Adresse:**  
  Der öffentliche Schlüssel wird Base58-codiert ausgegeben (entspricht der Solana-Adresse).

- **Privater Schlüssel (Hex):**  
  Der 32-Byte private Schlüssel als Hex-String.

- **Phantom-kompatibler Private Key (64-Byte Liste):**  
  Kombination aus 32-Byte privatem und 32-Byte öffentlichem Schlüssel, als Liste ausgegeben.

- **Phantom-kompatibler Private Key (Base58):**  
  Der 64-Byte Schlüssel wird zusätzlich in einen Base58-codierten String konvertiert.

**Ablauf:**

1. Das Programm zeigt ein ASCII-Intro und fordert zur Eingabe eines gewünschten Suffix (Zielwort) für die Adresse auf.
2. Anschließend werden fortlaufend Schlüssel generiert, bis eine Adresse gefunden wird, die mit dem angegebenen Suffix endet (oder alle Adressen, falls kein Suffix definiert ist).
3. Bei einem Treffer werden alle relevanten Daten (Adresse, Hex-Schlüssel, 64-Byte Liste und Base58-Schlüssel) angezeigt und in der Datei `addresses.json` gespeichert.

**Ausführung:**

Starte das Programm mit:
```bash
python <dateiname>.py
```
Folge den Anweisungen im Terminal.

>> benutze 'BASED' als downloaddatei unter
>> https://xenex-ai.github.io/lab/solana/based/based_v1.py
>> starte, folge den Anweisungen im Terminal.
