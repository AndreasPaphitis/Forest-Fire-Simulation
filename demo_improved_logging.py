#!/usr/bin/env python3
"""
Demo script showing improved fire simulation logging output.
This demonstrates how the new logging system provides more readable and informative output.
"""

import logging
import time
from datetime import datetime

# Configure logging to show the improved format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger('demo')

def demo_original_output():
    """Show what the original verbose output looked like."""
    print("\n" + "="*80)
    print("ORIGINAL VERBOSE OUTPUT (Problematic)")
    print("="*80)
    
    # Simulate the original repetitive output
    for i in range(20):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S,%f')[:-3]
        logger.info(f"BURNOUT: Cell (3112,2783,0) burned out - fuel: 3.00 -> 0.00 (threshold: 0.1)")
        logger.info(f"ENGINE DEBUG: Initial active_cells detected: 1 cells")
        time.sleep(0.01)  # Simulate processing time

def demo_improved_output():
    """Show what the improved output looks like."""
    print("\n" + "="*80)
    print("IMPROVED READABLE OUTPUT (New)")
    print("="*80)
    
    # Simulate the improved initialization
    logger.info("🔥 FIRE SIMULATION INITIALIZED")
    logger.info("   Grid Size: 537 × 453 × 1 = 243,261 total cells")
    logger.info("   Initial Fire: 1 active cells (0.000% of grid)")
    logger.info("   Ignition Points: [(3112, 2783, 0)]")
    
    # Simulate step progress
    logger.info("📊 STEP 1/1000")
    logger.info("   Active: 5 cells | Burned: 1 cells")
    logger.info("   Total Affected: 6 cells (0.002% of grid)")
    logger.info("   Spread Rate: 5.00 active cells/step")
    
    # Simulate burnout batch processing
    logger.info("🔥 BURNOUT: Cell (3112,2783,0) - fuel: 3.00 → 0.00 (threshold: 0.1)")
    logger.info("🔥 BURNOUT: Cell (3112,2784,0) - fuel: 3.00 → 0.00 (threshold: 0.1)")
    logger.info("🔥 BURNOUT: Cell (3111,2783,0) - fuel: 0.35 → 0.00 (threshold: 0.1)")
    
    # Simulate batch progress
    logger.info("📈 BURNOUT BATCH: 50 cells burned out")
    logger.info("   Total Burnouts: 150 | Active: 25 | Affected: 0.072% of grid")
    
    # Simulate final statistics
    logger.info("🏁 SIMULATION COMPLETED")
    logger.info("   Runtime: 45.23 seconds (0.75 minutes)")
    logger.info("   Steps: 156 simulation steps")
    logger.info("   Final Results:")
    logger.info("     • Burned Cells: 1,247 (0.513% of grid)")
    logger.info("     • Still Burning: 0 cells")
    logger.info("     • Peak Active: 89 cells")
    logger.info("   Performance: 27.6 cells burned/second")

def demo_comparison():
    """Show a side-by-side comparison."""
    print("\n" + "="*80)
    print("COMPARISON: Original vs Improved")
    print("="*80)
    
    print("ORIGINAL PROBLEMS:")
    print("❌ Repetitive burnout messages (hundreds of identical lines)")
    print("❌ No context about grid size or percentages")
    print("❌ No progress tracking or batch processing")
    print("❌ Difficult to understand simulation state")
    print("❌ No performance metrics")
    print("❌ Verbose debug messages cluttering output")
    
    print("\nIMPROVED FEATURES:")
    print("✅ Clear initialization with grid information")
    print("✅ Progress tracking with percentages and rates")
    print("✅ Batch processing of burnout events")
    print("✅ Performance metrics (cells/second)")
    print("✅ Comprehensive final statistics")
    print("✅ Emoji indicators for different message types")
    print("✅ Reduced verbosity while maintaining information")

if __name__ == "__main__":
    demo_original_output()
    demo_improved_output()
    demo_comparison()
    
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print("The improved logging system provides:")
    print("• Better readability with structured output")
    print("• Progress tracking and performance metrics")
    print("• Reduced verbosity through batch processing")
    print("• Clear visual indicators and formatting")
    print("• Comprehensive statistics and context")
    print("\nThis makes it much easier to monitor fire simulation progress")
    print("and understand what's happening during execution.")
