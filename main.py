# Basic imports
import sys
import threading
import io
from pathlib import Path
import multiprocessing

# Tkinter imports
import customtkinter as tk
from tkinter import scrolledtext
from PIL import Image

# Custom imports
from lbm.src.app.app      import *
from lbm.src.core.lattice import *
from lbm.src.core.run     import *

class Simulation_var:
    def __init__(self, type="array"):
        self.type = type
        self.width = None 

    def set_type(self, type):
        self.type = type

    def get_type(self):
        return self.type 

    def set_width(self, width):
        self.width = width

    def get_width(self):
        if self.width==None:
            return "Default value"
        return self.width


class QueueAsFile(io.TextIOBase):
    def __init__(self, queue):
        self.queue = queue

    def write(self, string):
        self.queue.put(string)

    def flush(self):
        pass  # Optional: if you need to flush

# global variables declaration
width_label = None
width_entry = None
start_button = None
gif_delay = 50 # gif_delay between each image (in milliseconds)
    
def export_to_gif_with_dialog(parent_folder):
    parent_folder = Path(parent_folder)
    input_folder = parent_folder / "png"

    # Load all PNG images from the folder
    png_files = sorted((filename for filename in input_folder.iterdir() if filename.suffix == ".png"),
                       key=lambda x: int(''.join(filter(str.isdigit, x.name))))

    if not png_files:
        print("No images found for GIF export.")
        return

    # Create a list to store the images
    images = []

    for image_path in png_files:
        try:
            img = Image.open(image_path)
            images.append(img)
        except Image.UnidentifiedImageError:
            print(f"Error opening image '{image_path}'. Skipping...")

    if not images:
        print("No valid images found for GIF export.")
        return

    # Ask the user to choose the destination folder for saving the GIF
    save_path = tk.filedialog.asksaveasfilename(defaultextension=".gif", filetypes=[("GIF files", "*.gif")])
    
    if not save_path:
        print("Operation canceled by the user.")
        return
    # Save the images as a GIF
    images[0].save(save_path, save_all=True, append_images=images[1:], loop=0, duration=gif_delay*3)  # Adjust the duration as needed

def loop_images(label, secondary, parent_folder, image_index=0):
    
    parent_folder=Path(parent_folder)
    input_folder = parent_folder / "png"

    # Load all PNG images from the folder
    png_files = sorted((filename for filename in input_folder.iterdir() if filename.suffix == ".png"), key=lambda x: int(''.join(filter(str.isdigit, x.name))))

    if not png_files:        
        # Display a message when no images are found
        label.configure(text="Images not created yet, wait a few more seconds...")

        # Schedule the next check after a gif_delay
        secondary.after(gif_delay, loop_images, label, secondary, parent_folder, image_index)
        return

    if image_index >= len(png_files):
        image_index = 0

    image_path = png_files[image_index]
    
    try:
        img = Image.open(image_path)
    except Image.UnidentifiedImageError:
        label.configure(image=None,text=f"Error opening image '{image_path}'. Skipping...")
        img = None

    if img:
        photo = tk.CTkImage(light_image=img,dark_image=img,size=(1600,356))

        # Update the displayed image
        label.configure(image=photo,text="")
        label.image = photo

    # Schedule the display of the next image
    secondary.after(gif_delay, loop_images, label, secondary, parent_folder, image_index + 1)

def enqueue_output(out_queue, display_queue, exit_event):
    for line in iter(out_queue.get, None):  # Use get method with timeout to handle termination
        line = line.replace("\r", "\n") 
        display_queue.put(line)
        if exit_event.is_set():
            break

def show_realtime_output(selected_simulation_type):
    
    if selected_simulation_type.get_type() == "custom vent":
        # Create a new window to display real-time output
        output_window = tk.CTkToplevel()
        output_window.title(f"Realtime Command Output - {selected_simulation_type.get_type()} - width {selected_simulation_type.get_width()}")

        # Add a label above the scrolling text widget
        label = tk.CTkLabel(output_window, text=f"Live Solving Output: {selected_simulation_type.get_type()}\nwidth = {selected_simulation_type.get_width()}", font=("Helvetica", 12, "bold"))
        label.pack(pady=10)  # Add some padding between the label and the text widget
    else: 
        # Create a new window to display real-time output
        output_window = tk.CTkToplevel()
        output_window.title(f"Realtime Command Output - {selected_simulation_type.get_type()}")
        
        # Add a label above the scrolling text widget
        label = tk.CTkLabel(output_window, text=f"Live Solving Output: {selected_simulation_type.get_type()}", font=("Helvetica", 12, "bold"))
        label.pack(pady=10)  # Add some padding between the label and the text widget

    # Add a scrolling text widget to display real-time output
    output_text = scrolledtext.ScrolledText(output_window, wrap=tk.WORD, width=80, height=20)
    output_text.pack(expand=True, fill='both')


    # Display initial message
    output_text.insert(tk.END, "The simulation is running. Please wait for the output. This may take a few seconds...\n")

    # Create a queue to store the reference to ltc
    ltc_queue = multiprocessing.Queue()

    # Créez deux queues pour la sortie standard et la sortie d'erreur
    stdout_queue = multiprocessing.Queue()
    stderr_queue = multiprocessing.Queue()
    
    # Use subprocess.PIPE to capture standard output in real-time
    process = multiprocessing.Process(target=run_with_queues, args=(selected_simulation_type, stdout_queue, stderr_queue,ltc_queue),daemon=True)

    # Store the process as an attribute of the secondary window
    output_window.process = process

    # Create a queue to store output lines
    output_queue = multiprocessing.Queue()

    # Create an event to signal the thread to exit
    exit_event = multiprocessing.Event()

    # Create a thread to put output lines into the queue
    output_thread = threading.Thread(target=enqueue_output, args=(stdout_queue, output_queue, exit_event))
    output_thread.daemon = True
    output_thread.start()

    process.start()
    
    # Retrieve the reference to ltc from the queue
    ltc = ltc_queue.get()

    # Read the queue and display the output in real-time
    def update_output():
        while not output_queue.empty():
            output_line = output_queue.get()
            output_text.insert(tk.END, output_line)

        if process.is_alive():
            # If the process is not finished, schedule the next update
            output_text.after(50, update_output)
            output_text.yview(tk.END)  # Scroll down to see the latest output
        else:
            # Display the final output
            if process.exitcode == 0:
                output_text.insert(tk.END, f"\n\nSimulation finished with success !")
            else:
                output_text.insert(tk.END, f"\n\nSimulation finished with an error, exit code: {process.exitcode}")
            output_text.yview(tk.END)  # Scroll down to see the latest output
            output_text.configure(state='disabled')  # Make the text area read-only

    # Créer un bouton "Show result" dans la fenêtre de sortie
    show_result_button = tk.CTkButton(output_window, text="Show Result (slows down solving)", command=lambda: show_result(ltc.output_dir,selected_simulation_type))
    # Créer un bouton "Show result" dans la fenêtre de sortie après une attente de 5 secondes
    output_window.after(3000, lambda: show_result_button.pack())

    # Schedule the first update of the output
    output_text.after(50, update_output)
   
    # Function to kill the process when the secondary window is closed
    def on_close(): 
        exit_event.set()
        output_window.process.terminate()
        output_window.destroy()

    # Set on_close function as the closing handler for the secondary window
    output_window.protocol("WM_DELETE_WINDOW", on_close)

def run_with_queues(selected_simulation_type, stdout_queue, stderr_queue, ltc_queue):
    # Redirigez sys.stdout et sys.stderr vers les queues
    sys.stdout = QueueAsFile(stdout_queue)
    sys.stderr = QueueAsFile(stderr_queue)
    
    try:
        if selected_simulation_type.get_type()=="custom vent":
            # Get variables
            width = selected_simulation_type.get_width()

            # Instantiate app depending on conditions
            if width != "Default value":
                app = vent(float(width))
            else:
                app = vent()

            # Instanciate lattice
            ltc = lattice(app)

            # Mettez la référence de ltc dans la file de sortie
            ltc_queue.put(ltc)

            # Run
            run(ltc, app)
        else:
            # Instanciate app
            app = app_factory.create(selected_simulation_type.get_type())

            # Instanciate lattice
            ltc = lattice(app)

            # Mettez la référence de ltc dans la file de sortie
            ltc_queue.put(ltc)

            # Appelez votre fonction run normalement
            run(ltc, app)
    finally:
        # Restaurez sys.stdout et sys.stderr pour éviter des problèmes potentiels
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__
        
def start_simulation(selected_simulation_type):
    # Create a thread to run the command in the background
    thread = threading.Thread(target=show_realtime_output, args=(selected_simulation_type,))
    thread.start()

def show_result(path,selected_simulation_type):
    # Create a secondary window to display images
    secondary = tk.CTkToplevel()
    secondary.title(f"Simulation Result - {selected_simulation_type.get_type()}")

    # Label to display the images
    label = tk.CTkLabel(secondary)
    label.pack()
    loop_images(label, secondary,path)
   # Button to start the simulation
    test = tk.CTkButton(secondary, text="Export to GIF", command=lambda: export_to_gif_with_dialog(path))
    test.pack(pady=10)  # Ajouter un espace de 10 pixels en dessous du bouton        
    
def on_width_change(event,selected_simulation_type):
    if event.widget.get == '':
        selected_simulation_type.set_width(float(0))
    else:
        selected_simulation_type.set_width(float(event.widget.get()))

# Main function
def main():
    # Main window
    root = tk.CTk()
    root.title("Simulation generator of CFD using LBM method")

    # Measure the title size
    title_width = root.winfo_reqwidth() * 3
    title_height = root.winfo_reqheight() * 1

    # Set the size of the main window based on the title size
    root.geometry(f"{title_width}x{title_height}")

    # Options for the dropdown menu
    simulation_types = ["array","vent", "custom vent","cavity", "poiseuille", "step","turek"]

    # Étiquette et menu déroulant pour le type de simulation
    simulation_type_label = tk.CTkLabel(root, text="Simulation type:")
    simulation_type_label.pack()
      
    def on_simulation_type_change(choice):
        global width_label, width_entry, speed_entry, speed_label, start_button
   
        # Initialisation of Simulation_var
        selected_simulation_type=Simulation_var()
        selected_simulation_type.set_type(choice)
       # Détruire l'ancien width_label s'il existe
        if width_label or width_entry:
            width_label.destroy()
            width_entry.destroy()
            start_button.destroy()
        elif start_button:
            start_button.destroy()

        if choice =="custom vent":
            # Width of vent parameter
            width_label = tk.CTkLabel(root, text="Vent width (between 0 and 4):")
            width_label.pack()
            width_entry = tk.CTkEntry(master=root,placeholder_text="0.8")
            width_entry.bind("<KeyRelease>", lambda event: on_width_change(event, selected_simulation_type))
            width_entry.pack()

            # Button to start the simulation
            start_button = tk.CTkButton(root, text="Start simulation", command=lambda: start_simulation(selected_simulation_type))
            start_button.pack(pady=10)  # Ajouter un espace de 10 pixels en dessous du bouton        
        else:
            # Button to start the simulation
            start_button = tk.CTkButton(root, text="Start simulation", command=lambda: start_simulation(selected_simulation_type))
            start_button.pack(pady=10)  # Ajouter un espace de 10 pixels en dessous du bouton        
            
    simulation_type_menu = tk.CTkOptionMenu(root,values=simulation_types,command=on_simulation_type_change)
    simulation_type_menu.pack()
    
    
    root.mainloop()

# Call the main function if the script is run directly
if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
