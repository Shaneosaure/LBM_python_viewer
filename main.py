# Basic imports
import os
import sys
import threading
import queue
import subprocess
from pathlib import Path

# Tkinter imports
import tkinter as tk
from tkinter import scrolledtext
from PIL import Image, ImageTk

def create_gif_from_latest_pngs(delay, label, secondary, parent_folder="./results", image_index=0):
    parent_folder = Path(parent_folder)
    subfolders = sorted((d for d in parent_folder.iterdir() if d.is_dir()), key=lambda x: x.stat().st_ctime, reverse=True)

    if not subfolders:
        print("No subfolders found in the parent directory.")
        return

    latest_folder = subfolders[0]
    input_folder = latest_folder / "png"

    # Load all PNG images from the folder
    png_files = sorted((filename for filename in input_folder.iterdir() if filename.suffix == ".png"), key=lambda x: int(''.join(filter(str.isdigit, x.name))))

    if not png_files:
        print(f"No PNG images found in the folder '{input_folder}'.")
        return

    if image_index >= len(png_files):
        image_index = 0

    image_path = png_files[image_index]
    img = Image.open(image_path)
    img = img.resize((1600, 356))  # Adjust the image size as needed
    photo = ImageTk.PhotoImage(img)

    # Update the displayed image
    label.config(image=photo)
    label.image = photo

    # Schedule the display of the next image
    secondary.after(delay, create_gif_from_latest_pngs, delay, label, secondary, parent_folder, image_index + 1)

def enqueue_output(out, queue, exit_event):
    for line in iter(out.readline, b''):
        if line != '':
            queue.put(line)
            if exit_event.is_set():  # Check if the exit event is set
                break  # Exit the loop if the event is set

    out.close() #close the function

def show_realtime_output(command):
    # Create a new window to display real-time output
    output_window = tk.Toplevel()
    output_window.title("Realtime Command Output")

    # Add a scrolling text widget to display real-time output
    output_text = scrolledtext.ScrolledText(output_window, wrap=tk.WORD, width=80, height=20)
    output_text.pack(expand=True, fill='both')

    # Display initial message
    output_text.insert(tk.END, "The simulation is running. Please wait for the output. This may take a few seconds...\n")

    # Use subprocess.PIPE to capture standard output in real-time
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, universal_newlines=True)
    
    # Store the process as an attribute of the secondary window
    output_window.process = process

    # Create a queue to store output lines
    output_queue = queue.Queue()

    # Create an event to signal the thread to exit
    exit_event = threading.Event()

    # Create a thread to put output lines into the queue
    output_thread = threading.Thread(target=enqueue_output, args=(process.stdout, output_queue, exit_event))
    output_thread.daemon = True  # The thread terminates when the main program ends
    output_thread.start()

    # Read the queue and display the output in real-time
    def update_output():
        try:
            while True:
                output_line = output_queue.get_nowait()
                output_text.insert(tk.END, output_line)
        except queue.Empty:
            pass

        if process.poll() is None:
            # If the process is not finished, schedule the next update
            output_text.after(50, update_output)
            output_text.yview(tk.END)  # Scroll down to see the latest output
        else:
            # Display the final output
            if process.returncode == 0:
                output_text.insert(tk.END, f"\n\nSimulation finished with success !")
            else: 
                output_text.insert(tk.END, f"\n\nSimulation finished with an error, exit code: {process.returncode}")
            output_text.yview(tk.END)  # Scroll down to see the latest output
            output_text.configure(state='disabled')  # Make the text area read-only

    # Schedule the first update of the output
    output_text.after(50, update_output)
   
    # Function to kill the process when the secondary window is closed
    def on_close(): 
        exit_event.set()
        output_window.process.kill()
        output_window.destroy()

    # Set on_close function as the closing handler for the secondary window
    output_window.protocol("WM_DELETE_WINDOW", on_close)

def execute_command(simulation_type_var):
    # Actual running python path
    python_executable = sys.executable

    # Build the command with the simulation type
    command = f"{python_executable} lbm/start.py {simulation_type_var}"

    # Display the output in real-time in a secondary window
    show_realtime_output(command)

def start_simulation(simulation_type_var):
    # Create a thread to run the command in the background
    thread = threading.Thread(target=execute_command, args=(simulation_type_var,))
    thread.start()

def show_result():
    # Delay between each image (in milliseconds)
    delay = 50  # Change this value to adjust the animation speed
    # Create a secondary window to display images
    secondary = tk.Toplevel()
    secondary.title("Simulation Result")

    # Label to display the images
    label = tk.Label(secondary)
    label.pack()
    create_gif_from_latest_pngs(delay, label, secondary)


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

    # Button to show the results of the simulation
    result_button = tk.Button(root, text="Show result", command=show_result)
    result_button.pack()

    root.mainloop()

# Call the main function if the script is run directly
if __name__ == "__main__":
    main()
