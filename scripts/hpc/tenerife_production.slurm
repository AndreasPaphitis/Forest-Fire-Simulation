#!/bin/bash
#SBATCH --job-name=tenerife_calibration
#SBATCH --partition=highmem
#SBATCH --nodes=4
#SBATCH --ntasks-per-node=8
#SBATCH --cpus-per-task=4
#SBATCH --mem=512G
#SBATCH --time=24:00:00
#SBATCH --output=tenerife_calibration_%j.out
#SBATCH --error=tenerife_calibration_%j.err
#SBATCH --mail-type=BEGIN,END,FAIL
#SBATCH --account=research

# CRITICAL: Production setup for 9.3 billion cell Tenerife simulation
# Requires high-memory nodes with 512GB+ RAM per node

echo "=========================================="
echo "🏔️  TENERIFE FULL-SCALE CALIBRATION"
echo "Grid: 15,121 × 24,741 × 25 = 9.3B cells"
echo "Nodes: 4 × 512GB = 2TB total memory"
echo "=========================================="

# Load required modules
module load Python/3.11.3-GCCcore-12.3.0
module load SciPy-bundle/2023.07-gfbf-2023a
module load matplotlib/3.7.2-gfbf-2023a

# Set memory optimization environment variables
export OMP_NUM_THREADS=4
export MALLOC_TRIM_THRESHOLD_=0
export MALLOC_MMAP_THRESHOLD_=65536

# Python memory optimizations
export PYTHONHASHSEED=0
export PYTHONUNBUFFERED=1

# Enable huge pages if available
echo "🔧 Checking huge pages availability..."
if [ -f /proc/sys/vm/nr_hugepages ]; then
    echo "Huge pages available: $(cat /proc/sys/vm/nr_hugepages)"
else
    echo "Huge pages not available"
fi

# Check memory configuration
echo "💾 Memory configuration:"
echo "Total memory: $(free -h | grep Mem | awk '{print $2}')"
echo "Available memory: $(free -h | grep Mem | awk '{print $7}')"
echo "Swap space: $(free -h | grep Swap | awk '{print $2}')"

# Create output directory
OUTPUT_DIR="tenerife_production_${SLURM_JOB_ID}"
mkdir -p "$OUTPUT_DIR"
echo "📁 Output directory: $OUTPUT_DIR"

# Setup Python environment
echo "🐍 Setting up Python environment..."
cd "$SLURM_SUBMIT_DIR"

# Check Python packages
echo "📦 Checking critical packages..."
python -c "import numpy; print(f'NumPy: {numpy.__version__}')"
python -c "import scipy; print(f'SciPy: {scipy.__version__}')"
python -c "try: import psutil; print(f'psutil: {psutil.__version__}'); except: print('psutil: NOT AVAILABLE')"

# Memory monitoring function
monitor_memory() {
    while true; do
        timestamp=$(date '+%H:%M:%S')
        memory_usage=$(free | grep Mem | awk '{printf "%.1f", $3/1024/1024}')
        echo "[$timestamp] Memory usage: ${memory_usage} GB"
        sleep 30
    done
}

# Start memory monitoring in background
echo "👁️  Starting memory monitoring..."
monitor_memory > "memory_monitor_${SLURM_JOB_ID}.log" &
MONITOR_PID=$!

# Cleanup function
cleanup() {
    echo "🧹 Cleaning up..."
    kill $MONITOR_PID 2>/dev/null
    
    # Clean up any shared memory
    echo "🧹 Cleaning shared memory..."
    find /dev/shm -name "psm_*" -user $USER -delete 2>/dev/null || true
    
    echo "✅ Cleanup completed"
}

# Set cleanup trap
trap cleanup EXIT

# Pre-simulation memory check
echo "🔍 Pre-simulation memory check..."
python3 << 'EOF'
import psutil
import sys

# Check available memory
memory = psutil.virtual_memory()
available_gb = memory.available / (1024**3)
total_gb = memory.total / (1024**3)

print(f"Total memory: {total_gb:.1f} GB")
print(f"Available memory: {available_gb:.1f} GB")
print(f"Memory percentage used: {memory.percent:.1f}%")

# Estimate memory requirement for full grid
cells = 15121 * 24741 * 25
memory_estimate_gb = cells * 27 / (1024**3)  # 27 bytes per cell
terrain_memory_gb = 9.7  # From preprocessed terrain

total_estimate_gb = memory_estimate_gb + terrain_memory_gb

print(f"\nMemory requirements estimate:")
print(f"Grid cells: {cells:,} (9.3B)")
print(f"Estimated grid memory: {memory_estimate_gb:.1f} GB")
print(f"Terrain memory: {terrain_memory_gb:.1f} GB")
print(f"Total estimated: {total_estimate_gb:.1f} GB")

if available_gb < total_estimate_gb:
    print(f"❌ WARNING: Available memory ({available_gb:.1f} GB) < Required ({total_estimate_gb:.1f} GB)")
    print("   Simulation may fail - consider using smaller grid or more memory")
    sys.exit(1)
else:
    print(f"✅ Sufficient memory available")
EOF

if [ $? -ne 0 ]; then
    echo "❌ Pre-simulation memory check failed"
    exit 1
fi

# Run the calibration simulation
echo "🚀 Starting Tenerife calibration simulation..."
echo "Configuration: hpc_deployment/full_tenerife_production.json"
echo "Start time: $(date)"

# Set process limits
ulimit -v unlimited  # Virtual memory
ulimit -m unlimited  # Physical memory
ulimit -s unlimited  # Stack size

# Run simulation with error handling
python -c "
import sys
sys.path.insert(0, '.')

# Import production memory manager
from src.utils.production_memory_manager import setup_production_memory_protection

# Setup production memory protection
print('🛡️  Setting up production memory protection...')
memory_manager = setup_production_memory_protection()

# Add emergency callback to save state
def emergency_callback(stats):
    print(f'🚨 EMERGENCY: Process memory {stats.process_rss_gb:.1f}GB')
    print('🚨 Triggering emergency checkpoint...')
    # Could trigger checkpoint here

memory_manager.add_callback('emergency', emergency_callback)

try:
    # Import and run simulation
    from src.core.run_fire_simulation import main
    print('🔥 Starting forest fire simulation...')
    
    # Override config file
    sys.argv = ['run_fire_simulation.py', '--config', 'hpc_deployment/full_tenerife_production.json']
    
    # Run simulation
    main()
    
    print('✅ Simulation completed successfully!')
    
except Exception as e:
    print(f'❌ Simulation failed: {e}')
    import traceback
    traceback.print_exc()
    
    # Get final memory report
    report = memory_manager.get_memory_report()
    print(f\"Final memory usage: {report['current']['process_rss_gb']:.1f} GB\")
    
    sys.exit(1)
finally:
    # Stop memory monitoring
    memory_manager.stop_monitoring()
"

SIMULATION_EXIT_CODE=$?

echo "Simulation completed with exit code: $SIMULATION_EXIT_CODE"
echo "End time: $(date)"

# Final memory check
echo "📊 Final memory status:"
free -h

# Collect results
echo "📋 Collecting results..."
if [ $SIMULATION_EXIT_CODE -eq 0 ]; then
    echo "✅ Simulation successful - results in $OUTPUT_DIR"
    
    # Archive results
    tar -czf "tenerife_results_${SLURM_JOB_ID}.tar.gz" "$OUTPUT_DIR"
    echo "📦 Results archived: tenerife_results_${SLURM_JOB_ID}.tar.gz"
    
else
    echo "❌ Simulation failed - check error logs"
    
    # Save debug information
    echo "Saving debug information..."
    cp "memory_monitor_${SLURM_JOB_ID}.log" "$OUTPUT_DIR/"
    
    # System information
    echo "System info:" > "$OUTPUT_DIR/system_info.txt"
    uname -a >> "$OUTPUT_DIR/system_info.txt"
    free -h >> "$OUTPUT_DIR/system_info.txt"
    lscpu >> "$OUTPUT_DIR/system_info.txt"
fi

echo "=========================================="
echo "🏔️  TENERIFE CALIBRATION COMPLETED"
echo "Job ID: $SLURM_JOB_ID"
echo "Exit Code: $SIMULATION_EXIT_CODE"
echo "=========================================="

exit $SIMULATION_EXIT_CODE
