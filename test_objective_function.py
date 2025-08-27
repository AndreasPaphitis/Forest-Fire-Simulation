#!/usr/bin/env python3
"""
Test script to understand the objective function issue.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import numpy as np
from src.core.calibration.objective_functions import (
    SpatialSimilarityObjective, 
    calculate_jaccard_index, 
    calculate_dice_coefficient
)

def test_scale_mismatch():
    """Test the scale mismatch issue."""
    print("🔍 Testing Objective Function Scale Mismatch")
    print("=" * 50)
    
    # Create a small simulated fire (like your current simulations)
    simulated_fire = np.zeros((609, 609))
    # Add a small fire around the ignition point (395, 377)
    for i in range(395-2, 395+3):
        for j in range(377-2, 377+3):
            if 0 <= i < 609 and 0 <= j < 609:
                simulated_fire[i, j] = 1
    
    simulated_burned_cells = np.sum(simulated_fire > 0)
    print(f"🔥 Simulated fire: {simulated_burned_cells} burned cells")
    
    # Create a realistic target fire (like EMSR data)
    target_fire = np.zeros((609, 609))
    # Add a larger fire area (realistic for EMSR data)
    for i in range(200, 400):
        for j in range(200, 400):
            if 0 <= i < 609 and 0 <= j < 609:
                target_fire[i, j] = 1
    
    target_burned_cells = np.sum(target_fire > 0)
    print(f"🎯 Target fire: {target_burned_cells} burned cells")
    
    # Calculate metrics
    jaccard = calculate_jaccard_index(simulated_fire, target_fire)
    dice = calculate_dice_coefficient(simulated_fire, target_fire)
    
    print(f"\n📊 Results:")
    print(f"   Jaccard Index: {jaccard:.6f}")
    print(f"   Dice Coefficient: {dice:.6f}")
    print(f"   Scale Ratio: {simulated_burned_cells / target_burned_cells:.6f}")
    
    # Test with no overlap
    no_overlap_sim = np.zeros((609, 609))
    no_overlap_sim[500, 500] = 1  # Fire in completely different location
    
    jaccard_no_overlap = calculate_jaccard_index(no_overlap_sim, target_fire)
    dice_no_overlap = calculate_dice_coefficient(no_overlap_sim, target_fire)
    
    print(f"\n📊 No Overlap Test:")
    print(f"   Jaccard Index: {jaccard_no_overlap:.6f}")
    print(f"   Dice Coefficient: {dice_no_overlap:.6f}")
    
    # Test with synthetic target (smaller scale)
    synthetic_target = np.zeros((609, 609))
    for i in range(390, 400):
        for j in range(370, 380):
            if 0 <= i < 609 and 0 <= j < 609:
                synthetic_target[i, j] = 1
    
    synthetic_burned_cells = np.sum(synthetic_target > 0)
    print(f"\n🎯 Synthetic target: {synthetic_burned_cells} burned cells")
    
    jaccard_synthetic = calculate_jaccard_index(simulated_fire, synthetic_target)
    dice_synthetic = calculate_dice_coefficient(simulated_fire, synthetic_target)
    
    print(f"📊 Synthetic Target Results:")
    print(f"   Jaccard Index: {jaccard_synthetic:.6f}")
    print(f"   Dice Coefficient: {dice_synthetic:.6f}")
    print(f"   Scale Ratio: {simulated_burned_cells / synthetic_burned_cells:.6f}")

def test_objective_function():
    """Test the full objective function."""
    print("\n🔍 Testing Full Objective Function")
    print("=" * 50)
    
    # Create objective function
    objective = SpatialSimilarityObjective(
        jaccard_weight=0.4,
        dice_weight=0.6
    )
    
    # Create simulation result (like what your calibration produces)
    simulated_fire = np.zeros((609, 609))
    for i in range(395-2, 395+3):
        for j in range(377-2, 377+3):
            if 0 <= i < 609 and 0 <= j < 609:
                simulated_fire[i, j] = 1
    
    simulation_result = {
        'fire_perimeter': simulated_fire,
        'stats': {
            'total_burned_cells': np.sum(simulated_fire > 0),
            'steps': 5
        }
    }
    
    # Create target data (like EMSR data)
    target_fire = np.zeros((609, 609))
    for i in range(200, 400):
        for j in range(200, 400):
            if 0 <= i < 609 and 0 <= j < 609:
                target_fire[i, j] = 1
    
    target_data = {
        'fire_perimeter': target_fire
    }
    
    # Evaluate objective function
    result = objective.evaluate(simulation_result, target_data)
    
    print(f"🔥 Simulation burned cells: {simulation_result['stats']['total_burned_cells']}")
    print(f"🎯 Target burned cells: {np.sum(target_fire > 0)}")
    print(f"📊 Objective value: {result.value:.6f}")
    print(f"📊 Is valid: {result.is_valid}")
    print(f"📊 Components: {result.components}")

if __name__ == "__main__":
    test_scale_mismatch()
    test_objective_function()
