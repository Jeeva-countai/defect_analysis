import os
import csv
import glob
import shutil
import subprocess
import traceback
from flask import Flask, request, jsonify, render_template
from db import DB

app = Flask(__name__)

# Initialize DB instance
db = DB()

# Base directory for temporary data
BASE_DIR = "/home/kniti"
TEMP_DIR = os.path.join(BASE_DIR, "needln_data")
ZIP_OUTPUT_DIR = BASE_DIR

def zip_folder(folder_path, output_dir):
    """Zip the folder and save the zip file in the output directory."""
    try:
        folder_name = os.path.basename(os.path.normpath(folder_path))
        zip_path = os.path.join(output_dir, folder_name)
        shutil.make_archive(zip_path, 'zip', folder_path)
        print(f"Folder zipped and saved as: {zip_path}.zip")
        return f"{zip_path}.zip"
    except Exception as e:
        print("Error zipping folder:", str(e))
        traceback.print_exc()
        return None


def recreate_folder(path):
    """Recreate folder: delete it if exists and create a new one."""
    try:
        if os.path.exists(path):
            shutil.rmtree(path)
        os.makedirs(path, exist_ok=True)
        print(f"Recreated folder: {path}")
    except Exception as e:
        print("Error recreating folder:", str(e))
        traceback.print_exc()


def copy_files(src_dir, dest_dir, imageid):
    """Copy files based on image id from source to destination."""
    try:
        filename = os.path.splitext(imageid)[0]
        pattern = os.path.join(src_dir, f"{filename}_*.jpg")

        files_to_copy = glob.glob(pattern)

        if not files_to_copy:
            print(f"No files matched the pattern: {pattern}")
            return

        for file in files_to_copy:
            shutil.copy(file, dest_dir)
            print(f"Copied: {file}")
    except Exception as e:
        print(f"Error copying files: {e}")
        traceback.print_exc()


def transfer_files_to_remote(client_ip, zip_file_path):
    """Transfer the necessary files to the remote server."""
    try:
        # Copy the necessary files
        subprocess.run(f'scp main.py {client_ip}:/home/kniti/', shell=True, check=True)
        subprocess.run(f'scp db.py {client_ip}:/home/kniti/', shell=True, check=True)
        subprocess.run(f'scp {zip_file_path} {client_ip}:/home/kniti/needln_data.zip', shell=True, check=True)
        print("Files transferred successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Error transferring files: {e}")
        traceback.print_exc()


def execute_remote_script(client_ip, date, defect_type):
    """Execute the main.py script on the remote server."""
    try:
        # Run the remote script
        command = f"ssh {client_ip} 'python3 /home/kniti/main.py {date} {defect_type}'"
        subprocess.run(command, shell=True, check=True)
        print("Remote script executed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Error executing remote script: {e}")
        traceback.print_exc()


def retrieve_result_file(client_ip, savedir):
    """Retrieve the result file from the remote server."""
    try:
        subprocess.run(f'scp {client_ip}:/home/kniti/needln_data.zip {savedir}', shell=True, check=True)
        print("Result file retrieved successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Error retrieving result file: {e}")
        traceback.print_exc()


def clean_up_remote_server(client_ip):
    """Clean up temporary files on the remote server."""
    try:
        subprocess.run(f'ssh {client_ip} "rm -rf /home/kniti/main.py /home/kniti/db.py /home/kniti/needln_data.zip"', shell=True, check=True)
        print("Cleaned up remote server.")
    except subprocess.CalledProcessError as e:
        print(f"Error cleaning up remote server: {e}")
        traceback.print_exc()


def fetch_data(date, defecttyp_id, client_ip, savedir):
    """Fetch data, process it, and manage file transfers."""
    try:
        recreate_folder(TEMP_DIR)

        roll_id = db.get_data_frame(date)
        if not roll_id:
            return "No data found for the given date.", False

        # Existing logic to fetch and process data, generate CSV, etc.
        for rollid in roll_id:
            roll = rollid['roll_id']
            roll_name = rollid['roll_name']
            try:
                needln_data = db.get_needle_line_defects(roll, defecttyp_id)
                rollid['defect_data'] = needln_data
                if needln_data:
                    for data in needln_data:
                        filepath = os.path.join(BASE_DIR, "projects", "knit-i", "knitting-core", data['file_path'])
                        savepath = os.path.join(TEMP_DIR, roll_name, str(data['alarm_id']))
                        os.makedirs(savepath, exist_ok=True)
                        copy_files(filepath, savepath, data['filename'])
            except Exception as e:
                print(f"Error processing roll_id {roll}: {e}")
                traceback.print_exc()
                continue

        # Prepare CSV data
        csv_data = []
        for roll in roll_id:
            roll_name = roll['roll_name']
            roll_number = roll['roll_number']
            for defect in roll.get('defect_data', []):
                csv_data.append({
                    'roll_id': roll['roll_id'],
                    'roll_name': roll_name,
                    'roll_number': roll_number,
                    'alarm_id': defect['alarm_id'],
                    'defect_id': defect['defect_id'],
                    'timestamp': defect['timestamp'].isoformat(),
                    'cam_id': defect['cam_id'],
                    'filename': defect['filename'],
                    'file_path': defect['file_path'],
                    'revolution': defect['revolution'],
                    'angle': defect['angle'],
                    'coordinate': defect['coordinate'],
                    'score': defect['score']
                })

        # Write to CSV
        csv_file_path = os.path.join(TEMP_DIR, f"{date}_{defecttyp_id}.csv")
        headers = [
            'roll_id', 'roll_name', 'roll_number', 'alarm_id', 'defect_id',
            'timestamp', 'cam_id', 'filename', 'file_path',
            'revolution', 'angle', 'coordinate', 'score'
        ]

        with open(csv_file_path, mode='w', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=headers)
            writer.writeheader()
            writer.writerows(csv_data)

        # Zip the folder
        zip_file_path = zip_folder(TEMP_DIR, ZIP_OUTPUT_DIR)

        # Transfer necessary files to the remote server
        transfer_files_to_remote(client_ip, zip_file_path)

        # Execute the script on the remote server
        execute_remote_script(client_ip, date, defecttyp_id)

        # Retrieve the result file from the remote server
        retrieve_result_file(client_ip, savedir)

        # Clean up the remote server
        clean_up_remote_server(client_ip)

        # Clean up local temporary folder
        if os.path.exists(TEMP_DIR):
            shutil.rmtree(TEMP_DIR)
            print(f"Deleted temporary folder: {TEMP_DIR}")

        return zip_file_path, True
    except Exception as e:
        print("Error in fetch_data:", str(e))
        traceback.print_exc()
        return str(e), False


@app.route('/')
def index():
    """Render the index page."""
    return render_template('index.html')


@app.route('/submit', methods=['POST'])
def submit():
    """Handle the form submission for processing data."""
    data = request.json
    date = data.get('date')
    defecttyp_id = data.get('defectType')
    client_ip = data.get('client_ip')  # Assuming this is part of the request data
    savedir = data.get('saveDir')      # Directory where the result should be saved locally

    if not date or not defecttyp_id or not client_ip or not savedir:
        return jsonify({"message": "Date, defect type, client IP, and save directory are required!"}), 400

    result, success = fetch_data(date, defecttyp_id, client_ip, savedir)

    if success:
        return jsonify({"message": "Processing completed successfully!", "file": result}), 200
    else:
        return jsonify({"message": "An error occurred during processing.", "error": result}), 500

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


if __name__ == '__main__':
    app.run(debug=True)  # You can specify the port here
