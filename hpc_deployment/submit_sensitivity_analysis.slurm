#!/bin/bash
#SBATCH --job-name=forest_fire_sensitivity
#SBATCH --output=sensitivity_analysis_%j.out
#SBATCH --error=sensitivity_analysis_%j.err
#SBATCH --time=02:00:00
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=32
#SBATCH --mem=32G
#SBATCH --partition=compute

# HPC-Optimized Forest Fire Sensitivity Analysis Job
# For 32-core CPU with 32 GB RAM
# Expected runtime: 20-30 minutes for full analysis

echo "🚀 Starting HPC Forest Fire Sensitivity Analysis"
echo "Job ID: $SLURM_JOB_ID"
echo "Node: $SLURMD_NODENAME"
echo "CPUs: $SLURM_CPUS_PER_TASK"
echo "Memory: ${SLURM_MEM_PER_NODE}MB"
echo "Start time: $(date)"
echo "Working directory: $(pwd)"
echo "==============================================="

# Load required modules (adjust for your HPC system)
module purge
module load Python/3.9.6-GCCcore-11.2.0
module load GDAL/3.3.2-foss-2021b
module load GEOS/3.9.1-GCC-11.2.0

# Activate virtual environment if needed
# source /path/to/your/venv/bin/activate

# Set environment variables for optimal performance
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export VECLIB_MAXIMUM_THREADS=1
# NumExpr optimization for 128-core HPC systems
export NUMEXPR_MAX_THREADS=128
export NUMEXPR_NUM_THREADS=128

# Move to the Forest Fire Simulation directory
cd Forest-Fire-Simulation

# Verify Python environment
echo "Python version: $(python --version)"
echo "Python executable: $(which python)"

# Run HPC-optimized sensitivity analysis
echo "🔥 Starting sensitivity analysis with HPC optimization..."

# Option 1: Full HPC mode with auto-detection
python sensitivity_analysis_runner.py \
    --hpc-mode \
    --output "hpc_sensitivity_results_$(date +%Y%m%d_%H%M%S)" \
    --name "tenerife_hpc_sensitivity_$SLURM_JOB_ID"

# Option 2: Production-scale analysis (uncomment to use)
# python sensitivity_analysis_runner.py \
#     --production-scale \
#     --hpc-mode \
#     --output "production_sensitivity_results_$(date +%Y%m%d_%H%M%S)" \
#     --name "tenerife_production_sensitivity_$SLURM_JOB_ID"

# Option 3: Custom configuration (uncomment and modify as needed)
# python sensitivity_analysis_runner.py \
#     --workers 28 \
#     --memory-level 3 \
#     --config "hpc_deployment/Forest_Fire_Simulation_production_test.json" \
#     --dem-file "/path/to/your/dtm.tif" \
#     --lidar-dir "/path/to/your/pad_results/" \
#     --output "custom_sensitivity_results_$(date +%Y%m%d_%H%M%S)" \
#     --name "custom_sensitivity_$SLURM_JOB_ID"

# Capture exit status
exit_status=$?

echo "==============================================="
echo "End time: $(date)"
echo "Exit status: $exit_status"

if [ $exit_status -eq 0 ]; then
    echo "✅ Sensitivity analysis completed successfully!"
    echo "📁 Check the output directory for results"
    echo "📊 Look for summary and recommendations files"
else
    echo "❌ Sensitivity analysis failed with exit status $exit_status"
    echo "📋 Check the error log for details"
fi

echo "🔍 Memory usage summary:"
echo "Peak memory used: $(sacct -j $SLURM_JOB_ID --format=MaxRSS --noheader --units=M | head -1)"

echo "🕐 Job timing summary:"
sacct -j $SLURM_JOB_ID --format=JobID,JobName,Elapsed,State --noheader

exit $exit_status 