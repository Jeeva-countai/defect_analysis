import os
import subprocess
import traceback
from flask import Flask, request, jsonify, render_template
from db import DB
from datetime import datetime, timedelta
import time
from flask import send_from_directory


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
        # Fetch mill and machine details from the database
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
        
        # Install Pillow on the client machine using pip3
        print(f"Installing Pillow on {machine_ip}...")
        install_pillow_command = "pip3 install Pillow"
        success, output = ssh.run_command(machine_ip, install_pillow_command)
        if not success:
            raise Exception(f"Failed to install Pillow: {output}")

        # Ensure the directory /home/kniti/defct_analysis exists
        print(f"Ensuring /home/kniti/defect_analysis exists on {machine_ip}...")
        create_dir_command = "mkdir -p /home/kniti/defect_analysis"
        success, output = ssh.run_command(machine_ip, create_dir_command)
        if not success:
            raise Exception(f"Failed to create /home/kniti/defect_analysis directory: {output}")

        # Check if client.py exists and remove it if necessary
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
            "scp", "-o", "StrictHostKeyChecking=no", "./client.py",
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

         # Check if the ZIP file exists on the remote machine
        remote_zip_path = f"/home/kniti/defect_analysis/{date}_{defect_type_id}.zip"
        print(f"Checking if {remote_zip_path} exists on the remote machine...")
        check_file_command = f"test -f {remote_zip_path} && echo 'File exists' || echo 'File does not exist'"
        success, output = ssh.run_command(machine_ip, check_file_command)
        if success and "File does not exist" in output:
            raise Exception(f"ZIP file {remote_zip_path} does not exist on the remote machine.")

        # Now fetch the ZIP file
        print(f"Fetching ZIP file from {remote_zip_path} to {save_dir}...")

        command = f"scp kniti@{machine_ip}:/home/kniti/defect_analysis/{date}_{defect_type_id}.zip {save_dir}"
        os.system(command)
       
        print(f"ZIP file fetched successfully: {os.path.join(save_dir, f'{date}_{defect_type_id}.zip')}")
        # return os.path.join(save_dir, f"{date}_{defect_type_id}.zip"), True

        # # Remove /home/kniti/defect_analysis directory after fetching the ZIP file
        print(f"Removing /home/kniti/defect_analysis directory on {machine_ip}...")
        remove_dir_command = "rm -rf /home/kniti/defect_analysis"
        success, output = ssh.run_command(machine_ip, remove_dir_command)
        if not success:
            raise Exception(f"Failed to remove /home/kniti/defect_analysis directory: {output}")

        return os.path.join(save_dir, f"{date}_{defect_type_id}.zip"), True

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
    save_dir = data.get("saveDir", "./files/")

    if not all([date, defect_type, mill_id, machine_id]):
        return jsonify({"message": "All fields except 'saveDir' are required!"}), 400

    result_file_path, success = fetch_data(date, defect_type, mill_id, machine_id, save_dir)
    if success:
        return jsonify({"message": "Processing completed!", "file": result_file_path}), 200
    return jsonify({"message": "Processing failed.", "error": result_file_path}), 500

@app.route('/download/<path:filename>')
def download_file(filename):
    directory = '/app/files/'  # Adjust to your base directory
    file_path = os.path.join(directory, filename)

    if os.path.exists(file_path):
        return send_from_directory(directory, filename, as_attachment=True)
    else:
        return jsonify({"error": "File not found"}), 404


if __name__ == "__main__":
    app.run(debug=True , port = 9996, host="0.0.0.0", threaded=True)
