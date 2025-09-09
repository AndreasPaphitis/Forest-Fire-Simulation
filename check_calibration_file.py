#!/usr/bin/env python3

import json
from datetime import datetime

print('🔍 CHECKING CALIBRATION FILE STRUCTURE AND METADATA...')
print('=' * 60)

with open('ultra_clean_calibration_20250910_005642_grid_search_results.json', 'r') as f:
    data = json.load(f)

# Check basic metadata
print(f'📊 CALIBRATION OVERVIEW:')
print(f'Total evaluations: {data.get("total_evaluations", "N/A")}')
print(f'Successful evaluations: {data.get("successful_evaluations", "N/A")}')
print(f'Parameter space: {list(data.get("parameter_space", {}).keys())}')

# Check convergence info for timing
conv = data.get('convergence_info', {})
total_time = conv.get('total_time', 0)
print(f'Total time: {total_time:.1f} seconds ({total_time/60:.1f} minutes)')
print(f'Success rate: {conv.get("success_rate", "N/A")}')

# Extract timestamp from filename
filename_timestamp = '20250910_005642'  # From filename
try:
    dt = datetime.strptime(filename_timestamp, '%Y%m%d_%H%M%S')
    print(f'📅 Calibration ran on: {dt.strftime("%Y-%m-%d at %H:%M:%S")}')
except:
    print(f'📅 Timestamp: {filename_timestamp}')

print(f'\n🎯 PARAMETER RANGES:')
param_space = data.get('parameter_space', {})
for param, values in param_space.items():
    print(f'   {param}: {min(values):.3f} to {max(values):.3f} ({len(values)} values)')

print(f'\n🔍 SAMPLE RESULTS (first 5):')
results = data.get('results', [])
for i, result in enumerate(results[:5]):
    obj_val = result.get('objective_value', 'N/A')
    is_valid = result.get('is_valid', 'N/A')
    params = result.get('parameter_values', {})
    print(f'#{i+1}: obj_val = {obj_val}, valid = {is_valid}')
    if params:
        print(f'    params: {params}')

print(f'\n🎯 CHECKING FOR BEST AND WORST:')
valid_results = [r for r in results if r.get('is_valid', True)]
if valid_results:
    sorted_results = sorted(valid_results, key=lambda x: x['objective_value'])
    
    best = sorted_results[0]
    worst = sorted_results[-1]
    
    print(f'✅ BEST (lowest error): {best["objective_value"]:.6f}')
    print(f'   Params: {best["parameter_values"]}')
    
    print(f'❌ WORST (highest error): {worst["objective_value"]:.6f}')
    print(f'   Params: {worst["parameter_values"]}')
    
    # Check the range
    print(f'\n📈 ERROR RANGE: {best["objective_value"]:.6f} to {worst["objective_value"]:.6f}')
else:
    print('❌ No valid results found!')
