#!/usr/bin/env python3
"""
Test script to verify vertical fire spread statistics integration
"""

import json
import sys
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent))

def test_vertical_spread_integration():
    """Test that vertical fire spread statistics are included in calibration results"""
    print("🧪 Testing Vertical Fire Spread Integration")
    print("=" * 50)
    
    # Check if there are any existing calibration results
    results_dir = Path("calibration_results")
    if not results_dir.exists():
        print("❌ No calibration results directory found")
        print("   Run a calibration first to test the integration")
        return False
    
    # Find the most recent calibration results
    calibration_dirs = [d for d in results_dir.iterdir() if d.is_dir() and "calibration" in d.name]
    if not calibration_dirs:
        print("❌ No calibration directories found")
        return False
    
    # Sort by modification time (most recent first)
    calibration_dirs.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    latest_calibration = calibration_dirs[0]
    
    print(f"📁 Found latest calibration: {latest_calibration.name}")
    
    # Look for results JSON files
    json_files = list(latest_calibration.glob("*.json"))
    if not json_files:
        print("❌ No JSON results files found")
        return False
    
    print(f"📄 Found {len(json_files)} JSON files")
    
    # Check each JSON file for vertical fire spread statistics
    for json_file in json_files:
        print(f"\n🔍 Checking: {json_file.name}")
        
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
            
            # Check if this is a results file with individual simulation results
            if 'results' in data and isinstance(data['results'], list):
                print(f"   ✅ Found results array with {len(data['results'])} simulations")
                
                # Check first few results for vertical fire spread data
                vertical_spread_found = 0
                total_results = min(5, len(data['results']))  # Check first 5 results
                
                for i, result in enumerate(data['results'][:total_results]):
                    if 'vertical_fire_spread' in result:
                        vertical_spread_found += 1
                        vertical_data = result['vertical_fire_spread']
                        
                        if vertical_data is not None:
                            print(f"   📊 Result {i+1}: Vertical spread data found!")
                            print(f"      - Total spread events: {vertical_data.get('total_spread_events', 'N/A')}")
                            print(f"      - Vertical spread: {vertical_data.get('vertical_spread_percentage', 'N/A'):.1f}%")
                            print(f"      - Vertical efficiency: {vertical_data.get('vertical_efficiency', 'N/A'):.1f}%")
                            print(f"      - Classification: {vertical_data.get('spread_classification', 'N/A')}")
                        else:
                            print(f"   ⚠️  Result {i+1}: vertical_fire_spread is None")
                    else:
                        print(f"   ❌ Result {i+1}: No vertical_fire_spread field found")
                
                print(f"   📈 Summary: {vertical_spread_found}/{total_results} results have vertical spread data")
                
                if vertical_spread_found > 0:
                    print("   ✅ Vertical fire spread integration is working!")
                    return True
                else:
                    print("   ❌ No vertical fire spread data found in results")
                    
            else:
                print(f"   ℹ️  Not a results file (no 'results' array)")
                
        except Exception as e:
            print(f"   ❌ Error reading {json_file.name}: {e}")
    
    print("\n❌ No vertical fire spread data found in any results files")
    return False

def show_example_output():
    """Show example of what the vertical fire spread data looks like"""
    print("\n📋 Example Vertical Fire Spread Output:")
    print("=" * 40)
    
    example_data = {
        "parameter_values": {
            "spread_probability": 0.8,
            "wind_speed": 5.0
        },
        "objective_value": 0.123,
        "simulation_stats": {
            "total_burned_cells": 23537,
            "final_active_cells": 390
        },
        "vertical_fire_spread": {
            "total_spread_events": 52339,
            "vertical_spread_events": 19900,
            "vertical_spread_percentage": 38.0,
            "horizontal_spread_events": 0,
            "horizontal_spread_percentage": 0.0,
            "ember_spread_events": 11687,
            "ember_spread_percentage": 22.3,
            "total_ignitions": 20326,
            "vertical_efficiency": 97.9,
            "vertical_horizontal_ratio": 0.0,
            "spread_classification": "High vertical spread - strong convection"
        },
        "evaluation_time": 738.43
    }
    
    print(json.dumps(example_data, indent=2))

if __name__ == "__main__":
    print("🔥 Vertical Fire Spread Integration Test")
    print("This test verifies that vertical fire spread statistics are included in calibration results")
    print()
    
    success = test_vertical_spread_integration()
    
    if not success:
        print("\n💡 To test the integration:")
        print("   1. Run a calibration: python scripts/run_tenerife_calibration_clean.py --workers 2 --grid-points 2 --max-steps 50")
        print("   2. Run this test again to verify the results include vertical fire spread data")
    
    show_example_output()
