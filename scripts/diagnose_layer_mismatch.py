#!/usr/bin/env python
"""
Comprehensive Layer Mismatch Diagnosis Script

This script helps identify and diagnose layer mismatch issues in the forest fire simulation.
It checks all components involved in layer handling and provides detailed diagnostics.
"""

import os
import sys
from pathlib import Path
import logging

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))

from src.utils.lidar_utils import LiDARDataManager
from src.config.config_tools import ModelConfig

def setup_logging():
    """Setup logging for diagnostics."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('layer_mismatch_diagnosis.log')
        ]
    )
    return logging.getLogger(__name__)

def diagnose_configuration():
    """Diagnose configuration layer settings."""
    logger = logging.getLogger(__name__)
    logger.info("🔍 DIAGNOSING CONFIGURATION")
    logger.info("=" * 50)
    
    # Check CUSTOM_CONFIG
    try:
        from scripts.run_tenerife_calibration_custom import CUSTOM_CONFIG
        logger.info(f"✅ CUSTOM_CONFIG loaded:")
        logger.info(f"   - num_layers: {CUSTOM_CONFIG['num_layers']}")
        logger.info(f"   - Type: {type(CUSTOM_CONFIG['num_layers'])}")
        logger.info(f"   - Is None: {CUSTOM_CONFIG['num_layers'] is None}")
    except Exception as e:
        logger.error(f"❌ Failed to load CUSTOM_CONFIG: {e}")
    
    # Check ModelConfig defaults
    try:
        config = ModelConfig()
        logger.info(f"✅ ModelConfig defaults:")
        logger.info(f"   - num_layers: {config.num_layers}")
        logger.info(f"   - Type: {type(config.num_layers)}")
    except Exception as e:
        logger.error(f"❌ Failed to create ModelConfig: {e}")

def diagnose_lidar_detection():
    """Diagnose LiDAR layer detection."""
    logger = logging.getLogger(__name__)
    logger.info("\n🔍 DIAGNOSING LIDAR DETECTION")
    logger.info("=" * 50)
    
    lidar_data_dir = r"C:\Users\user\Desktop\UvA\YEAR 2\Thesis\LiDAR\Analysis files\Processed\PAD Results"
    
    try:
        # Create LiDAR manager
        lidar_manager = LiDARDataManager(
            base_dir=lidar_data_dir,
            resolution=20.0,
            config=None
        )
        logger.info(f"✅ LiDARDataManager created")
        logger.info(f"   - Base directory: {lidar_data_dir}")
        logger.info(f"   - Directory exists: {Path(lidar_data_dir).exists()}")
        
        # Check directory structure
        if Path(lidar_data_dir).exists():
            pnoa_dirs = [d for d in Path(lidar_data_dir).iterdir() if d.is_dir() and d.name.startswith("PNOA")]
            logger.info(f"   - PNOA directories found: {len(pnoa_dirs)}")
            for pnoa_dir in pnoa_dirs:
                logger.info(f"     * {pnoa_dir.name}")
                
                # Check pad_rasters directory
                pad_rasters_dir = pnoa_dir / "pad_rasters"
                if pad_rasters_dir.exists():
                    pad_files = list(pad_rasters_dir.glob("*_pad_*.0m.tif"))
                    logger.info(f"       - PAD files: {len(pad_files)}")
                    
                    # Show first few files
                    for i, file in enumerate(pad_files[:5]):
                        logger.info(f"         {i+1}. {file.name}")
                    if len(pad_files) > 5:
                        logger.info(f"         ... and {len(pad_files) - 5} more")
                else:
                    logger.warning(f"       - No pad_rasters directory found")
        
        # Test layer detection without geographic bounds
        logger.info(f"\n🔍 Testing layer detection WITHOUT geographic bounds:")
        available_layers = lidar_manager._detect_available_layers(lidar_data_dir)
        max_layers = lidar_manager.get_max_available_layers(lidar_data_dir)
        
        logger.info(f"   - Available layers dict: {len(available_layers)} entries")
        logger.info(f"   - Available layer indices: {list(available_layers.keys()) if available_layers else 'None'}")
        logger.info(f"   - Max layers detected: {max_layers}")
        
        if available_layers:
            for layer_idx in sorted(available_layers.keys()):
                height_meters = layer_idx * 2
                file_count = len(available_layers[layer_idx])
                logger.info(f"   - Layer {layer_idx} (height {height_meters}m): {file_count} files")
        
        # Test layer detection WITH geographic bounds (fire area)
        logger.info(f"\n🔍 Testing layer detection WITH geographic bounds:")
        
        # Set geographic bounds for fire area (example bounds)
        geo_bounds = (342447.0, 3128903.5, 366389.8, 3149315.4)  # Example fire area bounds
        lidar_manager.geo_bounds = geo_bounds
        
        available_layers_bounded = lidar_manager._detect_available_layers(lidar_data_dir)
        max_layers_bounded = lidar_manager.get_max_available_layers(lidar_data_dir)
        
        logger.info(f"   - Geographic bounds: {geo_bounds}")
        logger.info(f"   - Available layers (bounded): {len(available_layers_bounded)} entries")
        logger.info(f"   - Available layer indices (bounded): {list(available_layers_bounded.keys()) if available_layers_bounded else 'None'}")
        logger.info(f"   - Max layers detected (bounded): {max_layers_bounded}")
        
        if available_layers_bounded:
            for layer_idx in sorted(available_layers_bounded.keys()):
                height_meters = layer_idx * 2
                file_count = len(available_layers_bounded[layer_idx])
                logger.info(f"   - Layer {layer_idx} (height {height_meters}m): {file_count} files")
        
        # Compare results
        logger.info(f"\n📊 COMPARISON:")
        logger.info(f"   - Total layers available: {len(available_layers)}")
        logger.info(f"   - Layers in fire area: {len(available_layers_bounded)}")
        logger.info(f"   - Geographic filtering effect: {len(available_layers) - len(available_layers_bounded)} layers excluded")
        
    except Exception as e:
        logger.error(f"❌ LiDAR detection failed: {e}")
        logger.error(f"   - Error type: {type(e).__name__}")
        logger.error(f"   - Error details: {str(e)}")

def diagnose_forest_model_initialization():
    """Diagnose forest model layer initialization."""
    logger = logging.getLogger(__name__)
    logger.info("\n🔍 DIAGNOSING FOREST MODEL INITIALIZATION")
    logger.info("=" * 50)
    
    try:
        from src.core.forest_model import ForestModel
        
        # Test with different layer counts
        test_layer_counts = [11, 12, 25]
        
        for num_layers in test_layer_counts:
            logger.info(f"\n🔍 Testing ForestModel with {num_layers} layers:")
            
            try:
                # Create forest model
                forest_model = ForestModel(
                    grid_size=(100, 100),
                    num_layers=num_layers,
                    model_resolution=20.0,
                    use_sparse_storage=True
                )
                
                logger.info(f"   ✅ ForestModel created successfully")
                logger.info(f"   - num_layers: {forest_model.num_layers}")
                logger.info(f"   - fuel_load_layers count: {len(forest_model.fuel_load_layers)}")
                logger.info(f"   - state_layers count: {len(forest_model.state_layers)}")
                
                # Test SparseLayerAccessor
                fuel_accessor = forest_model.fuel_load
                logger.info(f"   - fuel_load accessor type: {type(fuel_accessor)}")
                logger.info(f"   - fuel_load accessor num_layers: {fuel_accessor.num_layers}")
                logger.info(f"   - fuel_load sparse_layers length: {len(fuel_accessor.sparse_layers)}")
                
                # Validate layer count consistency
                if (forest_model.num_layers == num_layers and 
                    len(forest_model.fuel_load_layers) == num_layers and
                    len(forest_model.state_layers) == num_layers and
                    fuel_accessor.num_layers == num_layers and
                    len(fuel_accessor.sparse_layers) == num_layers):
                    logger.info(f"   ✅ All layer counts consistent")
                else:
                    logger.error(f"   ❌ Layer count mismatch detected")
                    logger.error(f"      - Expected: {num_layers}")
                    logger.error(f"      - ForestModel.num_layers: {forest_model.num_layers}")
                    logger.error(f"      - fuel_load_layers: {len(forest_model.fuel_load_layers)}")
                    logger.error(f"      - state_layers: {len(forest_model.state_layers)}")
                    logger.error(f"      - SparseLayerAccessor.num_layers: {fuel_accessor.num_layers}")
                    logger.error(f"      - SparseLayerAccessor.sparse_layers: {len(fuel_accessor.sparse_layers)}")
                
            except Exception as e:
                logger.error(f"   ❌ ForestModel creation failed: {e}")
                
    except Exception as e:
        logger.error(f"❌ Forest model diagnosis failed: {e}")

def diagnose_vegetation_integration():
    """Diagnose vegetation data integration."""
    logger = logging.getLogger(__name__)
    logger.info("\n🔍 DIAGNOSING VEGETATION INTEGRATION")
    logger.info("=" * 50)
    
    try:
        from src.core.vegetation_data_integration import TiledLiDARIntegration
        
        # Create test configuration
        config = ModelConfig(
            lidar_data_dir=r"C:\Users\user\Desktop\UvA\YEAR 2\Thesis\LiDAR\Analysis files\Processed\PAD Results",
            model_resolution=20.0,
            num_layers=11,  # Test with 11 layers
            geo_bounds=(342447.0, 3128903.5, 366389.8, 3149315.4)
        )
        
        logger.info(f"✅ Test configuration created:")
        logger.info(f"   - num_layers: {config.num_layers}")
        logger.info(f"   - lidar_data_dir: {config.lidar_data_dir}")
        logger.info(f"   - geo_bounds: {config.geo_bounds}")
        
        # Create vegetation integration
        integration = TiledLiDARIntegration(config=config)
        logger.info(f"✅ TiledLiDARIntegration created")
        
        # Test layer loading for a small tile
        logger.info(f"\n🔍 Testing layer loading for tile (0,0,10,10):")
        try:
            result = integration._load_lidar_data_for_tile(0, 0, 10, 10, 11)
            if result:
                logger.info(f"   ✅ Layer loading successful")
                logger.info(f"   - Result type: {type(result)}")
                logger.info(f"   - Result length: {len(result)}")
                logger.info(f"   - Result keys: {list(result.keys()) if isinstance(result, dict) else 'N/A'}")
            else:
                logger.warning(f"   ⚠️  Layer loading returned None")
        except Exception as e:
            logger.error(f"   ❌ Layer loading failed: {e}")
            
    except Exception as e:
        logger.error(f"❌ Vegetation integration diagnosis failed: {e}")

def generate_recommendations():
    """Generate recommendations based on diagnosis."""
    logger = logging.getLogger(__name__)
    logger.info("\n🎯 RECOMMENDATIONS")
    logger.info("=" * 50)
    
    logger.info("Based on the diagnosis, here are the recommended actions:")
    logger.info("")
    logger.info("1. ✅ CONFIGURATION:")
    logger.info("   - Ensure CUSTOM_CONFIG['num_layers'] is set to None for dynamic detection")
    logger.info("   - Remove any hardcoded layer count overrides")
    logger.info("")
    logger.info("2. 🔍 LIDAR DETECTION:")
    logger.info("   - Verify that LiDAR data directory exists and contains PAD files")
    logger.info("   - Check that geographic bounds are appropriate for your fire area")
    logger.info("   - Ensure PAD file naming convention matches expected pattern")
    logger.info("")
    logger.info("3. 🏗️  FOREST MODEL:")
    logger.info("   - Ensure forest model initialization uses detected layer count")
    logger.info("   - Verify SparseLayerAccessor receives correct layer count")
    logger.info("")
    logger.info("4. 🌱 VEGETATION INTEGRATION:")
    logger.info("   - Check layer mapping between PAD layers and simulation layers")
    logger.info("   - Verify that all expected layers have corresponding PAD files")
    logger.info("")
    logger.info("5. 🧪 TESTING:")
    logger.info("   - Run calibration with --dry-run to test configuration")
    logger.info("   - Monitor logs for layer mismatch warnings")
    logger.info("   - Use this diagnostic script to verify fixes")

def main():
    """Main diagnostic function."""
    logger = setup_logging()
    
    logger.info("🔍 COMPREHENSIVE LAYER MISMATCH DIAGNOSIS")
    logger.info("=" * 60)
    logger.info("This script will diagnose all components involved in layer handling")
    logger.info("and provide detailed information to help fix layer mismatch issues.")
    logger.info("")
    
    try:
        # Run all diagnostics
        diagnose_configuration()
        diagnose_lidar_detection()
        diagnose_forest_model_initialization()
        diagnose_vegetation_integration()
        generate_recommendations()
        
        logger.info("\n✅ DIAGNOSIS COMPLETE")
        logger.info("Check the log file 'layer_mismatch_diagnosis.log' for detailed results")
        
    except Exception as e:
        logger.error(f"❌ Diagnosis failed: {e}")
        raise

if __name__ == "__main__":
    main()
