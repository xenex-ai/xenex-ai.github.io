use colored::*;
use ed25519_dalek::Keypair;
use rand::rngs::OsRng;
use bs58;
use serde::{Serialize, Deserialize};
use std::fs;
use std::io::{self, Write};
use std::path::Path;
use indicatif::{ProgressBar, ProgressStyle};

#[derive(Serialize, Deserialize, Clone)]
struct Entry {
    address: String,
    private_key_hex: String,
    phantom_private_key: Vec<u8>,
    phantom_private_key_base58: String,
}

fn ascii_intro() {
    let intro = format!(
        r#"
{green}{bold} _______  _______  _______  _______  _______ 
(  ____ \(  ___  )(  ____ \(  ____ \(  ___  )
| (    \/| (   ) || (    \/| (    \/| (   ) |
| (_____ | |   | || (_____ | |      | (___) |
(_____  )| |   | |(_____  )| |      |  ___  |
      ) || |   | |      ) || |      | (   ) |
/\____) || (___) |/\____) || (____/\| )   ( |
\_______)(_______)\_______)(_______/|/     \|                                                            
 sosca v0.7.1
{reset}
    "#,
        green = Green.bold().to_string(),
        bold = Style::bold().to_string(),
        reset = Style::reset().to_string()
    );
    println!("{}", intro);
}

fn generate_address() -> (String, String, Vec<u8>, String) {
    // Schlüsselgenerierung mit ed25519-dalek
    let mut csprng = OsRng {};
    let keypair: Keypair = Keypair::generate(&mut csprng);
    let public_key_bytes = keypair.public.to_bytes();
    let private_key_bytes = keypair.secret.to_bytes();

    // Adresse: Base58-codierter öffentlicher Schlüssel
    let address = bs58::encode(public_key_bytes).into_string();

    // Privater Schlüssel als Hex-String
    let private_key_hex = hex::encode(private_key_bytes);

    // Phantom-kompatibler Private Key (Konkatenation von privatem und öffentlichem Schlüssel)
    let mut phantom_private_key: Vec<u8> = Vec::with_capacity(64);
    phantom_private_key.extend_from_slice(&private_key_bytes);
    phantom_private_key.extend_from_slice(&public_key_bytes);

    // Base58-codierte Version des Phantom Private Keys
    let phantom_private_key_base58 = bs58::encode(&phantom_private_key).into_string();

    (address, private_key_hex, phantom_private_key, phantom_private_key_base58)
}

fn save_address(entry: &Entry, filename: &str) -> io::Result<()> {
    let mut entries: Vec<Entry> = if Path::new(filename).exists() {
        let content = fs::read_to_string(filename)?;
        serde_json::from_str(&content).unwrap_or_else(|_| Vec::new())
    } else {
        Vec::new()
    };
    entries.push(entry.clone());
    let json_string = serde_json::to_string_pretty(&entries)?;
    fs::write(filename, json_string)?;
    Ok(())
}

fn main() {
    // ASCII-Art Intro anzeigen
    ascii_intro();

    // Eingabe des Zielworts (Suffix) von der Konsole
    print!("{}", "Bitte geben Sie das Zielwort (Suffix) ein, mit dem die Adresse enden soll (oder leer für alle): ".cyan());
    io::stdout().flush().unwrap();
    let mut target = String::new();
    io::stdin()
        .read_line(&mut target)
        .expect("Fehler beim Lesen der Eingabe");
    let target = target.trim().to_string();

    println!("{}", "Starte die Generierung und Überprüfung der Adressen...".yellow());

    // Fortschrittsanzeige konfigurieren
    let pb = ProgressBar::new_spinner();
    pb.set_style(ProgressStyle::with_template("{spinner} Generiere Keys: {pos}").unwrap());

    loop {
        pb.inc(1);
        let (address, private_key_hex, phantom_private_key, phantom_private_key_base58) =
            generate_address();

        // Falls ein Suffix angegeben wurde, prüfen wir, ob die Adresse damit endet.
        if !target.is_empty() && !address.ends_with(&target) {
            continue;
        }

        pb.finish_and_clear();
        println!("{}", "Erfolg! Passende Adresse gefunden!".green().bold());
        println!("{} {}", "Adresse:".magenta(), address.bold());
        println!("{} {}", "Privater Schlüssel (Hex):".magenta(), private_key_hex.bold());
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

        let entry = Entry {
            address,
            private_key_hex,
            phantom_private_key,
            phantom_private_key_base58,
        };

        if let Err(e) = save_address(&entry, "addresses.json") {
            eprintln!("Fehler beim Speichern: {}", e);
        }
        break;
    }
}
