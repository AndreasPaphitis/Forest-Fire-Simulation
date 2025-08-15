#!/usr/bin/env python3
"""
Immediate Memory Fix for Forest Fire Simulation OOM Issues

This script provides immediate fixes for the memory issues causing OOM kills.
Uses only standard library modules to avoid dependency issues.
"""

import gc
import os
import sys
import glob
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def immediate_memory_cleanup():
    """Perform immediate memory cleanup."""
    print("🚨 IMMEDIATE MEMORY CLEANUP - Forest Fire Simulation OOM Fix")
    print("=" * 60)
    
    # 1. Force garbage collection
    print("🗑️  Performing garbage collection...")
    collected = 0
    for i in range(5):  # Multiple passes
        current_collected = gc.collect()
        collected += current_collected
        if current_collected == 0:
            break
    print(f"   Freed {collected} objects")
    
    # 2. Clean up shared memory (Linux/Unix systems)
    shared_memory_cleaned = 0
    if os.path.exists("/dev/shm"):
        print("🧹 Cleaning shared memory leaks...")
        patterns = ["/dev/shm/psm_*", "/dev/shm/wnsm_*"]
        for pattern in patterns:
            leaked_blocks = glob.glob(pattern)
            for block_path in leaked_blocks:
                try:
                    os.remove(block_path)
                    shared_memory_cleaned += 1
                    print(f"   Removed: {os.path.basename(block_path)}")
                except Exception as e:
                    print(f"   Could not remove {block_path}: {e}")
    
    if shared_memory_cleaned > 0:
        print(f"✅ Cleaned {shared_memory_cleaned} shared memory blocks")
    else:
        print("ℹ️  No shared memory blocks found to clean")
    
    # 3. Memory release (Linux systems)
    try:
        import ctypes
        libc = ctypes.CDLL("libc.so.6")
        libc.malloc_trim(0)
        print("✅ Released memory back to OS")
    except:
        print("ℹ️  Memory trim not available (non-Linux system)")
    
    return collected, shared_memory_cleaned

def print_memory_optimization_guide():
    """Print immediate optimization recommendations."""
    print("\n💡 IMMEDIATE RECOMMENDATIONS TO PREVENT OOM:")
    print("=" * 50)
    
    print("\n1. 🎯 REDUCE GRID SIZE (Most Important)")
    print("   Current: 15121 x 24741 = 374M cells")
    print("   Try: 2000 x 2000 = 4M cells (100x smaller)")
    print("   Or: 5000 x 5000 = 25M cells (15x smaller)")
    
    print("\n2. 🔧 USE MEMORY-SAFE CONFIG")
    print("   cp hpc_deployment/memory_safe_config.json your_config.json")
    print("   Edit your config to use smaller grid_size")
    
    print("\n3. 🚫 DISABLE SHARED MEMORY TEMPORARILY")
    print("   Set 'use_shared_terrain': false in config")
    print("   This prevents memory copying overhead")
    
    print("\n4. ⚡ ENABLE MAXIMUM SPARSE OPTIMIZATION")
    print("   Set 'memory_optimization_level': 2")
    print("   Set 'use_sparse_storage': true")
    
    print("\n5. 🎬 DISABLE UNNECESSARY FEATURES")
    print("   Set 'create_animations': false")
    print("   Set 'store_full_states': false")
    print("   Set 'save_terrain_data': false")
    
    print("\n6. 📊 MONITOR MEMORY USAGE")
    print("   Use: htop")
    print("   Or: watch -n 1 'free -h'")
    print("   Or: ps aux --sort=-%mem | head")

def create_emergency_config():
    """Create an emergency small-scale configuration."""
    config_content = """{
  "simulation_name": "emergency_small_test",
  "description": "Emergency small-scale test to prevent OOM",
  
  "grid_configuration": {
    "grid_size": [1000, 1000],
    "num_layers": 10,
    "layer_height_meters": 2.0,
    "model_resolution": 10.0
  },
  
  "memory_optimization": {
    "memory_optimization_level": 2,
    "use_sparse_storage": true,
    "use_shared_terrain": false,
    "max_memory_gb": 16
  },
  
  "terrain_configuration": {
    "use_preprocessed_terrain": false,
    "generate_flat_terrain": true
  },
  
  "simulation_parameters": {
    "max_timesteps": 100,
    "timestep_minutes": 1.0,
    "save_interval": 20,
    "store_full_states": false
  },
  
  "fire_parameters": {
    "spread_rate": 0.3,
    "wind_speed_ms": 3.0,
    "wind_direction_degrees": 0.0,
    "moisture_content": 0.2,
    "initial_fuel_load": 1.0
  },
  
  "output_configuration": {
    "output_dir": "emergency_test_output",
    "export_formats": ["pickle"],
    "create_animations": false,
    "save_terrain_data": false
  }
}"""
    
    emergency_config_path = "hpc_deployment/emergency_small_test.json"
    try:
        with open(emergency_config_path, 'w') as f:
            f.write(config_content)
        print(f"\n✅ Created emergency config: {emergency_config_path}")
        print("   Use this for immediate testing without OOM risk")
    except Exception as e:
        print(f"❌ Could not create emergency config: {e}")

def check_current_memory_issues():
    """Check for current memory-related issues."""
    print("\n🔍 CHECKING CURRENT ISSUES:")
    print("-" * 30)
    
    # Check for large .npy files that might be loaded
    preprocessed_dir = Path("preprocessed_terrain")
    if preprocessed_dir.exists():
        print("📁 Preprocessed terrain files found:")
        total_size_gb = 0
        for npy_file in preprocessed_dir.glob("*.npy"):
            size_mb = npy_file.stat().st_size / (1024**2)
            total_size_gb += size_mb / 1024
            print(f"   {npy_file.name}: {size_mb:.1f} MB")
        print(f"   Total terrain data: {total_size_gb:.2f} GB")
        
        if total_size_gb > 10:
            print("⚠️  Large terrain files detected!")
            print("   Consider using smaller domain or memory mapping")
    
    # Check for shared memory
    if os.path.exists("/dev/shm"):
        shm_files = list(Path("/dev/shm").glob("psm_*"))
        if shm_files:
            print(f"🧠 Found {len(shm_files)} shared memory blocks")
            total_shm_mb = sum(f.stat().st_size for f in shm_files) / (1024**2)
            print(f"   Total shared memory: {total_shm_mb:.1f} MB")

def main():
    """Main function."""
    print("🚨 Forest Fire Simulation - Emergency Memory Fix")
    print("This script addresses the OOM kill issue you experienced")
    print()
    
    # Immediate cleanup
    collected, cleaned = immediate_memory_cleanup()
    
    # Check current issues
    check_current_memory_issues()
    
    # Provide guidance
    print_memory_optimization_guide()
    
    # Create emergency config
    create_emergency_config()
    
    print("\n" + "=" * 60)
    print("🎯 NEXT STEPS:")
    print("1. Use the emergency config for testing: emergency_small_test.json")
    print("2. Gradually increase grid size once small version works")
    print("3. Monitor memory usage during runs")
    print("4. Apply the memory fixes we created to your main config")
    print("\n✅ Emergency memory fixes completed!")

if __name__ == "__main__":
    main()
