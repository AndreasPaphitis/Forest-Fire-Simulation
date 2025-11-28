#!/bin/bash

# ========================================================================
# Forest Fire Simulation - Job Submission Script for Snellius HPC
# ========================================================================

print_usage() {
    cat << EOF
Usage: $0 [OPTIONS] [CONFIG_FILE]

Submit a forest fire simulation job to the SLURM queue.

OPTIONS:
    -h, --help              Show this help message
    -t, --time HOURS        Set job time limit (default: 24 hours)
    -c, --cores CORES       Set number of CPU cores (default: 32)
    -m, --memory GB         Set memory limit in GB (default: 120)
    -p, --partition NAME    Set partition (default: thin)
    -e, --email EMAIL       Set email for notifications
    --dry-run              Show the sbatch command without submitting

CONFIG_FILE:
    Path to JSON configuration file (default: my_simulation_config.json)

Examples:
    $0                                          # Submit with default settings
    $0 my_config.json                          # Submit with specific config
    $0 -t 12 -c 16 -m 64 my_config.json       # Custom resources
    $0 --dry-run my_config.json               # Preview command
EOF
}

# Default values
TIME_LIMIT="24:00:00"
CORES=32
MEMORY="120G"
PARTITION="thin"
EMAIL=""
CONFIG_FILE="my_simulation_config.json"
DRY_RUN=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            print_usage
            exit 0
            ;;
        -t|--time)
            TIME_LIMIT="$2:00:00"
            shift 2
            ;;
        -c|--cores)
            CORES="$2"
            shift 2
            ;;
        -m|--memory)
            MEMORY="$2G"
            shift 2
            ;;
        -p|--partition)
            PARTITION="$2"
            shift 2
            ;;
        -e|--email)
            EMAIL="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        -*)
            echo "Unknown option: $1"
            print_usage
            exit 1
            ;;
        *)
            CONFIG_FILE="$1"
            shift
            ;;
    esac
done

# Validate configuration file exists
if [ ! -f "$CONFIG_FILE" ]; then
    echo "ERROR: Configuration file '$CONFIG_FILE' not found!"
    echo "Available configurations:"
    ls -1 *.json 2>/dev/null || echo "No JSON configuration files found in current directory"
    exit 1
fi

# Build sbatch command
SBATCH_CMD="sbatch"
SBATCH_CMD="$SBATCH_CMD --job-name=forest_fire_sim"
SBATCH_CMD="$SBATCH_CMD --partition=$PARTITION"
SBATCH_CMD="$SBATCH_CMD --nodes=1"
SBATCH_CMD="$SBATCH_CMD --ntasks-per-node=1"
SBATCH_CMD="$SBATCH_CMD --cpus-per-task=$CORES"
SBATCH_CMD="$SBATCH_CMD --mem=$MEMORY"
SBATCH_CMD="$SBATCH_CMD --time=$TIME_LIMIT"
SBATCH_CMD="$SBATCH_CMD --output=%x_%j.out"
SBATCH_CMD="$SBATCH_CMD --error=%x_%j.err"

if [ -n "$EMAIL" ]; then
    SBATCH_CMD="$SBATCH_CMD --mail-type=BEGIN,END,FAIL"
    SBATCH_CMD="$SBATCH_CMD --mail-user=$EMAIL"
fi

SBATCH_CMD="$SBATCH_CMD fire_simulation.slurm $CONFIG_FILE"

# Show job details
echo "Forest Fire Simulation Job Submission"
echo "======================================"
echo "Configuration file: $CONFIG_FILE"
echo "Partition: $PARTITION"
echo "CPU cores: $CORES"
echo "Memory: $MEMORY"
echo "Time limit: $TIME_LIMIT"
if [ -n "$EMAIL" ]; then
    echo "Email notifications: $EMAIL"
fi
echo ""

# Execute or show command
if [ "$DRY_RUN" = true ]; then
    echo "Command that would be executed:"
    echo "$SBATCH_CMD"
else
    echo "Submitting job..."
    eval $SBATCH_CMD
    
    if [ $? -eq 0 ]; then
        echo ""
        echo "Job submitted successfully!"
        echo "Monitor your job with: squeue -u \$USER"
        echo "Cancel job with: scancel <job_id>"
    else
        echo "ERROR: Job submission failed!"
        exit 1
    fi
fi 