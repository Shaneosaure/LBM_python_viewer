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

def enqueue_output(out, queue):
    for line in iter(out.readline, b''):
        queue.put(line)
    out.close()

def show_realtime_output(command):
    # Create a new window to display real-time output
    output_window = tk.Toplevel()
    output_window.title("Realtime Command Output")

    # Add a scrolling text widget to display real-time output
    output_text = scrolledtext.ScrolledText(output_window, wrap=tk.WORD, width=80, height=20)
    output_text.pack(expand=True, fill='both')

    # Display a preliminary message
    output_text.insert(tk.END, "The simulation is running. Please wait for the output. This may take a few seconds...\n\n")

    # Use subprocess.PIPE to capture standard output in real-time
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, universal_newlines=True)

    # Store the process as an attribute of the secondary window
    output_window.process = process

    # Create a queue to store output lines
    output_queue = queue.Queue()

    # Create a thread to put output lines into the queue
    output_thread = threading.Thread(target=enqueue_output, args=(process.stdout, output_queue))
    output_thread.daemon = True  # The thread terminates when the main program ends
    output_thread.start()

    # Read the queue and display the output in real-time
    def update_output():
        while True:
            try:
                output_line = output_queue.get_nowait()
                output_text.insert(tk.END, output_line)
                output_text.yview(tk.END)  # Scroll down to see the latest output
            except queue.Empty:
                break

        if process.poll() is None:
            # If the process is not finished, schedule the next update
            output_text.after(300, update_output)
        else:
            # Display the exit code in the text widget
            output_text.insert(tk.END, f"\n\nProcess finished with exit code {process.returncode}")
            output_text.configure(state='disabled')  # Make the text area read-only

    # Schedule the first update of the output
    output_text.after(300, update_output)

    # Function to kill the process when the secondary window is closed
    def on_close():
        kill_subprocess(output_window.process)
        output_window.destroy()

    # Set on_close function as the closing handler for the secondary window
    output_window.protocol("WM_DELETE_WINDOW", on_close)

def execute_command(simulation_type_var):
    # Build the command with the simulation type
    command = f"python lbm/start.py {simulation_type_var}"

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

def kill_subprocess(process):
    try:
        process.terminate()
        process.wait(timeout=0.1)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()

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
    simulation_types = ["array", "cavity", "poiseuille", "step"]
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
