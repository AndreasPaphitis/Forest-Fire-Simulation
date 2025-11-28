#!/usr/bin/env python3

import numpy as np
import json

print('🔍 EXAMINING PREPROCESSED LIDAR DATA')
print('=' * 50)

# Load metadata
with open('preprocessed_lidar/lidar_metadata.json', 'r') as f:
    metadata = json.load(f)

print('📊 Metadata overview:')
print(f'Grid size: {metadata["grid_size"]}') 
print(f'Resolution: {metadata["resolution"]}m')
print(f'Num layers: {metadata["num_layers"]}')
print(f'Available layers: {len(metadata["available_layers"])}')
print()

# Load a few sample layers to see actual data ranges
layers_to_check = [1, 5, 10, 20]
print('📈 Layer data analysis:')

for layer_idx in layers_to_check:
    try:
        layer_file = f'preprocessed_lidar/layer_{layer_idx:02d}.npy'
        data = np.load(layer_file)
        
        print(f'Layer {layer_idx:2d}: shape={data.shape}, dtype={data.dtype}')
        print(f'          min={data.min():.4f}, max={data.max():.4f}, mean={data.mean():.4f}')
        print(f'          non-zero: {np.count_nonzero(data):,} / {data.size:,} ({np.count_nonzero(data)/data.size*100:.1f}%)')
        print()
        
    except Exception as e:
        print(f'Layer {layer_idx}: Error loading - {e}')

# Check if data is normalized
print('🎯 FUEL NORMALIZATION CHECK:')
layer_1 = np.load('preprocessed_lidar/layer_01.npy')
print(f'Layer 1 data range: {layer_1.min():.4f} to {layer_1.max():.4f}')

if layer_1.max() <= 1.0:
    print('✅ Data appears to be normalized (0-1 range)')
    print('   → Will use PAD normalization path in simulation')
else:
    print('⚠️  Data is NOT normalized (>1.0 range)')  
    print('   → Will use Legacy normalization path in simulation')
    print(f'   → With initial_fuel_load=8.0: fuel_factor = value/8.0')

# Sample some specific values
sample_indices = [(100, 100), (200, 200), (300, 300)]
print(f'\n🔍 Sample fuel values at specific locations:')
for x, y in sample_indices:
    if x < layer_1.shape[0] and y < layer_1.shape[1]:
        value = layer_1[x, y]
        fuel_factor_legacy = min(1.0, value / 8.0)
        fuel_factor_pad = value if value <= 1.0 else 1.0
        print(f'  ({x:3d},{y:3d}): value={value:.4f} → legacy_factor={fuel_factor_legacy:.4f}, pad_factor={fuel_factor_pad:.4f}')

print(f'\n🎯 CRITICAL ANALYSIS:')
print(f'If data max > 1.0 AND initial_fuel_load > 1.0:')
print(f'  → Uses Legacy path: fuel_factor = min(1.0, value / initial_fuel_load)')
print(f'  → With initial_fuel_load=8.0: Most values become very small!')
print(f'If data max <= 1.0 AND initial_fuel_load <= 1.0:')
print(f'  → Uses PAD path: fuel_factor = value directly')
print(f'  → Better fuel representation!')
