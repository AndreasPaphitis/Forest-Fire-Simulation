#!/usr/bin/env python3

"""
ANALYSIS: Dice vs Jaccard vs Combined for Calibration

This tests whether using Dice coefficient alone would be better than 
the combined Jaccard + Dice approach for finding realistic parameters.
"""

import numpy as np

def calculate_jaccard_index(predicted, actual):
    """Jaccard = intersection / union (more conservative)"""
    pred_bool = predicted.astype(bool)
    actual_bool = actual.astype(bool)
    
    intersection = np.logical_and(pred_bool, actual_bool).sum()
    union = np.logical_or(pred_bool, actual_bool).sum()
    
    if union == 0:
        return 1.0 if intersection == 0 else 0.0
    
    return float(intersection) / float(union)

def calculate_dice_coefficient(predicted, actual):
    """Dice = 2 * intersection / (|A| + |B|) (less conservative)"""
    pred_bool = predicted.astype(bool)
    actual_bool = actual.astype(bool)
    
    intersection = np.logical_and(pred_bool, actual_bool).sum()
    pred_sum = pred_bool.sum()
    actual_sum = actual_bool.sum()
    
    if pred_sum + actual_sum == 0:
        return 1.0 if intersection == 0 else 0.0
    
    return 2.0 * float(intersection) / float(pred_sum + actual_sum)

def jaccard_only_error(predicted, target):
    """Objective using only Jaccard error"""
    jaccard = calculate_jaccard_index(predicted, target)
    return 1.0 - jaccard

def dice_only_error(predicted, target):
    """Objective using only Dice error"""
    dice = calculate_dice_coefficient(predicted, target)
    return 1.0 - dice

def combined_error(predicted, target):
    """Objective using weighted Jaccard + Dice (current approach)"""
    jaccard = calculate_jaccard_index(predicted, target)
    dice = calculate_dice_coefficient(predicted, target)
    
    jaccard_error = 1.0 - jaccard
    dice_error = 1.0 - dice
    
    # Current weights: 40% Jaccard, 60% Dice
    return 0.4 * jaccard_error + 0.6 * dice_error

def main():
    print("🧪 DICE vs JACCARD vs COMBINED FOR CALIBRATION")
    print("=" * 60)
    
    # Create target fire (realistic size)
    target = np.zeros((100, 100))
    target[40:60, 40:60] = 1  # 20x20 = 400 cells
    target_area = np.sum(target)
    
    print(f"Target fire: {target_area} cells")
    print()
    
    # Test different scenarios
    scenarios = [
        ("Perfect Match", target.copy()),
        ("Slight Over-prediction (1.5x)", np.zeros((100, 100))),
        ("Moderate Over-prediction (2.5x)", np.zeros((100, 100))),
        ("Your Calibration Bug (25x)", np.ones((100, 100)))
    ]
    
    # Create over-prediction scenarios
    scenarios[1] = ("Slight Over-prediction (1.5x)", np.zeros((100, 100)))
    scenarios[1][1][38:62, 38:62] = 1  # 24x24 = 576 cells (1.44x)
    
    scenarios[2] = ("Moderate Over-prediction (2.5x)", np.zeros((100, 100)))
    scenarios[2][1][35:65, 35:65] = 1  # 30x30 = 900 cells (2.25x)
    
    print("SPATIAL ERROR COMPARISON:")
    print("-" * 60)
    print(f"{'Scenario':<25} {'Jaccard':<10} {'Dice':<10} {'Combined':<10} {'Best Choice'}")
    print("-" * 60)
    
    results = []
    
    for name, predicted in scenarios:
        pred_area = np.sum(predicted)
        area_ratio = pred_area / target_area
        
        jaccard_err = jaccard_only_error(predicted, target)
        dice_err = dice_only_error(predicted, target)
        combined_err = combined_error(predicted, target)
        
        # Which method gives the best discrimination?
        errors = [jaccard_err, dice_err, combined_err]
        method_names = ['Jaccard', 'Dice', 'Combined']
        best_method = method_names[np.argmin(errors)]
        
        results.append((name, area_ratio, jaccard_err, dice_err, combined_err, best_method))
        
        print(f"{name:<25} {jaccard_err:<10.4f} {dice_err:<10.4f} {combined_err:<10.4f} {best_method}")
    
    print()
    print("🔍 ANALYSIS FOR CALIBRATION:")
    print("-" * 60)
    
    # Calculate error ranges and discrimination
    perfect_errors = [results[0][2], results[0][3], results[0][4]]  # Perfect match errors
    bug_errors = [results[-1][2], results[-1][3], results[-1][4]]   # Bug simulation errors
    
    # Range = difference between perfect and worst case
    jaccard_range = bug_errors[0] - perfect_errors[0]
    dice_range = bug_errors[1] - perfect_errors[1]
    combined_range = bug_errors[2] - perfect_errors[2]
    
    print(f"Error Range (discrimination power):")
    print(f"  Jaccard only:  {jaccard_range:.4f}")
    print(f"  Dice only:     {dice_range:.4f}")
    print(f"  Combined:      {combined_range:.4f}")
    print()
    
    # Check which is most sensitive to over-prediction
    slight_over = results[1]  # 1.5x over-prediction
    print(f"Sensitivity to slight over-prediction (1.5x area):")
    print(f"  Jaccard error:  {slight_over[2]:.4f}")
    print(f"  Dice error:     {slight_over[3]:.4f}")
    print(f"  Combined error: {slight_over[4]:.4f}")
    print()
    
    # Recommendation
    print("🎯 CALIBRATION RECOMMENDATION:")
    print("=" * 60)
    
    if dice_range > jaccard_range and dice_range > combined_range:
        print("✅ RECOMMENDATION: Use DICE COEFFICIENT ONLY")
        print("   Reasons:")
        print("   - Highest discrimination between good and bad parameters")
        print("   - Simpler objective function (fewer local minima)")
        print("   - More stable optimization landscape")
        print("   - Less prone to finding extreme parameter values")
    elif jaccard_range > dice_range and jaccard_range > combined_range:
        print("✅ RECOMMENDATION: Use JACCARD INDEX ONLY") 
        print("   Reasons:")
        print("   - Most conservative (heavily penalizes over-prediction)")
        print("   - Highest discrimination power")
        print("   - Best for preventing over-prediction issues")
    else:
        print("✅ RECOMMENDATION: Keep COMBINED APPROACH")
        print("   Reasons:")
        print("   - Balanced approach")
        print("   - Leverages strengths of both metrics")
        print("   - Good compromise between sensitivity and stability")
    
    print()
    print("📊 PRACTICAL IMPLICATIONS:")
    print("-" * 60)
    print("For your specific over-prediction problem:")
    
    if dice_range > jaccard_range:
        print("🔹 Dice coefficient alone might find realistic parameters faster")
        print("🔹 Less likely to get stuck in extreme parameter regions")  
        print("🔹 More forgiving of slight over-prediction during search")
        print("🔹 Simpler to interpret and debug")
    else:
        print("🔹 Jaccard index alone might be too conservative")
        print("🔹 Combined approach balances sensitivity and stability")
    
    print()
    print("🚀 QUICK IMPLEMENTATION:")
    print("To switch to Dice-only, change this line in objective_functions_corrected.py:")
    print("   dice_weight=1.0, jaccard_weight=0.0")

if __name__ == "__main__":
    main()
