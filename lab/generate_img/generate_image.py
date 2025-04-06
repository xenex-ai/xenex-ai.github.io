import torch
from diffusers import StableDiffusionPipeline
from PIL import Image
import argparse

def main():
    # Argumente für den Prompt, den Dateinamen etc.
    parser = argparse.ArgumentParser(description="Generiere Bilder mit Stable Diffusion")
    parser.add_argument(
        "--prompt", 
        type=str, 
        default="Ein süßes 3D-Bild mit 'Guten Morgen' und niedlichen Tieren in 4K Wallpaper-Qualität", 
        help="Textprompt für die Bildgenerierung"
    )
    parser.add_argument(
        "--output", 
        type=str, 
        default="output.png", 
        help="Dateiname für das generierte Bild"
    )
    parser.add_argument(
        "--num_inference_steps", 
        type=int, 
        default=50, 
        help="Anzahl der Inferenz-Schritte (mehr Schritte = detaillierteres Bild)"
    )
    parser.add_argument(
        "--guidance_scale", 
        type=float, 
        default=7.5, 
        help="Guidance Scale zur Steuerung der Bildgenauigkeit (höhere Werte führen zu engerer Prompt-Übereinstimmung)"
    )
    args = parser.parse_args()

    # Bestimmen, ob CUDA verfügbar ist, andernfalls CPU verwenden
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Verwende Gerät: {device}")

    # Lade das Stable Diffusion Modell (hier Version v1-4, kann angepasst werden)
    model_id = "CompVis/stable-diffusion-v1-4"
    pipe = StableDiffusionPipeline.from_pretrained(
        model_id,
        revision="fp16" if device == "cuda" else None,
        torch_dtype=torch.float16 if device == "cuda" else torch.float32
    )
    pipe = pipe.to(device)

    # Generiere das Bild mit den angegebenen Parametern
    print("Bildgenerierung startet...")
    image = pipe(
        args.prompt, 
        num_inference_steps=args.num_inference_steps, 
        guidance_scale=args.guidance_scale
    ).images[0]

    # Speichere das generierte Bild
    image.save(args.output)
    print(f"Bild wurde erfolgreich unter '{args.output}' gespeichert.")

if __name__ == "__main__":
    main()
