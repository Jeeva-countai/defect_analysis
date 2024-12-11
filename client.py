import os
import csv
import shutil
import traceback
import time
from datetime import datetime, timedelta
import psycopg2
import argparse
import glob
from PIL import Image, ImageDraw, ImageFont
import ast
import zipfile


BASE_DIR = '/home/kniti/projects/knit-i/knitting-core'


# Defect type mapping from name to ID
defect_type_mapping = {
    "lycra": 1,
    "hole": 2,
    "shutoff": 3,
    "needln": 4,
    "oil": 5,
    "twoply": 6,
    "stopline": 7,
    "countmix": 8,
    "missplattin": 11,
    "oilln": 12,
    "storageln": 13,
    "sample": 14
}

class Execute:
    def __init__(self, db_name="knitting", user="postgres", password="55555", host="127.0.0.1", port="5432"):
        self.db_name = db_name
        self.conn = self.connect(user, password, host, port)

    def connect(self, user, password, host, port):
        try:
            conn = psycopg2.connect(
                database=self.db_name,
                user=user,
                password=password,
                host=host,
                port=port
            )
            conn.autocommit = True
            print(f"Connected to database: {self.db_name}")
            return conn
        except Exception as e:
            print(f"Error connecting to database {self.db_name}: {e}")
            traceback.print_exc()
            raise

    def execute_query(self, query, params=None):
        try:
            cur = self.conn.cursor()
            cur.execute(query, params)
            results = cur.fetchall()
            cur.close()
            return results
        except Exception as e:
            print(f"Error executing query: {e}")
            traceback.print_exc()
            return []

    def close(self):
        try:
            self.conn.close()
            print("Database connection closed.")
        except Exception as e:
            print(f"Error closing database connection: {e}")
            traceback.print_exc()

    def get_roll_id(self, start_date, end_date):
        try:
            query = (
                f"SELECT roll_id, roll_name FROM public.roll_details WHERE "
                f"((roll_end_date >= '{start_date}'::timestamp AND roll_end_date < '{end_date}'::timestamp) "
                f"OR (roll_start_date >= '{start_date}'::timestamp AND roll_start_date < '{end_date}'::timestamp)) "
                f"AND roll_sts_id=2 ORDER BY roll_id ASC;"
            )
            data = self.execute_query(query)
            print(data)
            return data
        except Exception as e:
            print(str(e))
            traceback.print_exc()

    def get_needle_line_defects(self, roll_id, defect_type_id):
        try:
            query = f"""
                SELECT alarm_id, defect_details.defect_id, defect_details.timestamp, cam_id, filename, 
                defect_details.file_path, revolution, angle, coordinate, score 
                FROM public.combined_alarm_defect_details 
                INNER JOIN public.defect_details ON public.defect_details.defect_id = 
                public.combined_alarm_defect_details.defect_id
                WHERE defect_details.roll_id = {roll_id} AND defecttyp_id = {defect_type_id};
            """
            rows = self.execute_query(query)
            return rows
        except Exception as e:
            print(str(e))
            traceback.print_exc()

def recreate_folder(path):
    try:
        if os.path.exists(path):
            shutil.rmtree(path)
            print(f"Deleted folder: {path}")
        os.makedirs(path, exist_ok=True)
        print(f"Recreated folder with read/write permissions: {path}")
    except Exception as e:
        print(f"Error recreating folder: {e}")
        traceback.print_exc()

# Function to zip a folder and save it to a specified directory
def zip_folder(folder_path, output_dir):
    try:
        folder_name = os.path.basename(os.path.normpath(folder_path))
        zip_path = os.path.join(output_dir, folder_name)
        
        # Create zip file
        shutil.make_archive(zip_path, 'zip', folder_path)

        
        print(f"Folder zipped and saved as: {zip_path}.zip with permissions set")
    except Exception as e:
        print(f"Error zipping folder: {e}")
        traceback.print_exc()


# Function to ensure proper file path by prepending base_path
def get_full_image_path(base_path, file_path, filename):
    try:
        # Ensure file_path is clean (without starting "/")
        if file_path.startswith("/"):
            file_path = file_path.lstrip("/")
        
        # Construct full image path
        full_image_path = os.path.join(base_path, file_path, filename)

        print(f"Full image path: {full_image_path}")
        return full_image_path
    except Exception as e:
        print(f"Error in get_full_image_path: {e}")
        traceback.print_exc()
        return None

def copy_files_with_regex(base_path, dest_dir, file_path, filename):
    try:
        print(f"Starting copy_files_with_regex...")

        # Ensure the file_path does not start with "/"
        if file_path.startswith("/"):
            file_path = file_path.lstrip("/")

        # Construct the full image path
        full_image_path = os.path.join(base_path, file_path, filename)
        print(f"Full image path: {full_image_path}")

        # Extract the directory path
        directory_path = os.path.dirname(full_image_path)
        if not os.path.exists(directory_path):
            print(f"Directory does not exist: {directory_path}. Please check base_path and file_path.")
            return False

        # Create a search pattern for matching files
        file_root, file_ext = os.path.splitext(filename)
        search_pattern = os.path.join(directory_path, f"{file_root}*{file_ext}")
        print(f"Search pattern: {search_pattern}")

        # Find matching files
        matching_files = glob.glob(search_pattern)
        print(f"Matching files: {matching_files}")

        if not matching_files:
            print(f"No matching files found for {filename} in {directory_path}")
            return False

        # Copy each matching file
        for matched_file in matching_files:
            print(f"Copying file: {matched_file} to {dest_dir}")
            shutil.copy(matched_file, dest_dir)
            print(f"Copied successfully: {matched_file}")

        return True
    except Exception as e:
        print(f"Error in copy_files_with_regex: {e}")
        traceback.print_exc()
        return False

def draw_bbox_on_image(full_image_path, coordinates, score, output_path):
    print(f"Attempting to process image: {full_image_path}")

    # Check if the image file exists
    if not os.path.exists(full_image_path):
        print(f"Image not found: {full_image_path}")
        return
    
    try:
        with Image.open(full_image_path) as img:
            draw = ImageDraw.Draw(img)
            x1, y1, x2, y2 = coordinates
            draw.rectangle((x1, y1, x2, y2), outline="red", width=3)
            
            font = ImageFont.load_default()
            score_text = f"Score: {score:.2f}"
            text_width, text_height = draw.textsize(score_text, font=font)
            text_position = (x1 + (x2 - x1 - text_width) / 2, y2 + 5)
            draw.text(text_position, score_text, fill="red", font=font)
            
            img.save(output_path)
            print(f"Image with bounding box saved to {output_path}")
    except Exception as e:
        print(f"Error in draw_bbox_on_image: {e}")

def process_images_with_defect_details(csv_file_path, zip_dir):
    # Create the bbox_images directory inside the ZIP folder directory
    bbox_images_dir = os.path.join(zip_dir, "bbox_images")
    os.makedirs(bbox_images_dir, exist_ok=True)
    
    print(f"Processing CSV: {csv_file_path}")
    with open(csv_file_path, "r") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            try:
                # Read values from the CSV row
                filename = row.get('filename')
                file_path = row.get('file_path')
                coordinates_str = row.get('coordinates')
                score = row.get('score')

                # Debugging information
                print(f"CSV Row Data: filename={filename}, file_path={file_path}, coordinates={coordinates_str}, score={score}")

                if not all([filename, file_path, coordinates_str, score]):
                    raise ValueError("Missing required fields in CSV row.")
                
                # Convert score to float
                score = float(score)
                
                # Safely parse coordinates
                coordinates = ast.literal_eval(coordinates_str)
                if isinstance(coordinates, list) and len(coordinates) == 2 and \
                   all(isinstance(coord, list) and len(coord) == 2 for coord in coordinates):
                    coordinates = [coordinates[0][0], coordinates[0][1], coordinates[1][0], coordinates[1][1]]
                else:
                    raise ValueError(f"Invalid coordinates format: {coordinates_str}")
                
                # Construct full image path
                full_image_path = os.path.join(BASE_DIR, file_path.strip('/'), filename)
                
                # Construct output path for the image with bounding box
                output_path = os.path.join(bbox_images_dir, filename)
                
                # Draw bounding box
                draw_bbox_on_image(full_image_path, coordinates, score, output_path)
                
            except Exception as e:
                print(f"Error processing row: {row.get('filename', 'Unknown')} -> {e}")
    
    print(f"Processing complete. Images saved in {bbox_images_dir}.")

def fetch_data(date, defect_type, save_dir):
    try:
        # Base path for images
        base_path = "/home/kniti/projects/knit-i/knitting-core"

        # Map defect type to its ID
        defect_type_id = defect_type_mapping.get(defect_type.lower())
        if not defect_type_id:
            raise ValueError(f"Invalid defect type: {defect_type}")

        # Initialize database connection
        db = Execute()  # Assuming `Execute` is already defined elsewhere

        # Calculate date range
        start_date = datetime.strptime(date, "%Y-%m-%d").replace(hour=0, minute=0, second=0)
        end_date = start_date + timedelta(days=1)

        # Fetch roll data
        rolls = db.get_roll_id(start_date, end_date)
        if not rolls:
            raise Exception(f"No rolls found for the given date range: {start_date} - {end_date}")

        # Prepare folder paths
        full_save_dir = os.path.join("/home/kniti/defect_analysis")
        recreate_folder(full_save_dir)

        # Subfolders for images and bounding box images
        images_dir = os.path.join(full_save_dir, "images")
        bbox_images_dir = os.path.join(full_save_dir, "bbox_images")
        recreate_folder(images_dir)
        recreate_folder(bbox_images_dir)

        csv_data = []

        # Process rolls and defects
        for roll_id, roll_name in rolls:
            defects = db.get_needle_line_defects(roll_id, defect_type_id)
            if defects:
                for defect in defects:
                    defect_id = defect[1]
                    timestamp = defect[2]
                    file_path = defect[5]
                    filename = defect[4]
                    coordinates_str = defect[8]
                    score = defect[9]

                    # Add data to CSV
                    csv_data.append({
                        "roll_id": roll_id,
                        "roll_name": roll_name,
                        "defect_id": defect_id,
                        "timestamp": timestamp,
                        "file_path": file_path,
                        "filename": filename,
                        "coordinates": coordinates_str,
                        "score": score
                    })

                    # Copy images
                    if filename:
                        copy_files_with_regex(base_path, images_dir, file_path, filename)

        # Save CSV
        csv_file_path = os.path.join(full_save_dir, f"{date}_{defect_type}.csv")
        headers = ['roll_id', 'roll_name', 'defect_id', 'timestamp', 'file_path', 'filename', 'coordinates', 'score']
        with open(csv_file_path, mode='w', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=headers)
            writer.writeheader()
            writer.writerows(csv_data)

        # Process images for bounding boxes
        process_images_with_defect_details(csv_file_path, full_save_dir)

        zip_dir = "/home/kniti/defect_analysis"
        os.makedirs(zip_dir, exist_ok=True)
        zip_filename = os.path.join(zip_dir, f"{date}_{defect_type}.zip")

        # Zip the entire save directory
        with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(save_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, save_dir)  # Maintain relative paths
                    zipf.write(file_path, arcname)

        print(f"Defect analysis completed and saved to {zip_filename}")


        print(f"Processing completed. Data saved in: {full_save_dir}")

    except Exception as e:
        print(f"Error in fetch_data: {e}")
        traceback.print_exc()



# Run the fetch_data function if this script is executed directly
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch defect data from the database.")
    parser.add_argument("date", help="Date for defect analysis in YYYY-MM-DD format.")
    parser.add_argument("defect_type", help="Defect type for analysis.")
    parser.add_argument("save_dir", help="Directory to save the defect data.")
    
    args = parser.parse_args()
    fetch_data(args.date, args.defect_type, args.save_dir)
