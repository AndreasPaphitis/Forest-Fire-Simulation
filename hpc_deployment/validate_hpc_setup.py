git #!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Enhanced HPC Environment Validation Script for Forest Fire Simulation

This script validates that all required dependencies, modules, and configurations
are properly set up for running forest fire simulations on the HPC cluster.
"""

import sys
import os
import json
import subprocess
import importlib
from pathlib import Path
from typing import Dict, List, Optional, Tuple

def print_header():
    """Print validation header."""
    print("="*80)
    print("🔥 FOREST FIRE SIMULATION - HPC ENVIRONMENT VALIDATION")
    print("="*80)
    print()

def print_section(title: str):
    """Print section header."""
    print(f"\n🔍 {title}")
    print("-" * (len(title) + 4))

def print_check(item: str, passed: bool, details: str = ""):
    """Print validation check result."""
    status = "✅" if passed else "❌"
    print(f"{status} {item:<50} {details}")
    return passed

def check_python_version() -> bool:
    """Check Python version requirements."""
    print_section("Python Environment")
    
    version = sys.version_info
    required_major, required_minor = 3, 8
    
    version_str = f"{version.major}.{version.minor}.{version.micro}"
    is_valid = version.major == required_major and version.minor >= required_minor
    
    print_check("Python version", is_valid, 
               f"({version_str} - requires >= {required_major}.{required_minor})")
    
    return is_valid

def check_required_modules() -> Tuple[bool, List[str]]:
    """Check required Python modules."""
    print_section("Required Python Modules")
    
    required_modules = [
        'numpy', 'scipy', 'matplotlib', 'scikit-learn',
        'rasterio', 'fiona', 'shapely', 'pyproj', 'gdal'
    ]
    
    missing_modules = []
    all_passed = True
    
    for module in required_modules:
        try:
            importlib.import_module(module)
            print_check(f"{module} module", True, "available")
        except ImportError:
            print_check(f"{module} module", False, "MISSING")
            missing_modules.append(module)
            all_passed = False
    
    return all_passed, missing_modules

def check_system_modules() -> bool:
    """Check HPC system modules (if available)."""
    print_section("HPC System Modules")
    
    # Check if we're on an HPC system with module command
    try:
        result = subprocess.run(['module', 'list'], 
                              capture_output=True, text=True, timeout=10)
        print_check("Module system", True, "available")
        
        # Check for specific modules we need
        module_output = result.stderr  # module command outputs to stderr
        required_hpc_modules = ['Python', 'GDAL', 'GEOS', 'PROJ']
        
        for module in required_hpc_modules:
            if module in module_output:
                print_check(f"{module} module", True, "loaded")
            else:
                print_check(f"{module} module", False, "not loaded")
        
        return True
        
    except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
        print_check("Module system", False, "not available (local environment)")
        return False

def check_memory_and_resources() -> bool:
    """Check available system resources."""
    print_section("System Resources")
    
    try:
        import psutil
        
        # Check available memory
        memory = psutil.virtual_memory()
        memory_gb = memory.total / (1024**3)
        memory_available_gb = memory.available / (1024**3)
        
        print_check("Total system memory", True, f"{memory_gb:.1f} GB")
        print_check("Available memory", memory_available_gb > 8, 
                   f"{memory_available_gb:.1f} GB (recommends > 8 GB)")
        
        # Check CPU cores
        cpu_count = psutil.cpu_count()
        print_check("CPU cores", cpu_count >= 4, f"{cpu_count} cores")
        
        return memory_available_gb > 8 and cpu_count >= 4
        
    except ImportError:
        print_check("Resource monitoring", False, "psutil not available")
        return False

def validate_configuration_file(config_path: str) -> Tuple[bool, Dict]:
    """Validate simulation configuration file."""
    print_section(f"Configuration Validation: {config_path}")
    
    if not os.path.exists(config_path):
        print_check("Configuration file exists", False, f"File not found: {config_path}")
        return False, {}
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        print_check("Configuration file format", True, "valid JSON")
    except json.JSONDecodeError as e:
        print_check("Configuration file format", False, f"Invalid JSON: {e}")
        return False, {}
    
    # Check required configuration keys
    required_keys = [
        'model_resolution', 'grid_size', 'num_layers', 'max_steps',
        'wind_speed', 'wind_direction', 'ignition_points'
    ]
    
    missing_keys = []
    for key in required_keys:
        has_key = key in config
        print_check(f"Config parameter: {key}", has_key)
        if not has_key:
            missing_keys.append(key)
    
    # Validate grid size
    grid_size = config.get('grid_size', [0, 0])
    if isinstance(grid_size, list) and len(grid_size) == 2:
        total_cells = grid_size[0] * grid_size[1] * config.get('num_layers', 1)
        print_check("Grid size format", True, f"{grid_size[0]}×{grid_size[1]} = {total_cells:,} cells")
        
        # Memory estimation
        bytes_per_cell = config.get('bytes_per_cell', 10)
        estimated_memory_mb = (total_cells * bytes_per_cell) / (1024**2)
        print_check("Estimated memory usage", estimated_memory_mb < 100000, 
                   f"{estimated_memory_mb:.1f} MB")
    else:
        print_check("Grid size format", False, "invalid format")
    
    return len(missing_keys) == 0, config

def check_simulation_modules() -> bool:
    """Test import of simulation modules."""
    print_section("Simulation Module Integration")
    
    try:
        # Add project root to path if needed
        project_root = Path(__file__).parent.parent
        src_path = project_root / 'src'
        
        if str(src_path) not in sys.path:
            sys.path.insert(0, str(src_path))
        
        # Also add project root to path
        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))
        
        from src.config.config_tools import ModelConfig, load_config
        print_check("Config tools import", True)
        
        from src.core.fire_simulation_engine import FireSimulationEngine
        print_check("Fire simulation engine import", True)
        
        from src.core.forest_model import ForestModel  
        print_check("Forest model import", True)
        
        # Test basic configuration creation
        test_config = ModelConfig(grid_size=10, num_layers=3, max_steps=5)
        print_check("Configuration creation", True, "basic config created")
        
        return True
        
    except ImportError as e:
        print_check("Simulation modules", False, f"Import error: {e}")
        return False
    except Exception as e:
        print_check("Simulation modules", False, f"Error: {e}")
        return False

def check_file_permissions() -> bool:
    """Check file system permissions."""
    print_section("File System Permissions")
    
    # Test basic I/O operations  
    print_status("Testing file I/O operations...")
    
    # Use a more appropriate test directory name
    results_dir = Path("hpc_validation_test")
    try:
        results_dir.mkdir(exist_ok=True)
        test_file = results_dir / "test_write.txt"
        test_file.write_text("HPC validation test")
        test_file.unlink()
        results_dir.rmdir()
        print_check("Results directory write access", True, str(results_dir))
    except Exception as e:
        print_check("Results directory write access", False, f"Error: {e}")
        issues.append(f"Cannot write to results directory: {e}")
    
    # Check read permissions for current directory
    try:
        list(Path(".").iterdir())
        print_check("Current directory read access", True)
    except Exception as e:
        print_check("Current directory read access", False, f"Error: {e}")
        return False
    
    return True

def main():
    """Main validation function."""
    print_header()
    
    # Track overall validation status
    all_checks_passed = True
    warnings = []
    
    # Run all validation checks
    all_checks_passed &= check_python_version()
    
    modules_ok, missing_modules = check_required_modules()
    all_checks_passed &= modules_ok
    if missing_modules:
        warnings.append(f"Missing Python modules: {', '.join(missing_modules)}")
    
    # HPC modules check (warning only, not required for local testing)
    hpc_modules_ok = check_system_modules()
    if not hpc_modules_ok:
        warnings.append("HPC module system not available (OK for local testing)")
    
    all_checks_passed &= check_memory_and_resources()
    all_checks_passed &= check_simulation_modules()
    all_checks_passed &= check_file_permissions()
    
    # Check configuration files if available
    config_files = list(Path(".").glob("*.json"))
    if config_files:
        for config_file in config_files:
            config_ok, _ = validate_configuration_file(str(config_file))
            all_checks_passed &= config_ok
    else:
        warnings.append("No configuration files found in current directory")
    
    # Print final results
    print("\n" + "="*80)
    if all_checks_passed:
        print("🎉 VALIDATION SUCCESSFUL - HPC environment ready for simulation!")
    else:
        print("❌ VALIDATION FAILED - Please fix the issues above before running simulation")
    
    if warnings:
        print("\n⚠️  Warnings:")
        for warning in warnings:
            print(f"   • {warning}")
    
    print("="*80)
    
    # Exit with appropriate code
    sys.exit(0 if all_checks_passed else 1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Validation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Validation failed with unexpected error: {e}")
        sys.exit(1)