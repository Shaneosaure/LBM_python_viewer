import tkinter as tk
from PIL import Image, ImageTk
import os

def create_gif_from_latest_pngs(delay,label,secondary,image_index=0):
    parent_folder = "./lbm/results"
    subfolders = [os.path.join(parent_folder, d) for d in os.listdir(parent_folder) if os.path.isdir(os.path.join(parent_folder, d))]
    subfolders.sort(key=lambda x: os.path.getctime(x), reverse=True)

    if not subfolders:
        print("Aucun sous-dossier trouvé dans le répertoire parent.")
        return

    latest_folder = subfolders[0]
    input_folder = os.path.join(latest_folder, "png")

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
    secondary.after(delay,create_gif_from_latest_pngs, delay,label,secondary, image_index + 1)

def start_simulation():
    tunnel_width = float(width_entry.get())
    object_params = object_entry.get()
    # Exemple d'utilisation
    # Délai entre chaque image (en millisecondes)
    delay = 50  # Changez cette valeur pour ajuster la vitesse de l'animation
    # Créer une fenêtre secondaire pour afficher les images
    secondary = tk.Toplevel()
    secondary.title("Simulation Result")

    # Label pour afficher les images
    label = tk.Label(secondary)
    label.pack()
    create_gif_from_latest_pngs(delay,label,secondary)

# Reste du code inchangé

# main window
root = tk.Tk()
root.title("Simulation generator of CFD using LBM method")

# Entry for tunnel width
width_label = tk.Label(root, text="Tunnel width:")
width_label.pack()
width_entry = tk.Entry(root)
width_entry.pack()

# Entry for object radius (we use a circle for the moment)
object_label = tk.Label(root, text="Object radius:")
object_label.pack()
object_entry = tk.Entry(root)
object_entry.pack()

# Bouton de démarrage de la simulation
start_button = tk.Button(root, text="Start simulation", command=start_simulation)
start_button.pack()


root.mainloop()