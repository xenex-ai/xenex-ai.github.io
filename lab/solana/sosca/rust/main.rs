use base58::ToBase58;
use colored::*;
use ed25519_dalek::{SigningKey, VerifyingKey};
use indicatif::{ProgressBar, ProgressStyle};
use rand::rngs::OsRng;
use rand::RngCore;  // importiere RngCore, um fill_bytes() zu nutzen
use serde::{Deserialize, Serialize};
use std::fs;
use std::io::{self, Write};
use std::thread::sleep;
use std::time::Duration;

#[derive(Serialize, Deserialize, Debug, Clone)]
struct AddressEntry {
    address: String,
    private_key_hex: String,
    phantom_private_key: Vec<u8>,
    phantom_private_key_base58: String,
}

fn ascii_intro() {
    let intro = format!(
        "{}\n\
         _______  _______  _______  _______  _______ \n\
         (  ____ \\(  ___  )(  ____ \\(  ____ \\(  ___  )\n\
         | (    \\/| (   ) || (    \\/| (    \\/| (   ) |\n\
         | (_____ | |   | || (_____ | |      | (___) |\n\
         (_____  )| |   | |(_____  )| |      |  ___  |\n\
               ) || |   | |      ) || |      | (   ) |\n\
         /\\____) || (___) |/\\____) || (____/\\| )   ( |\n\
         \\_______)(_______)\\_______)(_______/|/     \\|\n\
         \n\
         sosca v0.7.1\n{}",
        " ".green().bold(),
        "".clear()
    );
    println!("{}", intro);
}

fn generate_address() -> (String, String, Vec<u8>, String) {
    // Erzeuge ein neues Schlüsselpaar:
    // 1. Erzeuge mit OsRng einen zufälligen 32-Byte-Seed.
    let mut csprng = OsRng {};
    let mut seed = [0u8; 32];
    csprng.fill_bytes(&mut seed);

    // 2. Erzeuge den SigningKey aus diesem Seed.
    let signing_key = SigningKey::from_bytes(&seed);

    // 3. Leite den VerifyingKey (PublicKey) vom SigningKey ab.
    let verifying_key: VerifyingKey = signing_key.verifying_key();

    // SigningKey::to_bytes() gibt ein 64-Byte-Array zurück (intern repräsentiert es den Secret Key und weitere Daten).
    // Wir betrachten hier nur die ersten 32 Byte als privaten Schlüssel (Seed).
    let full_signing_bytes = signing_key.to_bytes();
    let secret_key_bytes = &full_signing_bytes[..32]; // 32 Byte privater Schlüssel
    let public_key_bytes = verifying_key.to_bytes();    // 32 Byte Public Key

    // Base58-kodierte Adresse entspricht hier dem Public-Key.
    let address = public_key_bytes.to_base58();

    // Privater Schlüssel als Hex-String (32 Byte)
    let private_key_hex = hex::encode(secret_key_bytes);

    // Phantom-kompatibler Private Key: 64 Byte – Konkatenation des privaten Seeds und des Public Keys.
    let mut phantom_private_key = Vec::with_capacity(64);
    phantom_private_key.extend_from_slice(secret_key_bytes);
    phantom_private_key.extend_from_slice(&public_key_bytes);

    // Base58-Kodierung des 64-Byte Private Keys
    let phantom_private_key_base58 = phantom_private_key.to_base58();

    (address, private_key_hex, phantom_private_key, phantom_private_key_base58)
}

fn save_address(entry: &AddressEntry, filename: &str) -> io::Result<()> {
    let mut data: Vec<AddressEntry> = if let Ok(contents) = fs::read_to_string(filename) {
        match serde_json::from_str(&contents) {
            Ok(existing) => existing,
            Err(_) => Vec::new(),
        }
    } else {
        Vec::new()
    };

    data.push(entry.clone());
    let json_data = serde_json::to_string_pretty(&data)?;
    fs::write(filename, json_data)
}

fn main() {
    ascii_intro();

    // Lies das Zielwort (Suffix) ein.
    print!(
        "{}",
        "Bitte geben Sie das Zielwort (Suffix) ein, mit dem die Adresse enden soll (oder leer für alle): ".cyan()
    );
    io::stdout().flush().unwrap();

    let mut target = String::new();
    io::stdin()
        .read_line(&mut target)
        .expect("Fehler beim Einlesen der Eingabe");
    let target = target.trim();

    println!("{}", "Starte die Generierung und Überprüfung der Adressen...".yellow());

    // Progressbar initialisieren
    let pb = ProgressBar::new_spinner();
    pb.set_style(
        ProgressStyle::default_spinner()
            .tick_chars("⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏ ")
            .template("{spinner} {msg}"),
    );
    pb.enable_steady_tick(80);
    pb.set_message("Generiere Keys...");

    loop {
        let (address, private_key_hex, phantom_private_key, phantom_private_key_base58) =
            generate_address();

        // Falls ein Suffix angegeben ist, wird überprüft, ob die Adresse damit endet.
        if !target.is_empty() && !address.ends_with(target) {
            continue;
        }

        pb.finish_and_clear();
        println!(
            "{}",
            "Erfolg! Passende Adresse gefunden!".green().bold()
        );
        println!("{} {}", "Adresse:".magenta(), address.bold());
        println!(
            "{} {}",
            "Privater Schlüssel (Hex):".magenta(),
            private_key_hex.bold()
        );
        println!(
            "{} {:?}",
            "Phantom-kompatibler Private Key (64-Byte Liste):".magenta(),
            phantom_private_key
        );
        println!(
            "{} {}",
            "Phantom-kompatibler Private Key (Base58):".magenta(),
            phantom_private_key_base58.bold()
        );

        let entry = AddressEntry {
            address,
            private_key_hex,
            phantom_private_key,
            phantom_private_key_base58,
        };

        if let Err(e) = save_address(&entry, "addresses.json") {
            eprintln!("Fehler beim Speichern der Adresse: {}", e);
        }

        break;
    }

    sleep(Duration::from_millis(200));
}
