#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Options to Reduce Calibration Output

This script shows all the ways to reduce the amount of output from the calibration process.
"""

import json
from pathlib import Path

def show_output_reduction_options():
    """Show all ways to reduce calibration output."""
    
    print("🔇 CALIBRATION OUTPUT REDUCTION OPTIONS")
    print("=" * 60)
    
    # Option 1: Engine Logging Interval
    print("\n1. 📊 ENGINE LOGGING INTERVAL")
    print("   Current setting: 100 (logs every 100 steps)")
    print("   Options:")
    print("   - Set to 500: logs every 500 steps")
    print("   - Set to 1000: logs every 1000 steps") 
    print("   - Set to 0: disable step logging completely")
    print("   - Set to -1: disable all step logging")
    
    # Option 2: Logging Level
    print("\n2. 📝 LOGGING LEVEL")
    print("   Current: INFO level")
    print("   Options:")
    print("   - WARNING: Only show warnings and errors")
    print("   - ERROR: Only show errors")
    print("   - CRITICAL: Only show critical errors")
    
    # Option 3: Step Callback
    print("\n3. 🔄 STEP CALLBACK")
    print("   Current: Detailed progress tracking")
    print("   Options:")
    print("   - Disable step callback completely")
    print("   - Reduce callback frequency")
    print("   - Only show completion messages")
    
    # Option 4: Configuration File
    print("\n4. ⚙️  CONFIGURATION FILE CHANGES")
    print("   Edit your config file to include:")
    print("   {")
    print('     "engine_logging_interval": 1000,')
    print('     "verbose": false,')
    print('     "save_intermediate_results": false')
    print("   }")
    
    # Option 5: Command Line
    print("\n5. 🖥️  COMMAND LINE OPTIONS")
    print("   Add these flags to your calibration command:")
    print("   --quiet (if available)")
    print("   --no-verbose")
    print("   --minimal-output")
    
    # Option 6: Redirect Output
    print("\n6. 📤 OUTPUT REDIRECTION")
    print("   Redirect output to files:")
    print("   python run_tenerife_calibration.py > output.log 2>&1")
    print("   python run_tenerife_calibration.py > /dev/null 2>&1  # Suppress all output")
    
    # Option 7: Environment Variables
    print("\n7. 🌍 ENVIRONMENT VARIABLES")
    print("   Set these before running:")
    print("   export PYTHONWARNINGS='ignore'")
    print("   export NUMEXPR_MAX_THREADS=1")
    print("   export OMP_NUM_THREADS=1")

def create_minimal_config():
    """Create a minimal output configuration file."""
    
    minimal_config = {
        "engine_logging_interval": 1000,  # Log every 1000 steps instead of 100
        "verbose": False,
        "save_intermediate_results": False,
        "generate_plots": False,
        "console_output": False,
        "log_level": "WARNING"
    }
    
    config_file = "minimal_output_config.json"
    with open(config_file, 'w') as f:
        json.dump(minimal_config, f, indent=2)
    
    print(f"\n✅ Created minimal output config: {config_file}")
    print("   Use this with: --config minimal_output_config.json")

def show_current_config():
    """Show current configuration settings."""
    
    print("\n📋 CURRENT CONFIGURATION")
    print("=" * 30)
    
    config_files = [
        "hpc_deployment/Forest_Fire_Simulation_production_test.json",
        "hpc_deployment/Forest_Fire_Simulation_small_test.json",
        "hpc_deployment/Forest_Fire_Simulation_emergency_test.json"
    ]
    
    for config_file in config_files:
        if Path(config_file).exists():
            try:
                with open(config_file, 'r') as f:
                    config = json.load(f)
                
                print(f"\n📄 {config_file}:")
                print(f"   engine_logging_interval: {config.get('engine_logging_interval', 'Not set')}")
                print(f"   verbose: {config.get('verbose', 'Not set')}")
                print(f"   save_intermediate_results: {config.get('save_intermediate_results', 'Not set')}")
                
            except Exception as e:
                print(f"   Error reading {config_file}: {e}")

if __name__ == "__main__":
    show_output_reduction_options()
    show_current_config()
    create_minimal_config()
    
    print("\n🎯 RECOMMENDED QUICK FIXES:")
    print("1. Set engine_logging_interval to 1000 in your config file")
    print("2. Add --config minimal_output_config.json to your command")
    print("3. Or redirect output: python run_tenerife_calibration.py > calibration.log 2>&1")
