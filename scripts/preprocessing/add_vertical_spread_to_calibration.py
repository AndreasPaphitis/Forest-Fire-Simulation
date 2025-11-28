#!/usr/bin/env python3
"""
Simple script to show how to integrate vertical fire spread statistics 
into calibration results for your report
"""

def extract_vertical_spread_stats(forest_model):
    """
    Extract vertical fire spread statistics from a forest model
    for inclusion in calibration results
    """
    if not hasattr(forest_model, 'spread_stats') or not forest_model.spread_stats:
        return None
    
    stats = forest_model.spread_stats
    
    # Calculate key metrics
    total_spread = sum(stats.values())
    vertical_spread = stats.get('vertical_spread', 0)
    horizontal_spread = stats.get('horizontal_spread', 0)
    ember_spread = stats.get('ember_spread', 0)
    total_ignitions = stats.get('total_ignitions', 0)
    
    # Calculate percentages
    vertical_percentage = (vertical_spread / total_spread * 100) if total_spread > 0 else 0
    horizontal_percentage = (horizontal_spread / total_spread * 100) if total_spread > 0 else 0
    ember_percentage = (ember_spread / total_spread * 100) if total_spread > 0 else 0
    
    # Calculate efficiency
    vertical_efficiency = (vertical_spread / total_ignitions * 100) if total_ignitions > 0 else 0
    
    # Calculate ratio
    vertical_horizontal_ratio = vertical_spread / horizontal_spread if horizontal_spread > 0 else 0
    
    return {
        'total_spread_events': total_spread,
        'vertical_spread_events': vertical_spread,
        'vertical_spread_percentage': vertical_percentage,
        'horizontal_spread_events': horizontal_spread,
        'horizontal_spread_percentage': horizontal_percentage,
        'ember_spread_events': ember_spread,
        'ember_spread_percentage': ember_percentage,
        'total_ignitions': total_ignitions,
        'vertical_efficiency': vertical_efficiency,
        'vertical_horizontal_ratio': vertical_horizontal_ratio,
        'spread_classification': classify_vertical_spread(vertical_horizontal_ratio)
    }

def classify_vertical_spread(ratio):
    """Classify vertical spread behavior based on ratio"""
    if ratio > 0.1:
        return "High vertical spread - strong convection"
    elif ratio > 0.05:
        return "Moderate vertical spread - normal behavior"
    else:
        return "Low vertical spread - primarily horizontal"

def add_to_calibration_results(calibration_result, vertical_stats):
    """
    Add vertical spread statistics to calibration results
    """
    if vertical_stats:
        # Add to existing calibration result
        calibration_result['vertical_fire_spread'] = vertical_stats
        
        # Add summary metrics for easy reporting
        calibration_result['vertical_spread_summary'] = {
            'vertical_percentage': f"{vertical_stats['vertical_spread_percentage']:.1f}%",
            'vertical_efficiency': f"{vertical_stats['vertical_efficiency']:.1f}%",
            'classification': vertical_stats['spread_classification']
        }
    
    return calibration_result

# Example usage in your calibration workflow:
"""
# In your calibration script, after running a simulation:

# 1. Extract vertical spread stats
vertical_stats = extract_vertical_spread_stats(forest_model)

# 2. Add to your calibration results
calibration_result = {
    'objective_value': objective_value,
    'parameters': parameters,
    'simulation_time': simulation_time,
    # ... other existing results
}

# 3. Add vertical spread data
calibration_result = add_to_calibration_results(calibration_result, vertical_stats)

# 4. Save to your results file
import json
with open('calibration_results_with_vertical_spread.json', 'w') as f:
    json.dump(calibration_result, f, indent=2)
"""

# Example output format for your report:
example_output = {
    "calibration_run_1": {
        "objective_value": 0.123,
        "parameters": {"spread_probability": 0.8, "wind_speed": 5.0},
        "vertical_fire_spread": {
            "total_spread_events": 52339,
            "vertical_spread_events": 19900,
            "vertical_spread_percentage": 38.0,
            "vertical_efficiency": 97.9,
            "vertical_horizontal_ratio": 0.0,  # No horizontal spread in this test
            "spread_classification": "High vertical spread - strong convection"
        },
        "vertical_spread_summary": {
            "vertical_percentage": "38.0%",
            "vertical_efficiency": "97.9%",
            "classification": "High vertical spread - strong convection"
        }
    }
}

print("✅ Vertical fire spread integration ready!")
print("📊 Key metrics available for your report:")
print("   - Vertical spread percentage")
print("   - Vertical spread efficiency") 
print("   - Spread classification")
print("   - Vertical/Horizontal ratio")
print("   - Total spread events breakdown")

if __name__ == "__main__":
    print("This script shows how to integrate vertical fire spread stats into your calibration results.")
    print("Copy the functions above into your calibration workflow to include vertical spread analysis.")
