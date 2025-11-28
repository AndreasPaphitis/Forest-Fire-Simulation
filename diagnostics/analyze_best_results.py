#!/usr/bin/env python3

import json

# Load calibration results
with open('ultra_clean_calibration_20250910_005642_grid_search_results.json', 'r') as f:
    data = json.load(f)

results = data['results']
valid_results = [r for r in results if r.get('is_valid', True)]

# Sort by objective value (ascending = best first)
sorted_results = sorted(valid_results, key=lambda x: x['objective_value'])

print('🎯 TOP 10 BEST CALIBRATION RESULTS (LOWEST ERROR):')
print('=' * 70)
for i, result in enumerate(sorted_results[:10]):
    params = result['parameter_values']
    obj_val = result['objective_value']
    components = result.get('objective_components', {})
    dice_sim = components.get('dice_similarity', 'N/A')
    area_ratio = components.get('area_ratio', 'N/A')
    
    print(f'#{i+1}: Error = {obj_val:.4f}')
    print(f'   min_fuel = {params["min_fuel_value"]:.3f}')
    print(f'   spread_prob = {params["spread_probability"]:.3f}') 
    print(f'   fuel_consumption = {params["fuel_consumption_rate"]:.3f}')
    print(f'   ember_prob = {params["ember_probability"]:.3f}')
    if dice_sim != 'N/A':
        print(f'   dice_similarity = {dice_sim:.3f}')
    if area_ratio != 'N/A':
        print(f'   area_ratio = {area_ratio:.3f}')
    print()

print('\n🔥 ABSOLUTE BEST PARAMETERS:')
print('=' * 40)
best = sorted_results[0]
best_params = best['parameter_values']
print(f'min_fuel_value = {best_params["min_fuel_value"]}')
print(f'spread_probability = {best_params["spread_probability"]}')
print(f'fuel_consumption_rate = {best_params["fuel_consumption_rate"]}')
print(f'ember_probability = {best_params["ember_probability"]}')
print(f'Objective Error = {best["objective_value"]:.6f}')

# Also check worst for comparison
print('\n💥 WORST PARAMETERS (for comparison):')
print('=' * 40)
worst = sorted_results[-1]
worst_params = worst['parameter_values']
print(f'min_fuel_value = {worst_params["min_fuel_value"]}')
print(f'spread_probability = {worst_params["spread_probability"]}')
print(f'fuel_consumption_rate = {worst_params["fuel_consumption_rate"]}')
print(f'ember_probability = {worst_params["ember_probability"]}')
print(f'Objective Error = {worst["objective_value"]:.6f}')
