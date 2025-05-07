import os
import glob
import json
import subprocess
import multiprocessing
import sys  # Missing import
import time
import concurrent.futures  # Missing full import
from concurrent.futures import ProcessPoolExecutor
import argparse

# ========================================================================
# USER CONFIGURATION - MODIFY THESE VALUES TO CONTROL SCRIPT BEHAVIOR
# ========================================================================
# Set DEFAULT_WORKERS to the desired number of parallel workers
# Setting to None will use all available CPU cores
DEFAULT_WORKERS = 4  # Change this value to your preferred number of workers
# ========================================================================

def process_single_file(laz_file, normalized_dir, vegetation_dir):
    """
    Process a single LAZ file - normalize it and extract vegetation.
    This function will be called by each worker process.
    
    Returns a tuple of (filename, success, error_message)
    """
    filename = os.path.basename(laz_file)
    base_filename = os.path.splitext(filename)[0]
    
    normalized_file = os.path.join(normalized_dir, f"{base_filename}_normalized.laz")
    vegetation_file = os.path.join(vegetation_dir, f"{base_filename}_vegetation.laz")
    
    # Create temp directory for this process
    process_id = os.getpid()
    temp_dir = os.path.join(os.path.dirname(normalized_dir), f"temp_{process_id}")
    os.makedirs(temp_dir, exist_ok=True)
    
    # Step 1: Normalize the point cloud
    normalize_pipeline = {
        "pipeline": [
            {
                "type": "readers.las",
                "filename": laz_file
            },
            {
                "type": "filters.hag_nn",
                "allow_extrapolation": True
            },
            {
                "type": "filters.ferry",
                "dimensions": "HeightAboveGround=>Z"
            },
            {
                "type": "writers.las",
                "filename": normalized_file,
                "compression": "laszip"
            }
        ]
    }
    
    # Create temporary pipeline file
    normalize_pipeline_file = os.path.join(temp_dir, f"temp_normalize_pipeline_{process_id}.json")
    with open(normalize_pipeline_file, 'w') as f:
        json.dump(normalize_pipeline, f, indent=4)
    
    # Run PDAL pipeline for normalization
    result = subprocess.run(["pdal", "pipeline", normalize_pipeline_file], 
                           capture_output=True, text=True)
    
    if result.returncode != 0:
        error_msg = f"Error normalizing {filename}: {result.stderr}"
        try:
            os.remove(normalize_pipeline_file)
        except:
            pass
        return (filename, False, error_msg)
    
    # Step 2: Extract vegetation
    vegetation_pipeline = {
        "pipeline": [
            {
                "type": "readers.las",
                "filename": normalized_file
            },
            {
                "type": "filters.range",
                "limits": "Classification[3:5]"
            },
            {
                "type": "writers.las",
                "filename": vegetation_file,
                "compression": "laszip"
            }
        ]
    }
    
    # Create temporary pipeline file
    vegetation_pipeline_file = os.path.join(temp_dir, f"temp_vegetation_pipeline_{process_id}.json")
    with open(vegetation_pipeline_file, 'w') as f:
        json.dump(vegetation_pipeline, f, indent=4)
    
    # Run PDAL pipeline for vegetation extraction
    result = subprocess.run(["pdal", "pipeline", vegetation_pipeline_file], 
                           capture_output=True, text=True)
    
    if result.returncode != 0:
        error_msg = f"Error extracting vegetation from {filename}: {result.stderr}"
        try:
            os.remove(normalize_pipeline_file)
            os.remove(vegetation_pipeline_file)
        except:
            pass
        return (filename, False, error_msg)
    
    # Step 3: Delete the normalized file to save disk space
    if os.path.exists(normalized_file):
        try:
            os.remove(normalized_file)
        except Exception as e:
            pass
            
    # Clean up temporary files
    try:
        os.remove(normalize_pipeline_file)
        os.remove(vegetation_pipeline_file)
        os.rmdir(temp_dir)  # Only removes if directory is empty
    except:
        pass
    
    return (filename, True, "")

def process_laz_files(input_dir, output_dir, num_workers=None):
    """
    Process all LAZ files in the input directory using parallel processing.
    
    Args:
        input_dir: Directory containing input LAZ files
        output_dir: Directory where output files will be saved
        num_workers: Number of parallel workers to use (defaults to CPU count)
    """
    # Set number of workers
    if num_workers is None:
        num_workers = multiprocessing.cpu_count()
    else:
        num_workers = min(num_workers, multiprocessing.cpu_count())
    
    print(f"Using {num_workers} parallel workers")
    
    # Create output directories
    normalized_dir = os.path.join(output_dir, "normalized")
    vegetation_dir = os.path.join(output_dir, "vegetation")
    
    os.makedirs(normalized_dir, exist_ok=True)
    os.makedirs(vegetation_dir, exist_ok=True)
    
    # Find all LAZ files in the input directory but exclude .copc.laz files
    all_files = glob.glob(os.path.join(input_dir, "*.laz"))
    laz_files = [f for f in all_files if not f.endswith('.copc.laz')]
    
    skipped_count = len(all_files) - len(laz_files)
    print(f"Found {len(laz_files)} LAZ files to process (skipped {skipped_count} .copc.laz files)")
    
    # Process files in parallel
    start_time = time.time()
    results = []
    
    with ProcessPoolExecutor(max_workers=num_workers) as executor:
        # Submit all tasks
        future_to_file = {
            executor.submit(process_single_file, laz_file, normalized_dir, vegetation_dir): laz_file 
            for laz_file in laz_files
        }
        
        # Process results as they complete
        completed = 0
        for future in concurrent.futures.as_completed(future_to_file):
            completed += 1
            file = future_to_file[future]
            try:
                filename, success, error_msg = future.result()
                if success:
                    print(f"[{completed}/{len(laz_files)}] Successfully processed {filename}")
                else:
                    print(f"[{completed}/{len(laz_files)}] {error_msg}")
                results.append((filename, success, error_msg))
            except Exception as exc:
                filename = os.path.basename(file)
                print(f"[{completed}/{len(laz_files)}] {filename} generated an exception: {exc}")
                results.append((filename, False, str(exc)))
    
    # Summarize results
    end_time = time.time()
    elapsed_time = end_time - start_time
    
    successful = [r for r in results if r[1]]
    failed = [r for r in results if not r[1]]
    
    print("\nProcessing complete!")
    print(f"Total time: {elapsed_time:.2f} seconds")
    print(f"Files processed: {len(results)}")
    print(f"Successfully processed: {len(successful)}")
    print(f"Failed: {len(failed)}")
    
    if failed:
        print("\nFailed files:")
        for filename, _, error_msg in failed:
            print(f"- {filename}: {error_msg}")

if __name__ == "__main__":
    # Set up command line argument parsing
    parser = argparse.ArgumentParser(description='Process LAZ files in parallel')
    parser.add_argument('--input', type=str, 
                        default=r"C:\Users\user\Desktop\UvA\YEAR 2\Thesis\LiDAR\2nd covering IRC",
                        help='Input directory containing LAZ files')
    parser.add_argument('--output', type=str, 
                        default=r"C:\Users\user\Desktop\UvA\YEAR 2\Thesis\LiDAR\Analysis files\Processed",
                        help='Output directory for processed files')
    parser.add_argument('--workers', type=int, default=DEFAULT_WORKERS, 
                        help=f'Number of parallel workers (default: {DEFAULT_WORKERS or "number of CPU cores"})')
    
    args = parser.parse_args()
    
    # If no arguments were provided, ask interactively
    if len(sys.argv) == 1:
        print("LAZ File Processing with Parallel Execution")
        print("------------------------------------------")
        
        # Let user confirm or change default input directory
        default_input = args.input
        user_input = input(f"Input directory [default: {default_input}]: ")
        input_dir = user_input if user_input else default_input
        
        # Let user confirm or change default output directory
        default_output = args.output
        user_output = input(f"Output directory [default: {default_output}]: ")
        output_dir = user_output if user_output else default_output
        
        # Let user specify number of workers
        default_workers = DEFAULT_WORKERS if DEFAULT_WORKERS is not None else multiprocessing.cpu_count()
        user_workers = input(f"Number of parallel workers [default: {default_workers}]: ")
        try:
            num_workers = int(user_workers) if user_workers else default_workers
        except:
            num_workers = default_workers
            print(f"Invalid value, using default: {num_workers}")
    else:
        input_dir = args.input
        output_dir = args.output
        num_workers = args.workers
    
    # Confirm number of workers before starting
    print(f"\nReady to process files with {num_workers} workers on your system.")
    confirm = input(f"Do you want to continue with {num_workers} workers? (y/n) [default: y]: ").lower()
    
    if confirm in ["n", "no"]:
        new_workers = input(f"Enter new number of workers [1-{multiprocessing.cpu_count()}]: ")
        try:
            num_workers = int(new_workers)
            if num_workers < 1 or num_workers > multiprocessing.cpu_count():
                print(f"Invalid value. Using {num_workers} workers.")
        except:
            print(f"Invalid input. Keeping {num_workers} workers.")
    
    # Start processing
    process_laz_files(input_dir, output_dir, num_workers)