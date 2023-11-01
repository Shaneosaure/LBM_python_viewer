import tkinter as tk
from PIL import Image, ImageTk
import os

def display_images_as_gif(input_folder, delay, image_index=0):
    # Charger toutes les images PNG du dossier
    png_files = [filename for filename in os.listdir(input_folder) if filename.endswith(".png")]
    png_files.sort(key=lambda x: int(''.join(filter(str.isdigit, x))))

    if not png_files:
        print(f"Aucune image PNG trouvée dans le dossier '{input_folder}'.")
        return

    if image_index >= len(png_files):
        image_index = 0

    image_path = os.path.join(input_folder, png_files[image_index])
    img = Image.open(image_path)
    img = img.resize((1600, 356))  # Ajustez la taille de l'image selon vos besoins
    photo = ImageTk.PhotoImage(img)

    # Mettre à jour l'image affichée
    label.config(image=photo)
    label.image = photo

    # Planifier l'affichage de la prochaine image
    root.after(delay, display_images_as_gif, input_folder, delay, image_index + 1)

# main window
root = tk.Tk()
root.title("Simulation GIF Viewer")

# Label pour afficher les images
label = tk.Label(root)
label.pack()

# Dossier contenant les images PNG
input_folder = "./lbm/results/2023-11-01_17_53_41/png"

# Délai entre chaque image (en millisecondes)
delay = 100  # Changez cette valeur pour ajuster la vitesse de l'animation

# Démarrer l'affichage des images
display_images_as_gif(input_folder, delay)

root.mainloop()
