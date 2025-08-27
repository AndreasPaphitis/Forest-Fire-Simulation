#!/usr/bin/env python3
"""
Target Data Loading Diagnostic Script

This script diagnoses the critical issue where objective values are consistently 0.00000000
due to EMSR fire perimeter data not being loaded into target_data.

Phase 1: Target Data Loading Verification
Phase 2: Objective Function Debugging  
Phase 3: Memory and Performance Optimization
"""

import sys
import os
import numpy as np
from pathlib import Path
import logging

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.core.calibration.fire_perimeter_calibration import (
    FirePerimeterDiscovery, 
    TenerifeFirePerimeterCalibrator,
    FirePerimeterDataset
)
from src.core.calibration.calibration_config import CalibrationConfig, CalibrationTarget
from src.core.calibration.objective_functions import SpatialSimilarityObjective
from src.config.config_tools import ModelConfig

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def phase1_target_data_loading_verification():
    """Phase 1: Verify EMSR data access and target data preparation."""
    print("🔍 PHASE 1: TARGET DATA LOADING VERIFICATION")
    print("=" * 60)
    
    # Step 1: Check EMSR directory structure
    print("\n📁 Step 1: EMSR Directory Structure Check")
    emsr_dir = Path("EMSR Delineations")
    if not emsr_dir.exists():
        print(f"❌ EMSR directory not found: {emsr_dir}")
        return False
    
    print(f"✅ EMSR directory found: {emsr_dir}")
    
    # List day directories
    day_dirs = list(emsr_dir.glob("Day *"))
    print(f"📅 Found {len(day_dirs)} day directories:")
    for day_dir in day_dirs:
        print(f"   - {day_dir.name}")
        
        # Check for shapefiles
        shapefiles = list(day_dir.glob("*.shp"))
        json_files = list(day_dir.glob("*.json"))
        print(f"     Shapefiles: {len(shapefiles)}")
        print(f"     JSON files: {len(json_files)}")
        
        if shapefiles:
            print(f"     ✅ Primary shapefile: {shapefiles[0].name}")
        elif json_files:
            print(f"     ✅ Primary JSON file: {json_files[0].name}")
        else:
            print(f"     ❌ No fire perimeter files found")
    
    # Step 2: Test FirePerimeterDiscovery
    print("\n🔍 Step 2: Fire Perimeter Discovery Test")
    try:
        discovery = FirePerimeterDiscovery()
        dataset = discovery.discover_fire_perimeters()
        
        print(f"✅ Discovery successful: {len(dataset.fire_perimeters)} fire perimeters found")
        
        for i, fp in enumerate(dataset.fire_perimeters[:3]):  # Show first 3
            print(f"   {i+1}. {fp.fire_id} - Day {fp.day_number} ({fp.date})")
            print(f"      Area: {fp.area_hectares:.1f} ha" if fp.area_hectares else "      Area: Unknown")
            print(f"      Valid: {fp.is_valid}")
            if not fp.is_valid:
                print(f"      Error: {fp.error_message}")
        
        return dataset
        
    except Exception as e:
        print(f"❌ Discovery failed: {e}")
        import traceback
        traceback.print_exc()
        return None

def phase2_objective_function_debugging(dataset):
    """Phase 2: Debug objective function target data reception."""
    print("\n🔍 PHASE 2: OBJECTIVE FUNCTION DEBUGGING")
    print("=" * 60)
    
    if not dataset or not dataset.fire_perimeters:
        print("❌ No valid dataset for objective function testing")
        return False
    
    # Step 1: Create calibration targets
    print("\n🎯 Step 1: Calibration Target Creation")
    calibration_targets = []
    
    for i, fire_perimeter in enumerate(dataset.fire_perimeters[:2]):  # Use first 2
        if fire_perimeter.is_valid and fire_perimeter.shapefile_path:
            target = CalibrationTarget(
                fire_perimeter_path=str(fire_perimeter.shapefile_path),
                weight=1.0
            )
            calibration_targets.append(target)
            print(f"✅ Created target {i+1}: {Path(fire_perimeter.shapefile_path).name}")
    
    if not calibration_targets:
        print("❌ No valid calibration targets created")
        return False
    
    # Step 2: Test target data preparation
    print("\n🔄 Step 2: Target Data Preparation Test")
    try:
        calibrator = TenerifeFirePerimeterCalibrator()
        
        # Test with different grid sizes
        test_grid_sizes = [(609, 609), (1000, 1000), None]
        
        for grid_size in test_grid_sizes:
            print(f"\n   Testing grid size: {grid_size}")
            
            target_data = calibrator._prepare_target_data(calibration_targets, grid_size=grid_size)
            
            if target_data and 'fire_perimeter' in target_data:
                fire_perim = target_data['fire_perimeter']
                print(f"   ✅ Target data created successfully")
                print(f"      Fire perimeter type: {type(fire_perim)}")
                
                if hasattr(fire_perim, 'shape'):
                    print(f"      Fire perimeter shape: {fire_perim.shape}")
                elif hasattr(fire_perim, 'toarray'):
                    dense_shape = fire_perim.toarray().shape
                    print(f"      Fire perimeter shape (dense): {dense_shape}")
                
                # Check if it's sparse
                if hasattr(fire_perim, 'nnz'):
                    print(f"      Sparse matrix: {fire_perim.nnz} non-zero elements")
                
                # Count fire cells
                if hasattr(fire_perim, 'toarray'):
                    fire_cells = np.sum(fire_perim.toarray() > 0)
                else:
                    fire_cells = np.sum(fire_perim > 0)
                print(f"      Fire cells: {fire_cells:,}")
                
                return target_data
            else:
                print(f"   ❌ Target data preparation failed")
                print(f"      Target data keys: {list(target_data.keys()) if target_data else 'None'}")
        
        return None
        
    except Exception as e:
        print(f"❌ Target data preparation failed: {e}")
        import traceback
        traceback.print_exc()
        return None

def phase3_scale_mismatch_analysis(target_data):
    """Phase 3: Analyze scale mismatch between simulation and target."""
    print("\n🔍 PHASE 3: SCALE MISMATCH ANALYSIS")
    print("=" * 60)
    
    if not target_data or 'fire_perimeter' not in target_data:
        print("❌ No valid target data for scale analysis")
        return False
    
    # Step 1: Create synthetic simulation result
    print("\n🔥 Step 1: Simulation Result Creation")
    
    # Create a realistic simulation result (like your current simulations)
    simulated_fire = np.zeros((609, 609))
    
    # Add a large fire area (simulating 20K-118K burned cells)
    # This represents what your simulations are actually producing
    for i in range(200, 500):  # Large fire area
        for j in range(200, 500):
            if 0 <= i < 609 and 0 <= j < 609:
                simulated_fire[i, j] = 1
    
    simulated_burned_cells = np.sum(simulated_fire > 0)
    print(f"🔥 Simulated fire: {simulated_burned_cells:,} burned cells")
    
    # Step 2: Extract target data
    print("\n🎯 Step 2: Target Data Extraction")
    target_fire = target_data['fire_perimeter']
    
    # Convert to dense if sparse
    if hasattr(target_fire, 'toarray'):
        target_fire = target_fire.toarray()
        print(f"✅ Converted sparse target to dense")
    
    target_burned_cells = np.sum(target_fire > 0)
    print(f"🎯 Target fire: {target_burned_cells:,} burned cells")
    print(f"🎯 Target shape: {target_fire.shape}")
    
    # Step 3: Test objective function
    print("\n📊 Step 3: Objective Function Evaluation")
    
    # Create simulation result
    simulation_result = {
        'forest_model': type('MockForestModel', (), {
            'state': simulated_fire,
            'grid_size': (609, 609)
        })(),
        'stats': {
            'total_burned_cells': simulated_burned_cells,
            'steps': 10
        }
    }
    
    # Create target data
    target_data_for_objective = {
        'fire_perimeter': target_fire
    }
    
    # Test objective function
    objective = SpatialSimilarityObjective()
    result = objective.evaluate(simulation_result, target_data_for_objective)
    
    print(f"📊 Objective evaluation results:")
    print(f"   Objective value: {result.value:.8f}")
    print(f"   Is valid: {result.is_valid}")
    
    if result.components:
        print(f"   Components:")
        for key, value in result.components.items():
            if isinstance(value, float):
                print(f"     {key}: {value:.6f}")
            else:
                print(f"     {key}: {value}")
    
    # Step 4: Test with synthetic target fallback
    print("\n🔄 Step 4: Synthetic Target Fallback Test")
    
    # Test with no target data (should trigger synthetic target)
    result_synthetic = objective.evaluate(simulation_result, None)
    
    print(f"📊 Synthetic target results:")
    print(f"   Objective value: {result_synthetic.value:.8f}")
    print(f"   Is valid: {result_synthetic.is_valid}")
    
    if result_synthetic.components:
        print(f"   Components:")
        for key, value in result_synthetic.components.items():
            if isinstance(value, float):
                print(f"     {key}: {value:.6f}")
            else:
                print(f"     {key}: {value}")
    
    return result.value > 0.0

def main():
    """Main diagnostic function."""
    print("🚨 TARGET DATA LOADING DIAGNOSTIC")
    print("=" * 80)
    print("This script diagnoses the critical issue where objective values are 0.00000000")
    print("due to EMSR fire perimeter data not being loaded into target_data.")
    print()
    
    # Phase 1: Target Data Loading Verification
    dataset = phase1_target_data_loading_verification()
    if not dataset:
        print("\n❌ PHASE 1 FAILED: Cannot proceed without valid dataset")
        return False
    
    # Phase 2: Objective Function Debugging
    target_data = phase2_objective_function_debugging(dataset)
    if not target_data:
        print("\n❌ PHASE 2 FAILED: Cannot proceed without valid target data")
        return False
    
    # Phase 3: Scale Mismatch Analysis
    success = phase3_scale_mismatch_analysis(target_data)
    
    # Summary
    print("\n" + "=" * 80)
    print("🎯 DIAGNOSTIC SUMMARY")
    print("=" * 80)
    
    if success:
        print("✅ DIAGNOSTIC COMPLETED SUCCESSFULLY")
        print("   - EMSR data loading: WORKING")
        print("   - Target data preparation: WORKING") 
        print("   - Objective function: WORKING")
        print("   - Scale compatibility: WORKING")
        print("\n💡 RECOMMENDATION: The issue may be in the calibration workflow")
        print("   Check the calibration script for proper target data passing")
    else:
        print("❌ DIAGNOSTIC IDENTIFIED ISSUES")
        print("   - Check the specific failure points above")
        print("   - Verify EMSR data format and accessibility")
        print("   - Ensure spatial libraries are properly installed")
    
    return success

if __name__ == "__main__":
    main()
