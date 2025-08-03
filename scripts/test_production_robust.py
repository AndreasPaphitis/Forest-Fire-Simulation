#!/usr/bin/env python3
"""
Test script for robust production configuration.
This script tests the forest fire simulation with improved error handling.
"""

import sys
import os
import logging
import traceback
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def setup_logging():
    """Setup comprehensive logging."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('production_test.log')
        ]
    )
    return logging.getLogger(__name__)

def test_robust_production():
    """Test the robust production configuration."""
    logger = setup_logging()
    
    try:
        logger.info("🚀 Starting Robust Production Test")
        
        # Import the production simulation runner
        from run_production_sim import main as run_production
        
        # Test with robust configuration
        config_file = "hpc_deployment/Forest_Fire_Simulation_production_test.json"
        
        if not os.path.exists(config_file):
            logger.error(f"Configuration file not found: {config_file}")
            return False
            
        logger.info(f"Using configuration: {config_file}")
        
        # Run the simulation
        result = run_production(config_file)
        
        if result:
            logger.info("✅ Robust production test completed successfully")
            return True
        else:
            logger.error("❌ Robust production test failed")
            return False
            
    except Exception as e:
        logger.error(f"💥 Critical error in production test: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

def test_emergency_fallback():
    """Test the emergency fallback configuration."""
    logger = setup_logging()
    
    try:
        logger.info("🆘 Starting Emergency Fallback Test")
        
        # Import the production simulation runner
        from run_production_sim import main as run_production
        
        # Test with emergency configuration
        config_file = "hpc_deployment/Forest_Fire_Simulation_emergency_test.json"
        
        if not os.path.exists(config_file):
            logger.error(f"Emergency configuration file not found: {config_file}")
            return False
            
        logger.info(f"Using emergency configuration: {config_file}")
        
        # Run the simulation
        result = run_production(config_file)
        
        if result:
            logger.info("✅ Emergency fallback test completed successfully")
            return True
        else:
            logger.error("❌ Emergency fallback test failed")
            return False
            
    except Exception as e:
        logger.error(f"💥 Critical error in emergency test: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    logger = setup_logging()
    
    # Test both configurations
    logger.info("=" * 60)
    logger.info("FOREST FIRE SIMULATION - ROBUST TESTING")
    logger.info("=" * 60)
    
    # First test emergency fallback (simpler)
    emergency_success = test_emergency_fallback()
    
    logger.info("-" * 60)
    
    # Then test robust production
    production_success = test_robust_production()
    
    logger.info("=" * 60)
    logger.info("FINAL RESULTS:")
    logger.info(f"Emergency Test: {'✅ PASSED' if emergency_success else '❌ FAILED'}")
    logger.info(f"Production Test: {'✅ PASSED' if production_success else '❌ FAILED'}")
    
    if emergency_success and production_success:
        logger.info("🎉 ALL TESTS PASSED - READY FOR HPC DEPLOYMENT")
        sys.exit(0)
    elif emergency_success:
        logger.info("⚠️  EMERGENCY CONFIG WORKS - USE FOR BASIC TESTING")
        sys.exit(1)
    else:
        logger.info("💥 ALL TESTS FAILED - NEEDS DEBUGGING")
        sys.exit(2) 