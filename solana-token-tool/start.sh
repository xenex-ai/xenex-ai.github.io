#!/bin/bash

echo "Starte Solana SPL Token Tool..."

# .env prüfen
if [ ! -f .env ]; then
  echo "Fehler: .env-Datei fehlt. Bitte .env basierend auf .env.example erstellen."
  exit 1
fi

# Virtuelle Umgebung optional
if [ ! -d venv ]; then
  echo "Erstelle virtuelle Umgebung..."
  python3 -m venv venv
fi

# Aktivieren
source venv/bin/activate

# Abhängigkeiten installieren
echo "Installiere Python-Abhängigkeiten..."
pip install --upgrade pip
pip install -r requirements.txt

# App starten
echo "Starte Flask-App..."
python app.py

