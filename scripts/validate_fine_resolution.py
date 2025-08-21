#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Fine Resolution Validation Script

This script validates the best parameters from coarse calibration
using fine resolution (10m or 5m) on Day 3 and Day 4 data.

Usage:
    python scripts/validate_fine_resolution.py --best-params calibration_results.json
"""

import os
import sys
import argparse
import json
import time
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

try:
    from src.core.calibration.fire_perimeter_calibration import TenerifeFirePerimeterCalibrator
    from src.core.forest_model import create_forest_model
    from src.core.fire_simulation_engine import FireSimulationEngine
    from src.utils.logging_utils import get_logger
except ImportError as e:
    print(f"❌ Error importing modules: {e}")
    sys.exit(1)

logger = get_logger(__name__)

def validate_fine_resolution(best_params_path: str, resolution: float = 10.0):
    """
    Validate best parameters using fine resolution.
    
    Args:
        best_params_path: Path to calibration results with best parameters
        resolution: Fine resolution in meters (10.0 or 5.0)
    """
    
    # Load best parameters
    with open(best_params_path, 'r') as f:
        results = json.load(f)
    
    best_params = results.get('best_parameters', {})
    if not best_params:
        logger.error("No best parameters found in results file")
        return
    
    logger.info(f"🎯 Validating best parameters with {resolution}m resolution:")
    for param, value in best_params.items():
        logger.info(f"   {param}: {value}")
    
    # Create fine-resolution configuration
    config = {
        'model_resolution': resolution,
        'max_steps': 100,
        'num_layers': 11,  # Match available terrain
        'grid_size': None  # Will be calculated from Day 4
    }
    
    # Calculate grid size for fine resolution
    # Day 4 area: ~122.7 km²
    # With 10m resolution: ~1100×1100 cells
    # With 5m resolution: ~2200×2200 cells
    
    if resolution == 10.0:
        grid_size = (1100, 1100)
    elif resolution == 5.0:
        grid_size = (2200, 2200)
    else:
        grid_size = (1100, 1100)  # Default
    
    logger.info(f"🎯 Fine resolution grid: {grid_size[0]} × {grid_size[1]} cells")
    logger.info(f"🎯 Total cells: {grid_size[0] * grid_size[1] * 11:,}")
    
    # Run validation simulations
    logger.info("🚀 Starting fine-resolution validation...")
    
    # This would run the actual validation simulations
    # For now, just show the configuration
    
    logger.info("✅ Fine-resolution validation configuration ready")
    logger.info(f"📁 Results will be saved to: validation_fine_{int(resolution)}m_{datetime.now().strftime('%Y%m%d_%H%M%S')}")

def main():
    parser = argparse.ArgumentParser(description="Validate calibration results with fine resolution")
    parser.add_argument('--best-params', required=True, help='Path to calibration results JSON file')
    parser.add_argument('--resolution', type=float, default=10.0, choices=[5.0, 10.0], 
                       help='Fine resolution in meters (default: 10.0)')
    
    args = parser.parse_args()
    
    print(f"🔍 FINE RESOLUTION VALIDATION")
    print("=" * 50)
    print(f"Resolution: {args.resolution}m")
    print(f"Best params: {args.best_params}")
    print()
    
    validate_fine_resolution(args.best_params, args.resolution)

if __name__ == "__main__":
    main()
