#!/bin/bash
#SBATCH --job-name=forest_fire_sim
#SBATCH --partition=thin
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=32
#SBATCH --mem=128G
#SBATCH --time=48:00:00
#SBATCH --output=%x_%j.out
#SBATCH --error=%x_%j.err
#SBATCH --mail-type=BEGIN,END,FAIL
#SBATCH --mail-user=a.paphitis@student.uva.nl

# ========================================================================
# Forest Fire Simulation - SLURM Job Script for Snellius HPC
# ========================================================================

echo "Starting Forest Fire Simulation at $(date)"
echo "SLURM_JOB_ID: $SLURM_JOB_ID"
echo "SLURM_JOB_NAME: $SLURM_JOB_NAME"
echo "SLURM_NTASKS: $SLURM_NTASKS"
echo "SLURM_CPUS_PER_TASK: $SLURM_CPUS_PER_TASK"
echo "SLURM_MEM_PER_NODE: $SLURM_MEM_PER_NODE"

# Load required modules
echo "Loading modules..."
module purge
module load 2023
module load Python/3.11.3-GCCcore-12.3.0
module load GDAL/3.7.1-foss-2023a
module load GEOS/3.12.0-GCC-12.3.0
module load PROJ/9.2.1-GCCcore-12.3.0
module load HDF5/1.14.0-gompi-2023a
module load netCDF/4.9.2-gompi-2023a
module load SciPy-bundle/2023.07-gfbf-2023a

echo "Loaded modules:"
module list

# Set environment variables for optimal performance
export OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK
export NUMBA_NUM_THREADS=$SLURM_CPUS_PER_TASK
export MKL_NUM_THREADS=$SLURM_CPUS_PER_TASK
export GDAL_CACHEMAX=4096  # Increased GDAL cache
export GDAL_DISABLE_READDIR_ON_OPEN=EMPTY_DIR  # HPC optimization

# NumExpr optimization for multi-core systems
export NUMEXPR_MAX_THREADS=64
export NUMEXPR_NUM_THREADS=64

# Set up scratch storage for temporary files
export SIMULATION_SCRATCH="/scratch-shared/$USER/fire_sim_$SLURM_JOB_ID"
mkdir -p "$SIMULATION_SCRATCH"
echo "Scratch storage: $SIMULATION_SCRATCH"

# Set TMPDIR to scratch storage for better I/O performance  
export TMPDIR="$SIMULATION_SCRATCH/tmp"
mkdir -p "$TMPDIR"

# Change to the job directory
cd $SLURM_SUBMIT_DIR
echo "Working directory: $(pwd)"

# Validate HPC setup before running simulation
echo "Validating HPC setup..."
python validate_hpc_setup.py
if [ $? -ne 0 ]; then
    echo "ERROR: HPC setup validation failed. Aborting job."
    exit 1
fi

# Set configuration file (default or passed as argument)
CONFIG_FILE=${1:-"Forest_Fire_Simulation_production_test.json"}
echo "Using configuration file: $CONFIG_FILE"

if [ ! -f "$CONFIG_FILE" ]; then
    echo "ERROR: Configuration file $CONFIG_FILE not found!"
    exit 1
fi

# Validate memory requirements
echo "Validating memory requirements..."
python -c "
import json
import sys
with open('$CONFIG_FILE', 'r') as f:
    config = json.load(f)

grid_size = config.get('grid_size', [1000, 1000])
num_layers = config.get('num_layers', 10)
bytes_per_cell = config.get('bytes_per_cell', 30)

total_cells = grid_size[0] * grid_size[1] * num_layers
estimated_memory_gb = (total_cells * bytes_per_cell) / (1024**3)
allocated_memory_gb = ${SLURM_MEM_PER_NODE} / 1024

print(f'Grid: {grid_size[0]}x{grid_size[1]}x{num_layers} = {total_cells:,} cells')
print(f'Estimated memory: {estimated_memory_gb:.2f}GB')
print(f'Allocated memory: {allocated_memory_gb:.2f}GB')

if estimated_memory_gb > allocated_memory_gb * 0.9:
    print(f'WARNING: Memory usage may exceed allocation!')
    sys.exit(1)
else:
    print(f'Memory requirements OK ({estimated_memory_gb/allocated_memory_gb*100:.1f}% of allocation)')
"

if [ $? -ne 0 ]; then
    echo "ERROR: Memory validation failed. Grid may be too large for allocated memory."
    exit 1
fi

# Run the simulation directly with configuration file (no path overrides)
echo "Starting simulation with $SLURM_CPUS_PER_TASK cores..."
time python run_production_sim.py \
    --config "$CONFIG_FILE" \
    --cores $SLURM_CPUS_PER_TASK \
    --hpc-mode \
    --job-id $SLURM_JOB_ID

# Check if simulation completed successfully
exit_code=$?
if [ $exit_code -eq 0 ]; then
    echo "Simulation completed successfully at $(date)"
    
    # Results are already in project space - just create summary
    echo "Creating simulation summary..."
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    
    # Find the actual results directory created by the simulation
    RESULTS_DIR=$(find /gpfs/home1/apaphitis/simulation_results -name "*${SLURM_JOB_ID}*" -type d | head -1)
    
    if [ -n "$RESULTS_DIR" ]; then
        cat > "$RESULTS_DIR/simulation_summary.txt" << EOF
Forest Fire Simulation Summary
=============================
Job ID: $SLURM_JOB_ID
Job Name: $SLURM_JOB_NAME
End Time: $TIMESTAMP
Configuration: $CONFIG_FILE
Results Directory: $RESULTS_DIR
CPUs Used: $SLURM_CPUS_PER_TASK
Memory Allocated: $SLURM_MEM_PER_NODE MB
Status: COMPLETED SUCCESSFULLY
EOF
        
        # List output files
        echo "Output files created:" >> "$RESULTS_DIR/simulation_summary.txt"
        ls -la "$RESULTS_DIR" >> "$RESULTS_DIR/simulation_summary.txt"
        
        echo "Results saved to: $RESULTS_DIR"
    else
        echo "Warning: Could not locate results directory for summary"
    fi
    
else
    echo "ERROR: Simulation failed with exit code $exit_code"
    echo "Check error logs for details"
    exit $exit_code
fi

# Clean up scratch storage  
echo "Cleaning up scratch storage..."
rm -rf "$SIMULATION_SCRATCH"

echo "Job completed at $(date)" 