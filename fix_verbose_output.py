#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Fix Verbose Output in Fire Simulation Engine

This script modifies the fire simulation engine to reduce verbose output
by replacing full array dumps with summary information.
"""

import re
from pathlib import Path

def fix_verbose_output():
    """Fix the verbose output in fire_simulation_engine.py."""
    
    engine_file = Path("src/core/fire_simulation_engine.py")
    
    if not engine_file.exists():
        print("❌ Could not find fire_simulation_engine.py")
        return False
    
    # Read the file
    with open(engine_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Original problematic lines
    problematic_lines = [
        'logger.info(f"ENGINE DEBUG: Initial active_cells detected: {self.active_cells}") # DEBUG MODIFIED',
        'logger.info(f"ENGINE DEBUG: Entering _process_step. Current active_cells: {self.active_cells}") # DEBUG MODIFIED',
        'logger.info(f"ENGINE DEBUG: _process_step: current_active_cells to iterate: {current_active_cells}") # DEBUG MODIFIED'
    ]
    
    # Replacement lines
    replacement_lines = [
        'logger.info(f"ENGINE DEBUG: Initial active_cells detected: {len(self.active_cells)} cells") # DEBUG MODIFIED',
        'logger.info(f"ENGINE DEBUG: Entering _process_step. Current active_cells: {len(self.active_cells)} cells") # DEBUG MODIFIED',
        'logger.info(f"ENGINE DEBUG: _process_step: current_active_cells to iterate: {len(current_active_cells)} cells") # DEBUG MODIFIED'
    ]
    
    # Make the replacements
    original_content = content
    for original, replacement in zip(problematic_lines, replacement_lines):
        if original in content:
            content = content.replace(original, replacement)
            print(f"✅ Fixed: {original[:50]}...")
        else:
            print(f"⚠️  Could not find: {original[:50]}...")
    
    # Check if any changes were made
    if content == original_content:
        print("❌ No changes were made - lines may have already been fixed")
        return False
    
    # Write the fixed content back
    with open(engine_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ Successfully fixed verbose output in fire_simulation_engine.py")
    print("   - Replaced full array dumps with cell counts")
    print("   - This will dramatically reduce output volume")
    
    return True

def create_quick_config():
    """Create a quick configuration to reduce output."""
    
    config = {
        "engine_logging_interval": 1000,  # Log every 1000 steps instead of 100
        "verbose": False,
        "save_intermediate_results": False,
        "generate_plots": False,
        "console_output": False,
        "log_level": "WARNING"
    }
    
    config_file = "quiet_calibration_config.json"
    import json
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"✅ Created quiet config: {config_file}")
    return config_file

def show_usage():
    """Show how to use the fixes."""
    
    print("\n🎯 HOW TO USE THE FIXES:")
    print("=" * 40)
    print("1. The verbose output has been fixed in the engine")
    print("2. Use the quiet config for minimal output:")
    print(f"   python run_tenerife_calibration.py --config quiet_calibration_config.json")
    print("3. Or redirect output to a file:")
    print("   python run_tenerife_calibration.py > calibration.log 2>&1")
    print("4. To monitor progress, check the log file:")
    print("   tail -f calibration.log")

if __name__ == "__main__":
    print("🔧 FIXING VERBOSE CALIBRATION OUTPUT")
    print("=" * 50)
    
    # Fix the engine file
    if fix_verbose_output():
        print("\n✅ Engine file fixed successfully!")
    else:
        print("\n⚠️  Engine file may already be fixed or not found")
    
    # Create quiet config
    config_file = create_quick_config()
    
    # Show usage
    show_usage()
    
    print("\n🚀 You can now run calibration with much less output!")
