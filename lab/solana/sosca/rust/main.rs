use base58::ToBase58;
use colored::*;
use ed25519_dalek::{SigningKey, VerifyingKey};
use indicatif::{ProgressBar, ProgressStyle};
use rand::rngs::OsRng;
use rand::RngCore;
use serde::{Deserialize, Serialize};
use std::fs;
use std::io::{self, Write};
use std::thread::sleep;
use std::time::{Duration, Instant};

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
         sosca rust v0.7.2\n{}",
        " ".green().bold(),
        "".clear()
    );
    println!("{}", intro);
}

fn generate_address() -> (String, String, Vec<u8>, String) {
    // Erzeuge einen 32-Byte zufälligen Seed
    let mut csprng = OsRng {};
    let mut seed = [0u8; 32];
    csprng.fill_bytes(&mut seed);

    // Erzeuge das Schlüsselpaar
    let signing_key = SigningKey::from_bytes(&seed);
    let verifying_key: VerifyingKey = signing_key.verifying_key();

    // Extrahiere die benötigten Byte-Segmente:
    let full_signing_bytes = signing_key.to_bytes();
    let secret_key_bytes = &full_signing_bytes[..32];
    let public_key_bytes = verifying_key.to_bytes();

    // Erzeuge die Adresse: Base58-Kodierung des öffentlichen Schlüssels
    let address = public_key_bytes.to_base58();

    // Privater Schlüssel als Hex-String
    let private_key_hex = hex::encode(secret_key_bytes);

    // Erzeuge den Phantom-kompatiblen Private Key: 64-Byte (privater Seed + Public Key)
    let mut phantom_private_key = Vec::with_capacity(64);
    phantom_private_key.extend_from_slice(secret_key_bytes);
    phantom_private_key.extend_from_slice(&public_key_bytes);

    // Base58-Kodierung des Phantom Private Keys
    let phantom_private_key_base58 = phantom_private_key.to_base58();

    (address, private_key_hex, phantom_private_key, phantom_private_key_base58)
}

fn save_address(entry: &AddressEntry, filename: &str) -> io::Result<()> {
    let mut data: Vec<AddressEntry> = if let Ok(contents) = fs::read_to_string(filename) {
        serde_json::from_str(&contents).unwrap_or_else(|_| Vec::new())
    } else {
        Vec::new()
    };
    data.push(entry.clone());
    let json_data = serde_json::to_string_pretty(&data)?;
    fs::write(filename, json_data)
}

fn main() {
    ascii_intro();

    // Lese das Zielwort (Suffix) ein.
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

    // Initialisiere die Progressbar
    let pb = ProgressBar::new_spinner();
    pb.set_style(
        ProgressStyle::default_spinner()
            .tick_chars("⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏ ")
            .template("{spinner} {msg}"),
    );
    pb.enable_steady_tick(80);

    let start_time = Instant::now();
    let mut attempts: u64 = 0;

    loop {
        attempts += 1;
        let (address, private_key_hex, phantom_private_key, phantom_private_key_base58) =
            generate_address();

        // Aktualisiere die Anzeige der Fortschrittsinformationen
        let elapsed = start_time.elapsed().as_secs_f64();
        let keys_per_sec = attempts as f64 / elapsed;
        let msg = format!("Versuche: {} Keys | {:.2} Keys/Sekunde", attempts, keys_per_sec);
        pb.set_message(msg);


        // Überprüfe, ob das Suffix passt (falls definiert)
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
        println!("{} {}", "Anzahl Versuche:".blue(), attempts);
        println!(
            "{} {:.2} Sekunden",
            "Gesamtdauer:".blue(),
            elapsed
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

    // Kleiner Puffer, damit der Nutzer die Ausgabe erfassen kann.
    sleep(Duration::from_millis(200));
}
