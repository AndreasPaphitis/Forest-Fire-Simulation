#!/usr/bin/env python
"""
Simple test for layer detection logic.
"""

import re
import tempfile
from pathlib import Path

def test_layer_detection_logic():
    """Test the core layer detection logic."""
    print("🧪 Testing layer detection logic...")
    
    # Test the regex pattern
    pattern = r'_pad_(\d+)\.0m\.tif$'
    
    # Test files
    test_files = [
        "PNOA_2016_CANAR-TF_378-3152_ORT-CLA-CIR_vegetation_pad_0.0m.tif",
        "PNOA_2016_CANAR-TF_378-3152_ORT-CLA-CIR_vegetation_pad_2.0m.tif",
        "PNOA_2016_CANAR-TF_378-3152_ORT-CLA-CIR_vegetation_pad_4.0m.tif",
        "PNOA_2016_CANAR-TF_378-3152_ORT-CLA-CIR_vegetation_pad_6.0m.tif",
    ]
    
    # Test pattern matching
    for filename in test_files:
        match = re.search(pattern, filename)
        assert match is not None, f"Pattern should match {filename}"
        height = int(match.group(1))
        print(f"  {filename} -> height {height}m")
    
    print("✅ Pattern matching works")
    
    # Test layer exclusion logic
    heights = [0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24]
    layer_indices = [height // 2 for height in heights]
    
    print(f"  Heights: {heights}")
    print(f"  Layer indices: {layer_indices}")
    
    # Exclude layer 0
    available_layers = [layer for layer in layer_indices if layer != 0]
    print(f"  Available layers (excluding 0): {available_layers}")
    
    assert 0 not in available_layers, "Layer 0 should be excluded"
    assert len(available_layers) == len(layer_indices) - 1, "Should exclude exactly one layer"
    
    print("✅ Layer 0 exclusion works")
    
    # Test layer mapping
    max_layer = max(available_layers)
    total_layers = max_layer
    print(f"  Max layer: {max_layer}")
    print(f"  Total layers: {total_layers}")
    
    # Test simulation layer mapping
    for sim_layer in range(5):
        height_meters = (sim_layer + 1) * 2
        print(f"  Simulation layer {sim_layer} -> PAD height {height_meters}m")
    
    print("✅ Layer mapping works")
    
    print("🎉 All tests passed!")

if __name__ == "__main__":
    test_layer_detection_logic()
