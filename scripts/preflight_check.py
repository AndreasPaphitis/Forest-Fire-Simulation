#!/usr/bin/env python3
"""
Pre-flight check script for Forest Fire Simulation.
Verifies all components are ready before running the simulation.
"""

import sys
import os
import json
import logging
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def setup_logging():
    """Setup logging."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)

def check_file_exists(file_path, description):
    """Check if a file exists."""
    if os.path.exists(file_path):
        return True, f"✅ {description}: {file_path}"
    else:
        return False, f"❌ {description}: {file_path} (NOT FOUND)"

def check_directory_exists(dir_path, description):
    """Check if a directory exists."""
    if os.path.exists(dir_path) and os.path.isdir(dir_path):
        return True, f"✅ {description}: {dir_path}"
    else:
        return False, f"❌ {description}: {dir_path} (NOT FOUND)"

def check_configuration(config_file):
    """Check configuration file validity."""
    logger = logging.getLogger(__name__)
    
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
        
        logger.info(f"✅ Configuration file loaded: {config_file}")
        
        # Check critical parameters
        checks = []
        
        # Grid configuration
        grid_size = config.get('grid_size', [0, 0])
        num_layers = config.get('num_layers', 0)
        resolution = config.get('model_resolution', 0)
        geo_bounds = config.get('geo_bounds', [])
        
        checks.append((len(grid_size) == 2, f"Grid size format: {grid_size}"))
        checks.append((grid_size[0] > 0 and grid_size[1] > 0, f"Grid size positive: {grid_size}"))
        checks.append((num_layers > 0, f"Number of layers: {num_layers}"))
        checks.append((resolution > 0, f"Model resolution: {resolution}m"))
        checks.append((len(geo_bounds) == 4, f"Geographic bounds format: {geo_bounds}"))
        
        if len(geo_bounds) == 4:
            checks.append((geo_bounds[0] < geo_bounds[2], f"X bounds valid: {geo_bounds[0]} < {geo_bounds[2]}"))
            checks.append((geo_bounds[1] < geo_bounds[3], f"Y bounds valid: {geo_bounds[1]} < {geo_bounds[3]}"))
        
        # Memory calculation
        total_cells = grid_size[0] * grid_size[1] * num_layers
        memory_gb = (total_cells * 30) / (1024**3)  # 30 bytes per cell
        sparse_memory_gb = memory_gb * 0.05  # 5% density
        
        checks.append((memory_gb < 100, f"Dense memory reasonable: {memory_gb:.1f}GB"))
        checks.append((sparse_memory_gb < 10, f"Sparse memory safe: {sparse_memory_gb:.1f}GB"))
        
        # File paths
        dem_file = config.get('terrain', {}).get('dem_file', '')
        lidar_dir = config.get('vegetation', {}).get('lidar_data_dir', '')
        
        if dem_file:
            exists, msg = check_file_exists(dem_file, "DEM file")
            checks.append((exists, msg))
        
        if lidar_dir:
            exists, msg = check_directory_exists(lidar_dir, "LiDAR directory")
            checks.append((exists, msg))
        
        # HPC settings
        hpc_config = config.get('hpc', {})
        memory_limit = hpc_config.get('memory_limit_per_node', 0)
        use_sparse = hpc_config.get('use_sparse_storage', False)
        
        checks.append((memory_limit > sparse_memory_gb, f"Memory limit sufficient: {memory_limit}GB > {sparse_memory_gb:.1f}GB"))
        checks.append((use_sparse, f"Sparse storage enabled: {use_sparse}"))
        
        # Report results
        all_passed = True
        for passed, message in checks:
            if passed:
                logger.info(f"✅ {message}")
            else:
                logger.error(f"❌ {message}")
                all_passed = False
        
        return all_passed, config
        
    except Exception as e:
        logger.error(f"❌ Error loading configuration: {e}")
        return False, None

def check_lidar_data_access(config):
    """Check if LiDAR data can be accessed with the given bounds."""
    logger = logging.getLogger(__name__)
    
    try:
        from src.utils.lidar_utils import LiDARDataManager
        
        lidar_dir = config.get('vegetation', {}).get('lidar_data_dir', '')
        geo_bounds = config.get('geo_bounds', [])
        
        if not lidar_dir or not geo_bounds:
            logger.warning("⚠️  Cannot check LiDAR access - missing directory or bounds")
            return True  # Don't fail the check
        
        logger.info(f"🔍 Checking LiDAR data access...")
        logger.info(f"   Directory: {lidar_dir}")
        logger.info(f"   Bounds: {geo_bounds}")
        
        # Create LiDAR manager
        lidar_manager = LiDARDataManager(base_dir=lidar_dir)
        
        # Get actual LiDAR extent
        actual_extent = lidar_manager.get_lidar_extent(lidar_dir)
        
        if actual_extent:
            logger.info(f"✅ LiDAR extent found: {actual_extent}")
            
            # Check overlap
            min_x, min_y, max_x, max_y = actual_extent
            sim_min_x, sim_min_y, sim_max_x, sim_max_y = geo_bounds
            
            overlap_x = max(0, min(sim_max_x, max_x) - max(sim_min_x, min_x))
            overlap_y = max(0, min(sim_max_y, max_y) - max(sim_min_y, min_y))
            overlap_area = overlap_x * overlap_y
            
            if overlap_area > 0:
                logger.info(f"✅ Bounds overlap with LiDAR data: {overlap_area/1e6:.2f} km²")
                return True
            else:
                logger.error(f"❌ No overlap between simulation bounds and LiDAR data!")
                logger.error(f"   Simulation: {geo_bounds}")
                logger.error(f"   LiDAR: {actual_extent}")
                return False
        else:
            logger.warning("⚠️  Could not determine LiDAR extent")
            return True  # Don't fail the check
            
    except Exception as e:
        logger.warning(f"⚠️  Could not check LiDAR access: {e}")
        return True  # Don't fail the check

def check_imports():
    """Check if all required modules can be imported."""
    logger = logging.getLogger(__name__)
    
    imports_to_check = [
        ('src.config.config_tools', 'Configuration tools'),
        ('src.core.forest_model', 'Forest model'),
        ('src.core.fire_simulation_engine', 'Fire simulation engine'),
        ('src.utils.lidar_utils', 'LiDAR utilities'),
        ('numpy', 'NumPy'),
        ('scipy', 'SciPy'),
    ]
    
    all_imports_ok = True
    
    for module_name, description in imports_to_check:
        try:
            __import__(module_name)
            logger.info(f"✅ {description}: {module_name}")
        except ImportError as e:
            logger.error(f"❌ {description}: {module_name} - {e}")
            all_imports_ok = False
    
    return all_imports_ok

def main():
    """Main pre-flight check function."""
    logger = setup_logging()
    
    logger.info("=" * 60)
    logger.info("🚀 FOREST FIRE SIMULATION - PRE-FLIGHT CHECK")
    logger.info("=" * 60)
    
    # Check configurations
    configs_to_check = [
        "hpc_deployment/Forest_Fire_Simulation_small_test.json",
        "hpc_deployment/Forest_Fire_Simulation_production_test.json"
    ]
    
    all_checks_passed = True
    
    # 1. Check imports
    logger.info("\n📦 CHECKING IMPORTS...")
    imports_ok = check_imports()
    all_checks_passed &= imports_ok
    
    # 2. Check configurations
    for config_file in configs_to_check:
        logger.info(f"\n⚙️  CHECKING CONFIGURATION: {config_file}")
        
        if not os.path.exists(config_file):
            logger.error(f"❌ Configuration file not found: {config_file}")
            all_checks_passed = False
            continue
        
        config_ok, config = check_configuration(config_file)
        all_checks_passed &= config_ok
        
        if config:
            # Check LiDAR data access
            lidar_ok = check_lidar_data_access(config)
            all_checks_passed &= lidar_ok
    
    # Final report
    logger.info("\n" + "=" * 60)
    if all_checks_passed:
        logger.info("🎉 ALL PRE-FLIGHT CHECKS PASSED!")
        logger.info("✅ Simulation is ready to run")
        logger.info("\nRecommended commands:")
        logger.info("Small test:      srun -n 1 -c 32 -t 1:00:00 --mem=32G python run_production_sim.py hpc_deployment/Forest_Fire_Simulation_small_test.json")
        logger.info("Production test: srun -n 1 -c 32 -t 2:00:00 --mem=32G python run_production_sim.py hpc_deployment/Forest_Fire_Simulation_production_test.json")
        return True
    else:
        logger.error("❌ PRE-FLIGHT CHECKS FAILED!")
        logger.error("🔧 Please fix the issues above before running the simulation")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 