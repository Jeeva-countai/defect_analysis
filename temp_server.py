import os
import netifaces
import tkinter as tk
from tkinter import messagebox, filedialog
from tkcalendar import Calendar
from tkinter import ttk
from ssh import SSHManager
import threading
import time

# Function to get the server's Tailscale IP
def get_server_ip():
    try:
        addresses = netifaces.ifaddresses("tailscale0")
        server_ip = addresses[netifaces.AF_INET][0]['addr']
        return server_ip
    except KeyError:
        return None

# Function to handle the commands execution in a separate thread
def execute_commands_thread():
    try:
        client_ip = client_ip_entry.get()
        date = date_entry.get()
        savedir = save_dir_entry.get()
        selected_item = dropdown_menu.get()

        if not client_ip or not date or not savedir or not selected_item:
            messagebox.showwarning("Input Error", "Please fill in all the fields!")
            return

        server_ip = get_server_ip()
        if not server_ip:
            raise Exception("Could not retrieve Tailscale IP for 'tailscale0' interface")

        # Get the corresponding value for the selected key from the dictionary
        item_id = item_dict[selected_item]

        # Initialize SSHManager
        ssh = SSHManager('kniti', 'Charlemagne@1')

        # Define total steps for progress tracking
        total_steps = 6
        progress_step = 100 // total_steps  # Calculate step size for each stage

        # Prepare the commands
        command1 = f'scp main.py {client_ip}:/home/kniti/'
        command2 = f'scp db.py {client_ip}:/home/kniti/'
        command3 = f'python3 main.py {date} {item_id}'  # Using the value from the dictionary
        command4 = f'scp {client_ip}:/home/kniti/needln_data.zip {savedir}'
        command5 = 'pip3 install pandas'
        command6 = 'rm -rf main.py db.py needln_data.zip'

        # Execute the commands and update progress
        update_progress_bar(progress_step, "Copying Files...")
        os.system(command1)

        update_progress_bar(progress_step, "Searching defects...")
        os.system(command2)

        update_progress_bar(progress_step, "Installing pandas...")
        ssh.run_command(client_ip, command5)

        update_progress_bar(progress_step, "Running main.py script...")
        ssh.run_command(client_ip, command3)

        update_progress_bar(progress_step, "Transferring needln_data.zip...")
        os.system(command4)

        update_progress_bar(progress_step, "Cleaning up...")
        # ssh.run_command(client_ip, command6)

        messagebox.showinfo("Success", "Commands executed successfully!")
        
        # Stop loading animation and close the UI
        loading_var.set(False)
        root.quit()

    except Exception as e:
        loading_var.set(False)
        messagebox.showerror("Error", str(e))

# Function to run the command execution with progress bar
def execute_commands():
    loading_var.set(True)  # Start loading
    progress_bar['value'] = 0  # Reset progress bar
    threading.Thread(target=execute_commands_thread, daemon=True).start()  # Start command execution

# Function to update progress bar and display status
def update_progress_bar(step_value, status_text):
    current_value = progress_bar['value']
    progress_bar['value'] = current_value + step_value  # Increment progress bar
    status_label.config(text=status_text)
    root.update_idletasks()  # Ensure the UI updates immediately

# Function to open calendar and select date
def open_calendar():
    def select_date():
        selected_date = cal.selection_get()
        date_entry.delete(0, tk.END)
        date_entry.insert(0, selected_date.strftime('%Y-%m-%d'))
        cal_window.destroy()

    cal_window = tk.Toplevel(root)
    cal_window.title("Select Date")

    cal = Calendar(cal_window, selectmode="day", date_pattern="yyyy-mm-dd")
    cal.pack(pady=10)

    select_btn = tk.Button(cal_window, text="Select", command=select_date)
    select_btn.pack(pady=10)

# Function to open directory picker for save directory
def open_directory_picker():
    selected_dir = filedialog.askdirectory()
    if selected_dir:
        save_dir_entry.delete(0, tk.END)
        save_dir_entry.insert(0, selected_dir)

# Create the UI
root = tk.Tk()
root.title("SSH File Transfer and Execution")

# Dictionary for the dropdown options
item_dict = {'lycra': 1, 'needln': 4, 'shutoff': 3,'hole':2,'countmix': 8, 'stopline': 6, 'twoply': 6, 'oil': 5}

# Client IP field
client_ip_label = tk.Label(root, text="Client Tailscale IP:")
client_ip_label.grid(row=0, column=0, padx=10, pady=10)
client_ip_entry = tk.Entry(root)
client_ip_entry.grid(row=0, column=1, padx=10, pady=10)

# Date field with calendar button
date_label = tk.Label(root, text="Date (yyyy-mm-dd):")
date_label.grid(row=1, column=0, padx=10, pady=10)
date_entry = tk.Entry(root)
date_entry.grid(row=1, column=1, padx=10, pady=10)
calendar_btn = tk.Button(root, text="Select Date", command=open_calendar)
calendar_btn.grid(row=1, column=2, padx=10, pady=10)

# Save directory field with directory picker button
save_dir_label = tk.Label(root, text="Save Directory Path:")
save_dir_label.grid(row=2, column=0, padx=10, pady=10)
save_dir_entry = tk.Entry(root)
save_dir_entry.grid(row=2, column=1, padx=10, pady=10)
dir_picker_btn = tk.Button(root, text="Select Directory", command=open_directory_picker)
dir_picker_btn.grid(row=2, column=2, padx=10, pady=10)

# Dropdown menu for selecting item
dropdown_label = tk.Label(root, text="Select Defect Type:")
dropdown_label.grid(row=3, column=0, padx=10, pady=10)
dropdown_menu = ttk.Combobox(root, values=list(item_dict.keys()))
dropdown_menu.grid(row=3, column=1, padx=10, pady=10)

# Progress bar
progress_bar = ttk.Progressbar(root, orient="horizontal", length=300, mode="determinate")
progress_bar.grid(row=5, column=0, columnspan=3, padx=10, pady=10)

# Status label
status_label = tk.Label(root, text="Status: Waiting to start...")
status_label.grid(row=6, column=0, columnspan=3, padx=10, pady=10)

# Execute button
execute_button = tk.Button(root, text="RUN", command=execute_commands)
execute_button.grid(row=4, column=0, columnspan=3, padx=10, pady=10)

# Variable to track loading animation
loading_var = tk.BooleanVar(value=False)

# Run the UI loop
root.mainloop()
