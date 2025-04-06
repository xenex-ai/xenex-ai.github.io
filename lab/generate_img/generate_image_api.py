# python generate_image_api.py --api_key DEIN_API_KEY --prompt "Dein individueller Prompt hier" --output "meinbild.png"


import requests
import argparse

def generate_image(api_key, prompt, output_file):
    url = "https://api.deepai.org/api/text2img"
    headers = {
        "api-key": api_key
    }
    data = {
        "text": prompt
    }
    print("Sende Anfrage an die DeepAI API...")
    response = requests.post(url, data=data, headers=headers)
    
    if response.status_code != 200:
        print("Fehler bei der Bildgenerierung:", response.text)
        return
    
    result = response.json()
    if 'output_url' not in result:
        print("Ungültige Antwort erhalten:", result)
        return
    
    image_url = result['output_url']
    print("Bild-URL erhalten:", image_url)
    
    print("Lade Bild herunter...")
    img_response = requests.get(image_url)
    if img_response.status_code == 200:
        with open(output_file, 'wb') as f:
            f.write(img_response.content)
        print(f"Bild wurde erfolgreich unter '{output_file}' gespeichert.")
    else:
        print("Fehler beim Herunterladen des Bildes.")

def main():
    parser = argparse.ArgumentParser(description="Generiere ein KI-Bild über die DeepAI API")
    parser.add_argument("--api_key", type=str, required=True, help="Dein DeepAI API Schlüssel")
    parser.add_argument("--prompt", type=str, default="Ein süßes 3D-Bild mit 'Guten Morgen' und niedlichen Tieren in 4K Wallpaper-Qualität", help="Textprompt für die Bildgenerierung")
    parser.add_argument("--output", type=str, default="meinbild.png", help="Ausgabedateiname")
    
    args = parser.parse_args()
    generate_image(args.api_key, args.prompt, args.output)

if __name__ == "__main__":
    main()
