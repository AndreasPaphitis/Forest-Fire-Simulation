#!/usr/bin/env python3
"""
Verify Preprocessed LiDAR Data

This script verifies the quality and structure of preprocessed LiDAR data.

Author: Forest Fire Simulation Team
Date: 2025
Version: 1.0
"""

import sys
import os
from pathlib import Path
import numpy as np
import json
import logging

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.utils.logging_utils import get_logger
from src.utils.preprocessed_lidar_loader import PreprocessedLiDARLoader

logger = get_logger(__name__)

def verify_preprocessed_lidar():
    """Verify the preprocessed LiDAR data."""
    logger.info("🔍 VERIFYING PREPROCESSED LIDAR DATA")
    
    preprocessed_dir = "preprocessed_lidar"
    
    if not Path(preprocessed_dir).exists():
        logger.error(f"❌ Preprocessed directory not found: {preprocessed_dir}")
        return False
    
    logger.info(f"📁 Checking directory: {preprocessed_dir}")
    
    # Check metadata files
    metadata_file = Path(preprocessed_dir) / "lidar_metadata.json"
    file_paths_file = Path(preprocessed_dir) / "file_paths.json"
    
    if not metadata_file.exists():
        logger.error("❌ lidar_metadata.json not found")
        return False
    
    if not file_paths_file.exists():
        logger.error("❌ file_paths.json not found")
        return False
    
    logger.info("✅ Metadata files found")
    
    # Load and check metadata
    try:
        with open(metadata_file, 'r') as f:
            metadata = json.load(f)
        
        logger.info(f"📊 Metadata loaded successfully")
        logger.info(f"   Resolution: {metadata.get('resolution', 'N/A')}m")
        logger.info(f"   Grid size: {metadata.get('grid_size', 'N/A')}")
        logger.info(f"   Fire bounds: {metadata.get('fire_bounds', 'N/A')}")
        logger.info(f"   Number of layers: {metadata.get('num_layers', 'N/A')}")
        
    except Exception as e:
        logger.error(f"❌ Failed to load metadata: {e}")
        return False
    
    # Check layer files
    layer_files = list(Path(preprocessed_dir).glob("layer_*.npy"))
    logger.info(f"📁 Found {len(layer_files)} layer files")
    
    if len(layer_files) == 0:
        logger.error("❌ No layer files found")
        return False
    
    # Sort layer files
    layer_files.sort()
    
    # Check each layer
    total_size = 0
    layer_info = []
    
    for layer_file in layer_files:
        try:
            # Load layer data
            layer_data = np.load(layer_file)
            
            # Get layer number from filename
            layer_num = int(layer_file.stem.split('_')[1])
            
            # Calculate statistics
            file_size = layer_file.stat().st_size / (1024 * 1024)  # MB
            total_size += file_size
            
            non_zero = np.count_nonzero(layer_data)
            total_cells = layer_data.size
            coverage = (non_zero / total_cells) * 100
            
            min_val = np.min(layer_data)
            max_val = np.max(layer_data)
            mean_val = np.mean(layer_data[layer_data > 0]) if non_zero > 0 else 0
            
            layer_info.append({
                'layer': layer_num,
                'shape': layer_data.shape,
                'size_mb': file_size,
                'coverage_pct': coverage,
                'min_val': min_val,
                'max_val': max_val,
                'mean_val': mean_val,
                'non_zero_cells': non_zero,
                'total_cells': total_cells
            })
            
            logger.info(f"   Layer {layer_num:2d}: {layer_data.shape}, {file_size:.1f}MB, {coverage:.1f}% coverage")
            
        except Exception as e:
            logger.error(f"❌ Failed to load layer {layer_file.name}: {e}")
            return False
    
    logger.info(f"📊 Total size: {total_size:.1f}MB")
    
    # Test the loader
    try:
        logger.info("🧪 Testing PreprocessedLiDARLoader...")
        loader = PreprocessedLiDARLoader(preprocessed_dir)
        
        # Test loading all layers
        all_layers = loader.load_all_layers()
        
        if all_layers is None:
            logger.error("❌ Failed to load all layers")
            return False
        
        logger.info(f"✅ Successfully loaded {len(all_layers)} layers via loader")
        
        # Check first layer structure
        first_layer = list(all_layers.values())[0]
        logger.info(f"   First layer shape: {first_layer.shape}")
        logger.info(f"   First layer dtype: {first_layer.dtype}")
        
    except Exception as e:
        logger.error(f"❌ Loader test failed: {e}")
        return False
    
    # Summary
    logger.info("🎯 VERIFICATION SUMMARY:")
    logger.info(f"   ✅ Directory exists: {preprocessed_dir}")
    logger.info(f"   ✅ Metadata files: 2")
    logger.info(f"   ✅ Layer files: {len(layer_files)}")
    logger.info(f"   ✅ Total size: {total_size:.1f}MB")
    logger.info(f"   ✅ Loader works: Yes")
    
    # Coverage analysis
    coverages = [info['coverage_pct'] for info in layer_info]
    logger.info(f"   📊 Coverage range: {min(coverages):.1f}% - {max(coverages):.1f}%")
    logger.info(f"   📊 Average coverage: {np.mean(coverages):.1f}%")
    
    # Value range analysis
    all_mins = [info['min_val'] for info in layer_info]
    all_maxs = [info['max_val'] for info in layer_info]
    logger.info(f"   📊 Value range: {min(all_mins):.2e} - {max(all_maxs):.2f}")
    
    logger.info("✅ PREPROCESSED LIDAR DATA VERIFICATION COMPLETED")
    return True

if __name__ == "__main__":
    success = verify_preprocessed_lidar()
    if not success:
        sys.exit(1)
