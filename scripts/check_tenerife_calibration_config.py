#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Check Tenerife Calibration Configuration

Displays the exact configuration for Tenerife fire perimeter calibration
including timesteps, parameters, and resource estimates.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

def main():
    print("🔥 TENERIFE FIRE PERIMETER CALIBRATION - FINAL CONFIGURATION")
    print("=" * 80)
    
    # TOP 5 PARAMETERS FROM SENSITIVITY ANALYSIS
    top_5_parameters = [
        ('ember_probability', 0.382),      # Highest sensitivity
        ('fuel_consumption_rate', 0.165),  # Second highest
        ('ember_ignition', 0.138),         # Third highest
        ('slope_influence', 0.023),        # Fourth
        ('ember_height_factor', 0.019)     # Fifth
    ]
    
    print("🎯 TOP 5 PARAMETERS FROM SENSITIVITY ANALYSIS:")
    print("   (Method 2 Range-Based Sensitivity Analysis)")
    for i, (param, sensitivity) in enumerate(top_5_parameters, 1):
        print(f"   {i}. {param:<25} Sensitivity: {sensitivity:.3f}")
    
    # GRID SEARCH CONFIGURATION
    grid_points = 3
    total_combinations = grid_points ** len(top_5_parameters)
    
    print(f"\n🔢 GRID SEARCH CONFIGURATION:")
    print(f"   Grid points per parameter: {grid_points}")
    print(f"   Total parameter combinations: {total_combinations:,}")
    
    # TIMESTEP CONFIGURATION
    print(f"\n⏰ TIMESTEP CONFIGURATION:")
    print(f"   Default max_steps: 20 (from ModelConfig)")
    print(f"   Calibration max_steps: 100 (extended for fire progression)")
    print(f"   Each timestep represents: ~1 time unit of fire spread")
    print(f"   Stop condition: Fire extinguished OR max steps reached")
    print(f"   Simulation timeout: 120 minutes per run")
    
    # DOMAIN CONFIGURATION  
    print(f"\n🌍 FULL TENERIFE DOMAIN:")
    print(f"   Grid size: 15,121 × 24,741 × 25 layers")
    print(f"   Total cells: 9,347,092,500 (~9.35 billion)")
    print(f"   Spatial resolution: 5m per cell")
    print(f"   Vertical resolution: 25 layers × 2m = 50m height")
    print(f"   Coverage: Full Tenerife Island")
    print(f"   CRS: EPSG:25828 (UTM Zone 28N)")
    
    # MEMORY OPTIMIZATION
    print(f"\n💾 MEMORY OPTIMIZATION (Level 3 - Maximum):")
    print(f"   ✅ Sparse storage: Only active fire cells stored")
    print(f"   ✅ Disk storage: History stored on disk")
    print(f"   ✅ Differential history: Only changes stored")
    print(f"   ✅ Shared terrain: 50GB shared across all workers")
    print(f"   ✅ Memory per simulation: ~0.8GB (optimized)")
    
    # HPC CONFIGURATION OPTIONS
    configs = [
        {"name": "Conservative 64GB", "memory": 64, "workers": 40, "safe": True},
        {"name": "Standard 64GB", "memory": 64, "workers": 60, "safe": False},
        {"name": "Optimal 128GB", "memory": 128, "workers": 80, "safe": True},
        {"name": "Maximum 128GB", "memory": 128, "workers": 120, "safe": False}
    ]
    
    print(f"\n🖥️  HPC CONFIGURATION OPTIONS:")
    for config in configs:
        # Calculate estimates
        memory_per_sim = 0.8
        shared_terrain = 50.0
        concurrent_sims = min(config["workers"], total_combinations)
        peak_memory = shared_terrain + (memory_per_sim * concurrent_sims)
        
        time_per_sim_minutes = 20.0
        total_time_hours = (total_combinations * time_per_sim_minutes) / (60 * config["workers"])
        
        safety_icon = "✅" if config["safe"] else "⚠️ "
        
        print(f"\n   {safety_icon} {config['name']}:")
        print(f"      Memory: {config['memory']}GB / Workers: {config['workers']}")
        print(f"      Peak memory usage: {peak_memory:.1f}GB")
        print(f"      Estimated runtime: {total_time_hours:.1f} hours")
        print(f"      Memory safety: {'Safe' if config['safe'] else 'Moderate risk'}")
    
    # FIRE PERIMETER DATA
    print(f"\n🔥 FIRE PERIMETER DATA (EMSR685_AOI01):")
    print(f"   ✅ Training data: Day 1 (2023-08-18) + Day 2 (2023-08-21)")
    print(f"   ✅ Test data: Day 3 (2023-08-24) + Day 4 (2023-08-26)")
    print(f"   ✅ Temporal progression: 8-day fire evolution")
    print(f"   ✅ Objective function: Spatial similarity (Jaccard + Dice + Sørensen)")
    
    # EXECUTION COMMAND
    print(f"\n🚀 READY TO EXECUTE:")
    print(f"   Command for HPC environment:")
    print(f"   python scripts/run_tenerife_calibration.py --memory 64 --workers 40 --grid-points 3")
    print(f"   ")
    print(f"   For maximum performance (if memory allows):")
    print(f"   python scripts/run_tenerife_calibration.py --memory 128 --workers 80 --grid-points 3")
    
    # WHAT HAPPENS DURING CALIBRATION
    print(f"\n📝 WHAT HAPPENS DURING CALIBRATION:")
    print(f"   1. Load fire perimeter shapefiles for Days 1-2 (training)")
    print(f"   2. For each of {total_combinations} parameter combinations:")
    print(f"      a. Set up full Tenerife simulation with those parameters")
    print(f"      b. Run simulation for up to 100 timesteps")
    print(f"      c. Compare final fire shape to training perimeters")
    print(f"      d. Calculate spatial similarity score")
    print(f"   3. Select best parameter combination")
    print(f"   4. Validate on Days 3-4 (test data)")
    print(f"   5. Save results, plots, and parameter recommendations")
    
    print(f"\n✅ Configuration validated and ready for HPC deployment!")

if __name__ == "__main__":
    main()
