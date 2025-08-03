#!/usr/bin/env python3
"""
Validate Animation Configuration
Verifies that the 20-step animation configuration is ready for simulation.
"""

import json
import sys
from pathlib import Path

def validate_config():
    """Validate the animation configuration."""
    print("🧪 VALIDATING 20-STEP ANIMATION CONFIGURATION")
    print("=" * 60)
    
    # Load configuration
    config_file = Path("hpc_deployment/Forest_Fire_Simulation_animation_config.json")
    if not config_file.exists():
        print("❌ ERROR: Animation config file not found")
        return False
    
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
    except Exception as e:
        print(f"❌ ERROR: Failed to load config: {e}")
        return False
    
    print("✅ Configuration file loaded successfully")
    
    # Validate key settings
    print("\n📊 CONFIGURATION VALIDATION:")
    
    # Max steps
    max_steps = config.get('max_steps', 0)
    print(f"   Max steps: {max_steps}")
    if max_steps == 20:
        print("   ✅ PASS: Configured for 20 timesteps")
    else:
        print("   ❌ FAIL: Expected 20 timesteps")
        return False
    
    # Checkpoint interval
    checkpoint_interval = config.get('output', {}).get('checkpoint_interval', 0)
    print(f"   Checkpoint interval: {checkpoint_interval}")
    if checkpoint_interval == 1:
        print("   ✅ PASS: Every timestep will be checkpointed")
    else:
        print("   ❌ FAIL: Expected checkpoint interval of 1")
        return False
    
    # Save interval
    save_interval = config.get('save_interval', 0)
    print(f"   Save interval: {save_interval}")
    if save_interval == 1:
        print("   ✅ PASS: Data saved every timestep")
    else:
        print("   ❌ FAIL: Expected save interval of 1")
        return False
    
    # Animation settings
    animation_config = config.get('animation', {})
    if animation_config.get('enabled', False):
        print("   ✅ PASS: Animation features enabled")
    else:
        print("   ⚠️  WARNING: Animation features not explicitly enabled")
    
    # Ember settings
    ember_prob = config.get('ember_probability', 0)
    ember_dist = config.get('ember_distance', 0)
    ember_ign = config.get('ember_ignition', 0)
    print(f"   Ember probability: {ember_prob}")
    print(f"   Ember distance: {ember_dist}")
    print(f"   Ember ignition: {ember_ign}")
    
    if ember_prob > 0 and ember_dist > 0 and ember_ign > 0:
        print("   ✅ PASS: Ember dynamics configured")
    else:
        print("   ⚠️  WARNING: Ember dynamics may be disabled")
    
    # Grid size and layers
    grid_size = config.get('grid_size', [0, 0])
    num_layers = config.get('num_layers', 0)
    print(f"   Grid size: {grid_size[0]}×{grid_size[1]}")
    print(f"   Number of layers: {num_layers}")
    
    if grid_size[0] > 0 and grid_size[1] > 0:
        print("   ✅ PASS: Valid grid dimensions")
    else:
        print("   ❌ FAIL: Invalid grid dimensions")
        return False
    
    # Calculate expected outputs
    total_cells = grid_size[0] * grid_size[1] * num_layers
    expected_checkpoints = max_steps + 1  # Including initial state
    
    print("\n🎬 ANIMATION EXPECTATIONS:")
    print(f"   Total simulation cells: {total_cells:,}")
    print(f"   Expected checkpoint files: {expected_checkpoints}")
    print(f"   Animation frames: {max_steps}")
    print(f"   Frame resolution: Every timestep")
    
    # Storage requirements
    bytes_per_cell = config.get('bytes_per_cell', 30)
    checkpoint_size_mb = (total_cells * bytes_per_cell) / (1024 * 1024)
    total_storage_mb = checkpoint_size_mb * expected_checkpoints
    
    print(f"   Estimated checkpoint size: ~{checkpoint_size_mb:.1f} MB each")
    print(f"   Total storage requirement: ~{total_storage_mb:.1f} MB")
    
    # Output directory
    output_dir = config.get('output', {}).get('output_dir', 'N/A')
    print(f"   Output directory: {output_dir}")
    
    print("\n🚀 SIMULATION READINESS:")
    print("   ✅ Configuration validated")
    print("   ✅ 20 timesteps configured")
    print("   ✅ Every step will be checkpointed")
    print("   ✅ Ready for high-resolution animation")
    
    print("\n🎯 NEXT STEPS:")
    print("   1. Run simulation:")
    print("      python hpc_deployment/run_production_sim.py hpc_deployment/Forest_Fire_Simulation_animation_config.json")
    print("   2. Generate animation:")
    print("      python create_animation_generator.py <simulation_output_dir> --output fire_animation.mp4")
    
    return True

if __name__ == "__main__":
    success = validate_config()
    if success:
        print("\n🎉 CONFIGURATION VALIDATION: SUCCESS")
        print("🔥 Ready for 20-step simulation with frame-by-frame animation!")
    else:
        print("\n❌ CONFIGURATION VALIDATION: FAILED")
        print("Please fix the issues above before running the simulation.")
        sys.exit(1) 