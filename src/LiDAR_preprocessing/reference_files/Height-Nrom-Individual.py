import os
import glob
import json
import subprocess
import sys
import logging

# ------------------------------------------------------------
# Configuration
# ------------------------------------------------------------
# By default, run single-threaded.
num_workers = 1

# Full path to your pdal.exe; update as needed.
PDAL_EXE = r"C:\OSGeo4W\bin\pdal.exe"

# Input and output directories
input_dir = r"C:\Users\user\Desktop\UvA\YEAR 2\Thesis\LiDAR\2nd covering IRC"
output_dir = r"C:\Users\user\Desktop\UvA\YEAR 2\Thesis\LiDAR\Analysis files"
os.makedirs(output_dir, exist_ok=True)

# Configure logging to show high-level INFO messages
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def run_pdal_pipeline(pipeline_dict, pipeline_file):
    """
    Writes the pipeline dictionary to a JSON file and executes it with PDAL.
    Logs success or error messages.
    """
    with open(pipeline_file, "w") as f:
        json.dump(pipeline_dict, f, indent=4)

    try:
        result = subprocess.run(
            [PDAL_EXE, "pipeline", pipeline_file],
            capture_output=True, text=True, check=True
        )
        logging.info(f"PDAL pipeline executed successfully: {pipeline_file}")
    except subprocess.CalledProcessError as e:
        logging.error(f"PDAL pipeline failed with return code {e.returncode}")
        logging.error("STDOUT:\n" + e.stdout)
        logging.error("STDERR:\n" + e.stderr)
        sys.exit(1)

def main():
    print("Script started.")
    
    # Gather all .laz files, excluding .copc.laz
    all_laz = glob.glob(os.path.join(input_dir, "*.laz"))
    laz_files = [f for f in all_laz if not f.endswith(".copc.laz")]

    if not laz_files:
        logging.error("No valid .laz files found in the input directory (excluding .copc.laz).")
        sys.exit(1)

    logging.info(f"Found {len(laz_files)} LAZ files to process.")

    # Single-thread loop
    for laz_file in laz_files:
        base_name = os.path.splitext(os.path.basename(laz_file))[0]
        output_file = os.path.join(output_dir, base_name + "_veg_hag.laz")

        logging.info(f"Starting normalization for {laz_file}...")

        # 1) Read all points (including ground).
        # 2) filters.hag_nn => tries to compute height above ground from ground points in the same file.
        # 3) filters.range => keep only classifications 3-5 (vegetation).
        # 4) writers.las => output final LAZ

        pipeline = {
            "pipeline": [
                laz_file,
                {
                    "type": "filters.hag_nn"
                    # No extra parameters -> avoids "Unexpected argument" errors
                },
                {
                    "type": "filters.range",
                    "limits": "Classification[3:5]"
                },
                {
                    "type": "writers.las",
                    "filename": output_file,
                    "compression": "laszip"
                }
            ]
        }

        pipeline_file = output_file + "_pipeline.json"
        run_pdal_pipeline(pipeline, pipeline_file)

        logging.info(f"Finished normalizing {laz_file}. Output: {output_file}")

    print("Script completed successfully.")

if __name__ == "__main__":
    main()
