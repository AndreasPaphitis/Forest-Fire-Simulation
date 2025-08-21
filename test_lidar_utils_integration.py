#!/usr/bin/env python
"""
Integration test for LiDAR utilities with mock data.
"""

import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_lidar_utils_with_mock_data():
    """Test LiDAR utilities with mock data."""
    print("🧪 Testing LiDAR utilities with mock data...")
    
    # Create temporary directory with mock PAD files
    with tempfile.TemporaryDirectory() as temp_dir:
        pad_rasters_dir = Path(temp_dir) / "pad_rasters"
        pad_rasters_dir.mkdir()
        
        # Create mock PAD files
        mock_files = [
            "PNOA_2016_CANAR-TF_378-3152_ORT-CLA-CIR_vegetation_pad_0.0m.tif",  # Should be excluded
            "PNOA_2016_CANAR-TF_378-3152_ORT-CLA-CIR_vegetation_pad_2.0m.tif",  # Layer 1
            "PNOA_2016_CANAR-TF_378-3152_ORT-CLA-CIR_vegetation_pad_4.0m.tif",  # Layer 2
            "PNOA_2016_CANAR-TF_378-3152_ORT-CLA-CIR_vegetation_pad_6.0m.tif",  # Layer 3
            "PNOA_2016_CANAR-TF_378-3152_ORT-CLA-CIR_vegetation_pad_8.0m.tif",  # Layer 4
            "other_dataset_pad_2.0m.tif",  # Multiple datasets for same height
        ]
        
        for filename in mock_files:
            (pad_rasters_dir / filename).touch()
        
        print(f"  Created mock PAD files in {pad_rasters_dir}")
        
        # Import and test LiDAR utilities
        from src.utils.lidar_utils import LiDARDataManager
        
        # Create a mock config
        mock_config = MagicMock()
        mock_config.layer_height = 2.0
        
        # Create LiDAR manager
        lidar_manager = LiDARDataManager(
            base_dir=temp_dir,
            resolution=20.0,
            config=mock_config
        )
        
        print("  ✅ LiDARDataManager created successfully")
        
        # Test layer detection
        available_layers = lidar_manager._detect_available_layers(temp_dir)
        print(f"  Detected layers: {available_layers}")
        
        # Verify layer 0 is excluded
        assert 0 not in available_layers, "❌ Layer 0 should be excluded"
        print("  ✅ Layer 0 correctly excluded")
        
        # Verify correct layers are detected
        expected_layers = {1, 2, 3, 4}
        assert set(available_layers.keys()) == expected_layers, f"❌ Expected layers {expected_layers}, got {set(available_layers.keys())}"
        print("  ✅ Correct layers detected")
        
        # Verify file counts
        assert len(available_layers[1]) == 2, f"❌ Layer 1 should have 2 files, got {len(available_layers[1])}"
        assert len(available_layers[2]) == 1, f"❌ Layer 2 should have 1 file, got {len(available_layers[2])}"
        assert len(available_layers[3]) == 1, f"❌ Layer 3 should have 1 file, got {len(available_layers[3])}"
        assert len(available_layers[4]) == 1, f"❌ Layer 4 should have 1 file, got {len(available_layers[4])}"
        print("  ✅ Correct file counts per layer")
        
        # Test max layer calculation
        max_layers = lidar_manager.get_max_available_layers(temp_dir)
        assert max_layers == 4, f"❌ Expected max layers 4, got {max_layers}"
        print(f"  ✅ Max layers: {max_layers}")
        
        # Test layer file finding
        for layer in range(4):
            files = lidar_manager._find_layer_files(temp_dir, layer)
            expected_height = (layer + 1) * 2
            print(f"  Layer {layer} -> height {expected_height}m -> {len(files)} files")
        
        print("🎉 All LiDAR utilities tests passed!")

if __name__ == "__main__":
    test_lidar_utils_with_mock_data()
