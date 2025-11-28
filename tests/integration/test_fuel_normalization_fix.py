#!/usr/bin/env python3

import numpy as np

print('🔥 TESTING FUEL NORMALIZATION FIX')
print('=' * 50)

# Load sample preprocessed LiDAR data
layer_1 = np.load('preprocessed_lidar/layer_01.npy')

print(f'📊 Sample PAD values from Layer 1:')
sample_indices = [(100, 100), (200, 200), (300, 300), (400, 400)]

for x, y in sample_indices:
    if x < layer_1.shape[0] and y < layer_1.shape[1]:
        pad_value = layer_1[x, y]
        
        # OLD: Legacy normalization with initial_fuel_load=8.0
        fuel_factor_old = min(1.0, pad_value / 8.0)
        
        # NEW: PAD normalization with initial_fuel_load=1.0
        # This triggers: if max_fuel <= 1.0 and current_fuel <= 1.0: fuel_factor = current_fuel
        # Or if current_fuel > 1.0: fuel_factor = min(current_fuel, 1.0)
        fuel_factor_new = min(pad_value, 1.0)
        
        improvement = fuel_factor_new / fuel_factor_old if fuel_factor_old > 0 else float('inf')
        
        print(f'  ({x:3d},{y:3d}): PAD={pad_value:.3f} → OLD={fuel_factor_old:.3f} | NEW={fuel_factor_new:.3f} | Improvement: {improvement:.1f}x')

print(f'\n🎯 EXPECTED IMPACT:')
print(f'✅ Most forest cells will have 5-8x more effective fuel')
print(f'✅ Fire should spread much more realistically')
print(f'✅ Calibration should find lower spread_probability values')
print(f'✅ Simulation fire sizes should match EMSR data better')

print(f'\n🔧 NORMALIZATION PATH LOGIC:')
print(f'OLD (initial_fuel_load=8.0): max_fuel=8.0 > 1.0 → Legacy path → fuel_factor = PAD/8.0')
print(f'NEW (initial_fuel_load=1.0): max_fuel=1.0 ≤ 1.0 → PAD path → fuel_factor = min(PAD, 1.0)')

# Calculate statistics
non_zero_mask = layer_1 > 0
pad_values = layer_1[non_zero_mask]

fuel_factors_old = np.minimum(1.0, pad_values / 8.0)
fuel_factors_new = np.minimum(pad_values, 1.0)

print(f'\n📈 FOREST-WIDE STATISTICS:')
print(f'Non-zero cells: {np.sum(non_zero_mask):,} / {layer_1.size:,} ({np.sum(non_zero_mask)/layer_1.size*100:.1f}%)')
print(f'OLD fuel factors: mean={fuel_factors_old.mean():.3f}, max={fuel_factors_old.max():.3f}')
print(f'NEW fuel factors: mean={fuel_factors_new.mean():.3f}, max={fuel_factors_new.max():.3f}')
print(f'Average improvement: {fuel_factors_new.mean() / fuel_factors_old.mean():.1f}x better!')
