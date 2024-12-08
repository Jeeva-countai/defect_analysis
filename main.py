import os
import csv
import shutil
import subprocess
import traceback
import paramiko  # Import paramiko for better SSH/SCP handling
from flask import Flask, request, jsonify, render_template
from db import DB
from datetime import datetime, timedelta
import pytz
import time
import platform
from flask import send_file, send_from_directory


app = Flask(__name__)
db = DB()


class SSHManager:
    def __init__(self, username, password, use_tailscale=False):
        self.username = username
        self.password = password
        self.use_tailscale = use_tailscale  # Flag to use Tailscale authentication

    def run_command(self, hostname, command, max_attempts=10, delay=10):
        """Execute a command over SSH and capture the output, checking if the machine is online first."""
        print(f"Initialized SSHManager with username={self.username}, use_tailscale={self.use_tailscale}")

        # Check if the machine is online before attempting the SSH connection
        if not self.is_machine_online(hostname):
            print(f"Machine {hostname} is offline. Skipping SSH command execution.")
            return False, None

        for attempt in range(max_attempts):
            print(f"\n--- Attempt {attempt + 1} of {max_attempts} ---")
            try:
                # SSH command with options (adjusting for Tailscale or password authentication)
                if self.use_tailscale:
                    # Assuming that Tailscale is being used for authentication
                    ssh_command = f"ssh -o StrictHostKeyChecking=no {self.username}@{hostname} 'echo \"{self.password}\" | sudo -S bash -c \"{command}\"'"
                    print(f"Using Tailscale-based SSH command: {ssh_command}")
                else:
                    # Use standard password-based authentication
                    ssh_command = f"ssh -o StrictHostKeyChecking=no {self.username}@{hostname} 'echo \"{self.password}\" | sudo -S bash -c \"{command}\"'"
                    print(f"Using password-based SSH command: {ssh_command}")

                # Execute SSH command using subprocess
                print(f"Executing SSH command on {hostname}: {command}")
                result = subprocess.run(ssh_command, shell=True, check=True, capture_output=True, text=True)

                # Print command output
                print(f"Command output for attempt {attempt + 1}:")
                print(result.stdout)
                print(f"Command stderr (if any):")
                print(result.stderr)

                # If command is successful, return the result
                if result.returncode == 0:
                    print(f"Command executed successfully on {hostname}")
                    return True, result.stdout.strip()  # Return command output
                else:
                    print(f"Command failed with return code {result.returncode}")
                    raise subprocess.CalledProcessError(result.returncode, ssh_command, output=result.stdout, stderr=result.stderr)

            except subprocess.CalledProcessError as e:
                print(f"Attempt {attempt + 1} failed. Error executing command on {hostname}: {e}")
                print(f"stderr: {e.stderr}")
                print(f"stdout: {e.output}")
                time.sleep(delay)  # Retry delay
            except Exception as e:
                print(f"Unexpected error on attempt {attempt + 1}: {e}")
                time.sleep(delay)  # Retry delay

        print(f"Max attempts reached. Skipping command '{command}' for {hostname}.")
        return False, None  # Return None if max attempts reached

    def is_machine_online(self, ip_address):
        """Check if the machine is online using a ping command."""
        import subprocess
        import platform

        param = "-n" if platform.system().lower() == "windows" else "-c"
        try:
            result = subprocess.run(
                ["ping", param, "1", ip_address],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            # If the return code is 0, the ping was successful
            return result.returncode == 0
        except Exception as e:
            print(f"Error while pinging {ip_address}: {e}")
            return False
import os

def rename_zip_file(original_file_path, mill_name, machine_name, date, defect_type, save_dir):
    """
    Rename the fetched ZIP file to match the format:
    selectedmillname_selectedmachinename_date_defect.zip
    """
    try:
        # Generate the new file name
        new_file_name = f"{mill_name}_{machine_name}_{date}_{defect_type}.zip"
        
        # Create the new file path
        new_file_path = os.path.join(save_dir, new_file_name)

        # Rename the file
        os.rename(original_file_path, new_file_path)
        
        print(f"File renamed successfully to: {new_file_path}")
        return new_file_path, True
    except Exception as e:
        print(f"Error renaming file: {e}")
        return str(e), False


def fetch_data(date, defect_type_id, mill_id, machine_id, save_dir):
    """Fetch mill and machine details, run remote script, and fetch result."""
    try:
        mill_name = db.get_mills()
        machine_name = db.get_machines_by_mill(mill_id)
        machine_ip = db.get_machine_ip(mill_id, machine_id)
        
        if not all([mill_name, machine_name, machine_ip]):
            raise Exception(f"Missing details for mill_id={mill_id}, machine_id={machine_id}")

        # Establish SSH connection
        ssh = SSHManager(username="kniti", password="Charlemagne@1")
        success, _ = ssh.run_command(machine_ip, "hostname")
        if not success:
            raise Exception(f"SSH connection to {machine_ip} failed.")
        
        #  Check if client.py exists and remove it if it does
        print(f"Checking if client.py exists on {machine_ip}...")
        check_file_command = "test -f /home/kniti/client.py && echo 'File exists' || echo 'File does not exist'"
        success, output = ssh.run_command(machine_ip, check_file_command)
        if success and "File exists" in output:
            print("File exists, removing old client.py...")
            remove_file_command = "rm -f /home/kniti/client.py"
            success, _ = ssh.run_command(machine_ip, remove_file_command)
            if not success:
                raise Exception("Failed to remove old client.py")

        # Copy the updated client.py to the remote machine
        print(f"Copying client.py to {machine_ip}...")
        scp_command = [
            "scp", "/home/jeeva/defect_analysis/project/app/client.py",
            f"kniti@{machine_ip}:/home/kniti/client.py"
        ]
        result = subprocess.run(scp_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode != 0:
            raise Exception(f"Failed to copy client.py: {result.stderr.decode()}")


        # Run the remote script to process data
        remote_script_command = f"python3 /home/kniti/client.py {date} {defect_type_id} {save_dir}"
        success, output = ssh.run_command(machine_ip, remote_script_command)
        if not success:
            raise Exception(f"Failed to execute client.py: {output}")

        # Fetch the result file
        zip_filename = f"{date}_{defect_type_id}.zip"
        remote_file_path = f"/home/kniti/defect_analysis/{zip_filename}"
        local_file_path = os.path.join(save_dir, zip_filename)

        print(f"Fetching file from {remote_file_path} to {local_file_path}...")
        
        # Use subprocess.run with shell=False for better safety and error handling
        scp_fetch_command = [
            "scp", f"kniti@{machine_ip}:{remote_file_path}", local_file_path
        ]
        fetch_result = subprocess.run(scp_fetch_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        if fetch_result.returncode != 0:
            raise Exception(f"Failed to fetch ZIP file: {fetch_result.stderr.decode()}")
        
        print(f"ZIP file fetched successfully: {local_file_path}")
        return local_file_path, True

    except Exception as e:
        print(f"Error in fetch_data: {e}")
        traceback.print_exc()
        return str(e), False


@app.route("/")
def index():
    """Render the index page."""
    return render_template("index.html")

@app.route('/get_mills', methods=['GET'])
def get_mills():
    """Fetch mills data."""
    try:
        mills = db.get_mills()
        return jsonify({"mills": mills}), 200
    except Exception as e:
        print("Error in /get_mills route:", e)
        traceback.print_exc()
        return jsonify({"message": "Failed to fetch mills"}), 500

@app.route('/get_machines/<int:mill_id>', methods=['GET'])
def get_machines(mill_id):
    """Fetch machines data based on mill id."""
    try:
        machines = db.get_machines_by_mill(mill_id)
        return jsonify({"machines": machines}), 200
    except Exception as e:
        print("Error in /get_machines route:", e)
        traceback.print_exc()
        return jsonify({"message": "Failed to fetch machines"}), 500

@app.route("/submit", methods=["POST"])
def submit():
    """Handle form submission."""
    data = request.get_json()
    date = data.get("date")
    defect_type = data.get("defectType")
    mill_id = data.get("millId")
    machine_id = data.get("machineId")
    save_dir = data.get("saveDir")

    if not all([date, defect_type, mill_id, machine_id, save_dir]):
        return jsonify({"message": "All fields are required!"}), 400

    result_file_path, success = fetch_data(date, defect_type, mill_id, machine_id, save_dir)
    if success:
        return jsonify({"message": "Processing completed!", "file": result_file_path}), 200
    return jsonify({"message": "Processing failed.", "error": result_file_path}), 500

@app.route("/download/<date>/<defect_type_id>", methods=["POST"])
def download_file(date, defect_type_id):
    """Serve the file for download."""
    try:
        # Define the directory where files are stored
        save_dir = "/home/kniti/defect_analysis"
        
        # Generate the zip filename dynamically based on the date and defect_type_id
        zip_filename = f"{date}_{defect_type_id}.zip"
        
        # Build the full file path
        file_path = os.path.join(save_dir, zip_filename)
        
        # Check if the file exists
        if os.path.exists(file_path):
            # Serve the file from the directory
            return send_from_directory(directory=save_dir, path=zip_filename, as_attachment=True)

        else:
            return jsonify({"message": "File not found!"}), 404
    except Exception as e:
        print("Error in /download route:", e)
        traceback.print_exc()
        return jsonify({"message": "Failed to download file."}), 500



if __name__ == "__main__":
    app.run(debug=True , port = 4000)
