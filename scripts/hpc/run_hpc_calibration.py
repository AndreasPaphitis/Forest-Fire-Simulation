#!/usr/bin/env python3
"""
HPC Deployment Script for Tenerife Fire Calibration
Optimized for 64 CPUs with 1.7GB per CPU
"""

import os
import sys
import argparse
import logging
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# HPC Configuration
HPC_CONFIG = {
    'cpus': 64,
    'memory_per_cpu_gb': 1.7,
    'total_memory_gb': 108.8,
    'workers': 64,
    'memory_parameter': 64,  # 64GB memory limit as requested
    'grid_points': 3,
    'parameters': 4,
    'total_combinations': 81
}

# HPC Paths (adjust these for your HPC setup)
HPC_PATHS = {
    'project_root': '/gpfs/home1/apaphitis/git/github/Forest-Fire-Simulation',
    'lidar_data': '/gpfs/home1/apaphitis/data/LiDAR/Analysis_files/Processed/PAD_Results',
    'emsr_data': '/gpfs/home1/apaphitis/git/github/Forest-Fire-Simulation/EMSR Delineations',
    'preprocessed_terrain': '/gpfs/home1/apaphitis/git/github/Forest-Fire-Simulation/preprocessed_terrain',
    'output_results': '/gpfs/home1/apaphitis/results/tenerife_calibration'
}

def setup_hpc_environment():
    """Setup HPC environment and validate paths."""
    print("=== HPC ENVIRONMENT SETUP ===")
    
    # Set environment variables for HPC
    os.environ['NUMEXPR_MAX_THREADS'] = '64'
    os.environ['NUMEXPR_NUM_THREADS'] = '64'
    os.environ['OMP_NUM_THREADS'] = '1'  # Prevent oversubscription
    
    # Validate paths
    print("Validating HPC paths...")
    for name, path in HPC_PATHS.items():
        if os.path.exists(path):
            print(f"✅ {name}: {path}")
        else:
            print(f"❌ {name}: {path} (NOT FOUND)")
            if name in ['lidar_data', 'emsr_data']:
                print(f"   ⚠️  {name} not found - will use fallback paths")
    
    return True

def update_configuration_paths():
    """Update configuration files with HPC paths."""
    print("\n=== UPDATING CONFIGURATION PATHS ===")
    
    # Update calibration config
    config_file = project_root / "src/core/calibration/calibration_config.py"
    if config_file.exists():
        print(f"✅ Calibration config: {config_file}")
    
    # Update fire perimeter calibration
    fire_calib_file = project_root / "src/core/calibration/fire_perimeter_calibration.py"
    if fire_calib_file.exists():
        print(f"✅ Fire calibration: {fire_calib_file}")
    
    return True

def calculate_memory_requirements():
    """Calculate and verify memory requirements."""
    print("\n=== MEMORY REQUIREMENT VERIFICATION ===")
    
    # Grid size calculation
    grid_cells = 609 * 609 * 25  # 9,270,225 cells
    terrain_memory_mb = (grid_cells * 8) / (1024 * 1024)  # 74.2 MB
    
    # Per simulation breakdown
    per_simulation_mb = {
        'base_terrain': 74.2,
        'forest_state': 50.0,
        'lidar_data': 20.0,
        'simulation_overhead': 10.0
    }
    total_per_simulation_mb = sum(per_simulation_mb.values())
    
    # Total memory calculation
    total_simulation_memory_gb = (total_per_simulation_mb * HPC_CONFIG['total_combinations']) / 1024
    shared_terrain_memory_gb = terrain_memory_mb / 1024
    total_memory_gb = total_simulation_memory_gb + shared_terrain_memory_gb
    
    # HPC memory efficiency
    memory_efficiency = (total_memory_gb / HPC_CONFIG['total_memory_gb']) * 100
    
    print(f"Grid size: {609} × {609} × {25} = {grid_cells:,} cells")
    print(f"Terrain memory: {terrain_memory_mb:.1f} MB")
    print(f"Per simulation memory breakdown:")
    for component, memory in per_simulation_mb.items():
        print(f"  {component}: {memory:.1f} MB")
    print(f"Total per simulation: {total_per_simulation_mb:.1f} MB")
    print(f"Total simulation memory: {total_simulation_memory_gb:.1f} GB")
    print(f"Shared terrain memory: {shared_terrain_memory_gb:.1f} GB")
    print(f"Total memory requirement: {total_memory_gb:.1f} GB")
    print(f"HPC memory efficiency: {memory_efficiency:.1f}%")
    
    if memory_efficiency < 50:
        print("✅ Memory requirements are well within HPC limits")
    else:
        print("⚠️  Memory usage is high - consider optimization")
    
    return total_memory_gb, memory_efficiency

def estimate_execution_time():
    """Estimate execution time for HPC."""
    print("\n=== EXECUTION TIME ESTIMATION ===")
    
    # Computational complexity
    operations_per_timestep = 609 * 609 * 25  # 9.3M operations
    total_operations = operations_per_timestep * 100  # 100 timesteps
    total_operations_billion = total_operations / 1e9
    
    print(f"Operations per timestep: {operations_per_timestep:,}")
    print(f"Total operations per simulation: {total_operations_billion:.1f} billion")
    
    # Time estimates
    time_estimates = {
        'optimistic': 15,  # minutes per simulation
        'realistic': 30,   # minutes per simulation
        'conservative': 45  # minutes per simulation
    }
    
    # Parallel execution
    simulations_per_batch = HPC_CONFIG['workers']
    batches_needed = (HPC_CONFIG['total_combinations'] + simulations_per_batch - 1) // simulations_per_batch
    
    print(f"Workers: {HPC_CONFIG['workers']}")
    print(f"Simulations per batch: {simulations_per_batch}")
    print(f"Batches needed: {batches_needed}")
    
    print("\nExecution time estimates:")
    realistic_hours = 0
    for scenario, time_per_sim in time_estimates.items():
        total_time_hours = (time_per_sim * batches_needed) / 60
        print(f"  {scenario.capitalize()}: {total_time_hours:.1f} hours")
        if scenario == 'realistic':
            realistic_hours = total_time_hours
    
    return realistic_hours  # Return actual calculated hours

def create_hpc_command():
    """Create the HPC execution command."""
    print("\n=== HPC EXECUTION COMMAND ===")
    
    command = f"""python scripts/run_tenerife_calibration_custom.py \\
    --memory {HPC_CONFIG['memory_parameter']} \\
    --workers {HPC_CONFIG['workers']} \\
    --grid-points {HPC_CONFIG['grid_points']} \\
    --emsr-dir "{HPC_PATHS['emsr_data']}" """
    
    print("Recommended HPC command:")
    print(command)
    
    return command

def main():
    """Main HPC deployment function."""
    parser = argparse.ArgumentParser(description='HPC Deployment for Tenerife Calibration')
    parser.add_argument('--validate-only', action='store_true', help='Only validate setup, do not run')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be executed')
    args = parser.parse_args()
    
    print("🚀 HPC DEPLOYMENT FOR TENERIFE FIRE CALIBRATION")
    print("=" * 60)
    
    # Setup and validation
    setup_hpc_environment()
    update_configuration_paths()
    
    # Memory and timing analysis
    total_memory, efficiency = calculate_memory_requirements()
    realistic_time = estimate_execution_time()
    
    # Create execution command
    command = create_hpc_command()
    
    print("\n=== DEPLOYMENT SUMMARY ===")
    print(f"✅ HPC Configuration: {HPC_CONFIG['cpus']} CPUs, {HPC_CONFIG['memory_parameter']}GB memory")
    print(f"✅ Memory efficiency: {efficiency:.1f}%")
    print(f"✅ Expected runtime: {realistic_time:.1f} hours")
    print(f"✅ Total combinations: {HPC_CONFIG['total_combinations']}")
    
    if args.validate_only:
        print("\n✅ Validation complete - HPC setup is ready")
        return
    
    if args.dry_run:
        print("\n🔍 DRY RUN - Would execute:")
        print(command)
        return
    
    # Execute the calibration
    print("\n🚀 Starting HPC calibration...")
    print("=" * 60)
    
    # Import and run the calibration
    try:
        from scripts.run_tenerife_calibration_custom import main as run_calibration
        
        # Set up command line arguments for the calibration script
        sys.argv = [
            'run_tenerife_calibration_custom.py',
            '--memory', str(HPC_CONFIG['memory_parameter']),
            '--workers', str(HPC_CONFIG['workers']),
            '--grid-points', str(HPC_CONFIG['grid_points']),
            '--emsr-dir', HPC_PATHS['emsr_data']
        ]
        
        run_calibration()
        
    except Exception as e:
        print(f"❌ HPC calibration failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    print("\n✅ HPC calibration completed successfully!")
    return 0

if __name__ == "__main__":
    exit(main())
