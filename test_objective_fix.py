#!/usr/bin/env python3

"""
DEMONSTRATION: Why your calibration found extreme parameters

This shows the difference between:
1. ORIGINAL: Maximize similarity (found spread_probability=0.95)
2. CORRECTED: Minimize spatial error (will find realistic parameters)
"""

import numpy as np

def calculate_jaccard_index(predicted, actual):
    """Jaccard similarity = intersection / union"""
    pred_bool = predicted.astype(bool)
    actual_bool = actual.astype(bool)
    
    intersection = np.logical_and(pred_bool, actual_bool).sum()
    union = np.logical_or(pred_bool, actual_bool).sum()
    
    if union == 0:
        return 1.0 if intersection == 0 else 0.0
    
    return float(intersection) / float(union)

def calculate_dice_coefficient(predicted, actual):
    """Dice coefficient = 2 * intersection / (|A| + |B|)"""
    pred_bool = predicted.astype(bool)
    actual_bool = actual.astype(bool)
    
    intersection = np.logical_and(pred_bool, actual_bool).sum()
    pred_sum = pred_bool.sum()
    actual_sum = actual_bool.sum()
    
    if pred_sum + actual_sum == 0:
        return 1.0 if intersection == 0 else 0.0
    
    return 2.0 * float(intersection) / float(pred_sum + actual_sum)

def original_objective(predicted, target):
    """ORIGINAL: Maximize weighted similarity (BROKEN!)"""
    jaccard = calculate_jaccard_index(predicted, target)
    dice = calculate_dice_coefficient(predicted, target)
    
    # Your original weights
    similarity = 0.4 * jaccard + 0.6 * dice
    
    return similarity  # HIGHER IS BETTER = PROBLEM!

def corrected_objective(predicted, target):
    """CORRECTED: Minimize spatial error (FIXED!)"""
    jaccard = calculate_jaccard_index(predicted, target)
    dice = calculate_dice_coefficient(predicted, target)
    
    # Convert to ERROR (1 - similarity)
    jaccard_error = 1.0 - jaccard
    dice_error = 1.0 - dice
    
    # Same weights, but now ERROR-based
    spatial_error = 0.4 * jaccard_error + 0.6 * dice_error
    
    # Add over-prediction penalty
    predicted_area = np.sum(predicted > 0)
    target_area = np.sum(target > 0)
    area_ratio = predicted_area / max(target_area, 1)
    
    overprediction_penalty = 0.0
    if area_ratio > 2.0:
        overprediction_penalty = 2.0 * (area_ratio - 2.0) ** 2
    
    total_error = spatial_error + overprediction_penalty
    
    return total_error  # LOWER IS BETTER = CORRECT!

def main():
    print("🚨 CALIBRATION OBJECTIVE FUNCTION ANALYSIS")
    print("=" * 60)
    
    # Create target fire (small realistic fire)
    target = np.zeros((100, 100))
    target[40:60, 40:60] = 1  # 20x20 = 400 cells
    target_area = np.sum(target)
    
    print(f"Target fire: {target_area} cells (realistic size)")
    print()
    
    # Test different simulation outcomes
    scenarios = [
        ("Perfect Match", target.copy()),
        ("Slight Over-prediction", np.zeros((100, 100))),
        ("Your Calibration Result", np.ones((100, 100)))  # Entire domain!
    ]
    
    # Slight over-prediction
    scenarios[1] = ("Slight Over-prediction", np.zeros((100, 100)))
    scenarios[1][1][35:65, 35:65] = 1  # 30x30 = 900 cells
    
    print("SCENARIO COMPARISON:")
    print("-" * 60)
    
    for name, predicted in scenarios:
        pred_area = np.sum(predicted)
        area_ratio = pred_area / target_area
        
        original_score = original_objective(predicted, target)
        corrected_score = corrected_objective(predicted, target)
        
        print(f"{name}:")
        print(f"  Predicted area: {pred_area:,} cells ({area_ratio:.1f}x target)")
        print(f"  ORIGINAL objective: {original_score:.4f} (higher = better)")
        print(f"  CORRECTED objective: {corrected_score:.4f} (lower = better)")
        print()
    
    print("🔍 ANALYSIS:")
    print("- ORIGINAL: Your massive over-prediction got 0.05 similarity")
    print("- GRID SEARCH: Found this was 'best available' with extreme parameters")
    print("- CORRECTED: Massive over-prediction gets high error (bad!)")
    print("- RESULT: Grid search would now find realistic parameters")
    
    print()
    print("💡 THE FIX:")
    print("1. Use BOTH Jaccard AND Dice (same as before)")
    print("2. Convert to ERROR: error = 1 - similarity")  
    print("3. Add over-prediction penalty")
    print("4. Set higher_is_better = False")
    print("5. Grid search finds parameters that MINIMIZE error")

if __name__ == "__main__":
    main()
