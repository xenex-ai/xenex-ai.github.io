**Solana Address Generator (SAG) – a xenexAi product**

**Übersicht:**  
Dieses Python-Programm generiert fortlaufend ed25519-Schlüsselpaaren, wandelt den öffentlichen Schlüssel in eine Base58-kodierte Solana-Adresse um und prüft anschließend über die Solana JSON-RPC API den SOL-Guthaben sowie (optional) vorhandene Token-Konten. Erfolgreiche Funde – also Adressen mit einem positiven Guthaben oder mit Token – werden in der Datei `suc_address.json` gespeichert.

**Hauptfunktionen:**  
- **Adresserzeugung:**  
  Generiert in Echtzeit Solana-Wallets (ed25519) und wandelt den öffentlichen Schlüssel in das übliche Base58-Format um.
  
- **Guthaben- und Token-Abfrage:**  
  Überprüft den SOL-Guthaben (Lamports, umgerechnet in SOL) sowie vorhandene Token-Konten (falls aktiviert) jeder Adresse über den Solana Mainnet Beta RPC Endpoint.

- **Suffix-Suche:**  
  Ermöglicht die Eingabe eines Zielworts (Suffix), sodass nur Adressen berücksichtigt werden, die mit dem gewünschten Suffix enden.

- **Multithreading für hohe Geschwindigkeit:**  
  Nutzt einen dedizierten Generator-Thread und einen Pool von Worker-Threads (konfigurierbar, z. B. 16 Worker), um ca. 900 Schlüssel/Adressen pro Sekunde zu erzeugen und zu prüfen.

- **Live-Statusanzeige:**  
  Zeigt in Echtzeit über die Rich-Bibliothek Statusinformationen (letzte Adresse, geprüfte Anzahl, Fehler usw.) im Terminal an.

- **Flask-Webserver:**  
  Bietet eine Web-API (unter `http://localhost:5000/keys`), über die alle erfolgreichen Adressen inklusive privatem Schlüssel, SOL-Guthaben und Token-Konten abgerufen werden können.

- **Datenpersistenz:**  
  Speichert alle Treffer in der JSON-Datei `suc_address.json`, sodass keine erfolgreichen Ergebnisse verloren gehen.

**Abhängigkeiten:**  
- Python 3  
- Flask  
- Requests  
- PyNaCl  
- base58  
- Rich

**Verwendung:**  
1. Starte das Programm.  
2. Gib ein gewünschtes Suffix ein (oder lasse das Feld leer).  
3. Wähle, ob auch Token-Konten geprüft werden sollen (j/n).  
4. Der Generator startet und zeigt kontinuierlich den aktuellen Status an.  
5. Erfolgreiche Adressen können über den lokalen Webserver abgerufen werden.

