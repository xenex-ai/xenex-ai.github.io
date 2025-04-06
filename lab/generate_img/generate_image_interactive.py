import requests
import argparse
import sys
from PIL import Image
from io import BytesIO

def download_with_progress(url, output_file, chunk_size=8192):
    response = requests.get(url, stream=True)
    if response.status_code != 200:
        print("Fehler beim Herunterladen des Bildes.")
        return False

    total_length = response.headers.get('content-length')
    if total_length is None:
        # Kein Fortschrittsbalken möglich
        with open(output_file, 'wb') as f:
            f.write(response.content)
    else:
        total_length = int(total_length)
        downloaded = 0
        with open(output_file, 'wb') as f:
            for data in response.iter_content(chunk_size=chunk_size):
                downloaded += len(data)
                f.write(data)
                done = int(50 * downloaded / total_length)
                percent = int(100 * downloaded / total_length)
                sys.stdout.write("\r[%s%s] %d%%" % ('█' * done, '.' * (50-done), percent))
                sys.stdout.flush()
        print()  # Neue Zeile nach Fortschritt
    return True

def generate_image(api_key, prompt, notes, output_file):
    url = "https://api.deepai.org/api/text2img"
    headers = {
        "api-key": api_key
    }
    # Falls Notizen vorhanden sind, diese an den Prompt anhängen
    if notes:
        prompt = f"{prompt}\nNotizen: {notes}"
        
    data = {
        "text": prompt
    }
    print("Sende Anfrage an die DeepAI API...")
    response = requests.post(url, data=data, headers=headers)
    
    if response.status_code != 200:
        print("Fehler bei der Bildgenerierung:", response.text)
        return None
    
    result = response.json()
    if 'output_url' not in result:
        print("Ungültige Antwort erhalten:", result)
        return None
    
    image_url = result['output_url']
    print("Bild-URL erhalten:", image_url)
    
    print("Lade Bild herunter...")
    if download_with_progress(image_url, output_file):
        print(f"\nBild wurde erfolgreich unter '{output_file}' gespeichert.")
        return output_file
    else:
        return None

def open_image(image_path):
    try:
        img = Image.open(image_path)
        img.show()
    except Exception as e:
        print("Fehler beim Öffnen des Bildes:", e)

def main():
    parser = argparse.ArgumentParser(description="Generiere ein KI-Bild über die DeepAI API mit interaktiver Eingabe")
    parser.add_argument("--api_key", type=str, required=True, help="Dein DeepAI API Schlüssel")
    parser.add_argument("--output", type=str, default="meinbild.png", help="Ausgabedateiname für das generierte Bild")
    args = parser.parse_args()
    
    print("Willkommen zur KI Bildgenerierung!")
    
    # Interaktive Eingabe
    prompt = input("Bitte gib den gewünschten Bild-Prompt ein:\n> ")
    notes = input("Möchtest du zusätzliche Notizen/Anweisungen hinzufügen? (Falls nein, Enter drücken):\n> ")
    
    output_file = args.output
    
    result_file = generate_image(args.api_key, prompt, notes, output_file)
    if result_file:
        open_choice = input("Möchtest du das Bild jetzt anzeigen? (j/n): ")
        if open_choice.lower() == 'j':
            open_image(result_file)
    else:
        print("Bild konnte nicht generiert werden.")

if __name__ == "__main__":
    main()
