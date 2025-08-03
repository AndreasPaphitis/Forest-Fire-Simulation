import os
import json
import subprocess
import sys
import logging

# ------------------------------------------------------------
# Configuration
# ------------------------------------------------------------
# Set the full path to your PDAL executable (for example, from OSGeo4W or conda-forge)
PDAL_EXE = r"C:\OSGeo4W\bin\pdal.exe"

# Path to a single LAZ file you want to test.
input_laz = r"C:\Users\user\Desktop\UvA\YEAR 2\Thesis\LiDAR\2nd covering IRC merged dataset\merged_round3_1.laz"

# Output directory and file
output_dir = r"C:\Users\user\Desktop\UvA\YEAR 2\Thesis\LiDAR\Analysis files"
os.makedirs(output_dir, exist_ok=True)
output_laz = os.path.join(output_dir, "merged_round3_1_ground_point_DTM.laz")

# Configure logging to show high-level INFO messages
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s [%(levelname)s] %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')

# ------------------------------------------------------------
# Helper Function
# ------------------------------------------------------------
def run_pdal_pipeline(pipeline_dict, pipeline_file):
    """
    Saves the pipeline dictionary to a JSON file and executes it using PDAL.
    Logs high-level information about the pipeline execution.
    """
    # Write pipeline to JSON
    with open(pipeline_file, "w") as f:
        json.dump(pipeline_dict, f, indent=4)

    # Execute pipeline
    try:
        result = subprocess.run([PDAL_EXE, "pipeline", pipeline_file],
                                capture_output=True, text=True, check=True)
        logging.info(f"PDAL pipeline executed successfully: {pipeline_file}")
    except subprocess.CalledProcessError as e:
        logging.error(f"PDAL pipeline failed with return code {e.returncode}")
        logging.error("STDOUT:\n" + e.stdout)
        logging.error("STDERR:\n" + e.stderr)
        sys.exit(1)

# ------------------------------------------------------------
# Normalization Function
# ------------------------------------------------------------
def normalize_vegetation(laz_file, output_file):
    """
    Normalizes vegetation heights in a single LAZ file using filters.hag_nn.
    Writes the result to output_file.
    """
    logging.info(f"Normalizing vegetation for {laz_file} (filters.hag_nn)...")

    # Build a PDAL pipeline dictionary
    pipeline = {
        "pipeline": [
            laz_file,
            {
                "type": "filters.range",
                "limits": "Classification[3:5]"
            },
            {
                "type": "filters.hag_nn"  # no extra parameters
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
    logging.info(f"Vegetation normalization completed. Output: {output_file}")

# ------------------------------------------------------------
# Main Script
# ------------------------------------------------------------
if __name__ == "__main__":
    print("Script started.")
    try:
        # Simply call the normalization on a single file
        normalize_vegetation(input_laz, output_laz)
        logging.info("Normalization finished without errors.")
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
        sys.exit(1)

    print("Script completed successfully.")
