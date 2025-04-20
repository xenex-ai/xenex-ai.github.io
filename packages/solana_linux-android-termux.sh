#!/data/data/com.termux/files/usr/bin/bash

echo "[XenexGit] Starte Solana-Entwicklungsumgebung Setup..."

# 1) Termux-Pakete aktualisieren
echo "[1/10] Aktualisiere Termux-Pakete..."
pkg update -y && pkg upgrade -y

# 2) proot-distro & Git installieren
echo "[2/10] Installiere proot-distro und Git..."
pkg install -y proot-distro git

# 3) Ubuntu installieren, falls nicht vorhanden
if ! proot-distro list | grep -qx 'ubuntu'; then
  echo "[3/10] Installiere Ubuntu via proot-distro..."
  proot-distro install ubuntu
else
  echo "[3/10] Ubuntu bereits installiert – überspringe."
fi

# 4–10) In Ubuntu einrichten und interaktive Shell starten
proot-distro login ubuntu -- bash -lc "
set -e

echo '[4/10] Update Ubuntu-Pakete...'
apt update && apt upgrade -y

echo '[5/10] Installiere System‑Dependencies (ohne APT-npm)...'
apt install -y \
  curl wget git \
  python3 python3-pip python3-venv \
  build-essential pkg-config libssl-dev libudev-dev clang make \
  ca-certificates xz-utils \
  rustc cargo

echo '[6/10] Node.js 18.x (ARM64) installieren (inkl. npm automatisch)...'
curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
  && apt install -y nodejs

# (Optional: Sollte npm fehlen -> manuell nachinstallieren)
if ! command -v npm &>/dev/null; then
  echo '[ ] npm nicht gefunden, installiere manuell...'
  curl -L https://www.npmjs.com/install.sh | sh
fi

echo '[7/10] Solana CLI aus Source kompilieren (ARM64)...'
cd ~
if [ ! -d solana ]; then
  git clone https://github.com/solana-labs/solana.git
fi
cd solana
git fetch --tags
git checkout v1.18.14
cargo build --release -p solana-cli

echo '[8/10] Solana CLI installieren...'
mkdir -p ~/.local/share/solana/install/active_release/bin
cp target/release/solana ~/.local/share/solana/install/active_release/bin/

echo '[9/10] PATH für Solana setzen...'
grep -qxF 'export PATH=\"\$HOME/.local/share/solana/install/active_release/bin:\$PATH\"' ~/.bashrc \
  || echo 'export PATH=\"\$HOME/.local/share/solana/install/active_release/bin:\$PATH\"' >> ~/.bashrc
export PATH=\"\$HOME/.local/share/solana/install/active_release/bin:\$PATH\"

echo '[10/10] Python‑venv & solana-py installieren...'
mkdir -p ~/solana-xenexAi && cd ~/solana-xenexAi
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install solana==0.36.6

# Finale Status-Ausgabe
echo ''
echo '🎉 Setup abgeschlossen!'
echo '• Solana CLI Version:' \$(solana --version)
echo '• Node.js Version:' \$(node -v)
echo '• npm Version:' \$(npm -v)
echo '• Python Version:' \$(python --version)
echo ''
echo 'Arbeitsverzeichnis:' \"\$PWD\"
echo 'Virtualenv aktiv – bereit für deine Solana‑Projekte!'
exec bash
"
