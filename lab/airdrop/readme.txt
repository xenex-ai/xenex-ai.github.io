Hier folgt der komplette, professionelle Python‑Code. Dieses Skript sorgt dafür, dass zur Programmausführung automatisch alle benötigten Bibliotheken (u. a. solana‑py und colorama) installiert werden, falls sie fehlen. Es implementiert erweiterte Fehlerbehandlungen und eine ansprechende visuelle Ausgabe.

Kopiere den folgenden Code in eine Datei (z. B. `solana_airdrop.py`) und führe ihn mit Python aus.

### Hinweise zum Einsatz

- **Dateien:**  
  - **key.json:** Enthält deinen privaten Schlüssel als JSON‑Liste (z. B. `[12, 34, 56, ...]`).  
  - **airdrop.json:** Enthält die Airdrop-Daten. Beispiel:
    ```json
    [
      {"address": "EmpfaengerAdresse1", "amount": 0.1},
      {"address": "EmpfaengerAdresse2", "amount": 0.2}
    ]
    ```

- **Devnet:**  
  Das Skript stellt eine Verbindung zum Devnet her (`https://api.devnet.solana.com`), sodass du dein Programm testen kannst, ohne echtes Geld zu verwenden.

- **Fehlerbehandlung:**  
  Es werden verschiedene Fehlerfälle abgefangen, beispielsweise fehlende Dateien oder fehlerhafte Dateneinträge, und es wird eine aussagekräftige Logging-Ausgabe erzeugt.

- **Automatische Paketinstallation:**  
  Bereits beim Start prüft das Skript, ob die notwendigen Bibliotheken installiert sind. Falls nicht, werden sie automatisch nachinstalliert.
