# Basic imports
import sys
import threading
import io
from pathlib import Path
import multiprocessing

# Tkinter imports
import tkinter as tk
from tkinter import scrolledtext
from PIL import Image, ImageTk

# Custom imports
from lbm.src.app.app      import *
from lbm.src.core.lattice import *
from lbm.src.core.run     import *

class QueueAsFile(io.TextIOBase):
    def __init__(self, queue):
        self.queue = queue

    def write(self, string):
        self.queue.put(string)

    def flush(self):
        pass  # Optional: if you need to flush

def create_gif_from_latest_pngs(delay, label, secondary, parent_folder, image_index=0):
    
    parent_folder=Path(parent_folder)
    input_folder = parent_folder / "png"

    # Load all PNG images from the folder
    png_files = sorted((filename for filename in input_folder.iterdir() if filename.suffix == ".png"), key=lambda x: int(''.join(filter(str.isdigit, x.name))))

    if not png_files:
        print(f"No PNG images found in the folder '{input_folder}'.")
        return

    if image_index >= len(png_files):
        image_index = 0

    image_path = png_files[image_index]
    
    try:
        img = Image.open(image_path)
    except Image.UnidentifiedImageError:
        print(f"Error opening image '{image_path}'. Skipping...")
        img = None

    if img:
        img = img.resize((1600, 356))  # Adjust the image size as needed
        photo = ImageTk.PhotoImage(img)

        # Update the displayed image
        label.config(image=photo)
        label.image = photo

    # Schedule the display of the next image
    secondary.after(delay, create_gif_from_latest_pngs, delay, label, secondary, parent_folder, image_index + 1)
    
def enqueue_output(out_queue, display_queue, exit_event):
    for line in iter(out_queue.get, None):  # Use get method with timeout to handle termination
        line = line.replace("\r", "\n") 
        display_queue.put(line)
        if exit_event.is_set():
            break

def show_realtime_output(simulation_type_var):
    # Create a new window to display real-time output
    output_window = tk.Toplevel()
    output_window.title(f"Realtime Command Output - {simulation_type_var}")
    
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
    process = multiprocessing.Process(target=run_with_queues, args=(simulation_type_var, stdout_queue, stderr_queue,ltc_queue),daemon=True)

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

    # Créer un bouton "Show result" dans la fenêtre de sortie
    show_result_button = tk.Button(output_window, text="Show Result (slows down solving)", command=lambda: show_result(ltc.output_dir))
    show_result_button.pack()

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

    # Schedule the first update of the output
    output_text.after(50, update_output)
   
    # Function to kill the process when the secondary window is closed
    def on_close(): 
        exit_event.set()
        output_window.process.terminate()
        output_window.destroy()

    # Set on_close function as the closing handler for the secondary window
    output_window.protocol("WM_DELETE_WINDOW", on_close)

def run_with_queues(simulation_type_var, stdout_queue, stderr_queue, ltc_queue):
    # Redirigez sys.stdout et sys.stderr vers les queues
    sys.stdout = QueueAsFile(stdout_queue)
    sys.stderr = QueueAsFile(stderr_queue)

    try:
         # Instanciate app
        app = app_factory.create(simulation_type_var)

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
        
def start_simulation(simulation_type_var):
    # Create a thread to run the command in the background
    thread = threading.Thread(target=show_realtime_output, args=(simulation_type_var,))
    thread.start()

def show_result(path):
    # Delay between each image (in milliseconds)
    delay = 50  # Change this value to adjust the animation speed
    # Create a secondary window to display images
    secondary = tk.Toplevel()
    secondary.title("Simulation Result")

    # Label to display the images
    label = tk.Label(secondary)
    label.pack()
    create_gif_from_latest_pngs(delay, label, secondary,path)


# Main function
def main():
    # Main window
    root = tk.Tk()
    root.title("Simulation generator of CFD using LBM method")

    # Measure the title size
    title_width = root.winfo_reqwidth() * 3
    title_height = root.winfo_reqheight()

    # Set the size of the main window based on the title size
    root.geometry(f"{title_width}x{title_height}")

    # Options for the dropdown menu
    simulation_types = ["array","vent", "cavity", "poiseuille", "step","turek"]
    selected_simulation_type = tk.StringVar(value=simulation_types[0])

    # Label and dropdown menu for the simulation type
    simulation_type_label = tk.Label(root, text="Simulation type:")
    simulation_type_label.pack()

    simulation_type_menu = tk.OptionMenu(root, selected_simulation_type, *simulation_types)
    simulation_type_menu.pack()

    # Entry for the object radius
    object_label = tk.Label(root, text="Object radius:")
    object_label.pack()
    object_entry = tk.Entry(root)
    object_entry.pack()

    # Button to start the simulation
    start_button = tk.Button(root, text="Start simulation", command=lambda: start_simulation(selected_simulation_type.get()))
    start_button.pack()

    root.mainloop()

# Call the main function if the script is run directly
if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
