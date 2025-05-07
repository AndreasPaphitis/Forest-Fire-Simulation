import os
import json
import subprocess
import logging

# ------------------------------------------------------------
# Configuration
# ------------------------------------------------------------
# Input LAS/LAZ file
input_laz = r"C:\Users\user\Desktop\UvA\YEAR 2\Thesis\LiDAR\2nd covering IRC\PNOA_2016_CANAR-TF_338-3142_ORT-CLA-CIR.laz"

# Output Directory
output_dir = r"C:\Users\user\Desktop\UvA\YEAR 2\Thesis\LiDAR\Analysis files"
os.makedirs(output_dir, exist_ok=True)

# Output Files
dtm_file = os.path.join(output_dir, "DTM.tif")
normalized_laz = os.path.join(output_dir, "Normalized_Points.laz")

# ------------------------------------------------------------
# Logging Configuration
# ------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# ------------------------------------------------------------
# Function: Run PDAL Pipeline
# ------------------------------------------------------------
def run_pdal_pipeline(pipeline_dict, pipeline_name="pipeline.json"):
    """
    Runs a PDAL pipeline.
    Saves the pipeline as a JSON file and executes it using PDAL.
    """
    pipeline_path = os.path.join(output_dir, pipeline_name)

    with open(pipeline_path, "w") as f:
        json.dump(pipeline_dict, f, indent=4)

    cmd = ["pdal", "pipeline", pipeline_path, "--verbose", "5"]

    logging.info(f"Running PDAL pipeline: {pipeline_name}")

    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        logging.info(f"Pipeline {pipeline_name} completed successfully!")
    except subprocess.CalledProcessError as e:
        logging.error(f"Pipeline {pipeline_name} failed!\nError:\n{e.stderr}")
        exit(1)

# ------------------------------------------------------------
# Step 1: Normalize Heights Using Ground-Based TIN
# ------------------------------------------------------------
normalization_pipeline = {
    "pipeline": [
        # Extract only ground points for the TIN
        input_laz,
        {"type": "filters.range", "limits": "Classification[2]"},
        {"type": "filters.delaunay"},  # Create TIN from ground points
        {"type": "filters.hag_delaunay"},  # Normalize heights for all points
        {
            "type": "writers.las",
            "filename": normalized_laz,
            "compression": "laszip"
        }
    ]
}

logging.info("=== Step 1: Normalizing Heights Using Ground-Based TIN ===")
run_pdal_pipeline(normalization_pipeline, "Height_Normalization.json")

logging.info(f"Height normalization completed! Normalized file: {normalized_laz}")

# ------------------------------------------------------------
# Step 2: Validate Output
# ------------------------------------------------------------
logging.info("=== Step 2: Validating Normalized Point Cloud ===")
cmd = ["pdal", "info", normalized_laz, "--dimensions", "Z"]

try:
    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    logging.info(f"Validation Output:\n{result.stdout}")
except subprocess.CalledProcessError as e:
    logging.error(f"Validation failed!\nError:\n{e.stderr}")
    exit(1)
