#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Parameter Consistency Validation Script

This script validates that all parameter definitions are consistent across
the sensitivity analysis framework files.
"""

def validate_parameter_consistency():
    """Validate parameter consistency across all files."""
    
    print("🔍 VALIDATING PARAMETER CONSISTENCY ACROSS FRAMEWORK")
    print("=" * 60)
    
    try:
        # Import required modules
        from src.core.calibration.parameter_bounds import get_default_calibration_bounds
        from src.core.calibration.calibration_config import CalibrationConfig
        from scripts.sensitivity_analysis_runner import HPCOptimizedSensitivityRunner
        
        # Get parameters from different sources
        bounds_params = set(get_default_calibration_bounds().keys())
        print(f"📊 Parameter Bounds: {len(bounds_params)} parameters")
        
        config = CalibrationConfig()
        config_params = set(config.calibration_parameters)
        print(f"⚙️  Calibration Config: {len(config_params)} parameters")
        
        runner = HPCOptimizedSensitivityRunner()
        runner_params = set(runner._get_all_calibration_parameters())
        print(f"🚀 Sensitivity Runner: {len(runner_params)} parameters")
        
        print("\n🔍 CONSISTENCY CHECK:")
        
        # Check if all sets are identical
        if bounds_params == config_params == runner_params:
            print("✅ ALL PARAMETER SETS ARE IDENTICAL")
            print(f"✅ Total Parameters: {len(bounds_params)}")
            
            print("\n📋 Parameter List:")
            for i, param in enumerate(sorted(bounds_params), 1):
                print(f"  {i:2d}. {param}")
                
            print("\n🎯 VALIDATION RESULT: SUCCESS")
            print("   All files define identical parameter sets")
            return True
            
        else:
            print("❌ PARAMETER SETS ARE INCONSISTENT")
            
            # Show differences
            all_params = bounds_params | config_params | runner_params
            
            print("\n📊 Parameter Comparison:")
            print("Parameter                     | Bounds | Config | Runner")
            print("-" * 50)
            
            for param in sorted(all_params):
                bounds_mark = "✅" if param in bounds_params else "❌"
                config_mark = "✅" if param in config_params else "❌"
                runner_mark = "✅" if param in runner_params else "❌"
                print(f"{param:28} |   {bounds_mark}   |   {config_mark}   |   {runner_mark}")
                
            print("\n🎯 VALIDATION RESULT: FAILURE")
            print("   Parameter sets are inconsistent between files")
            return False
            
    except Exception as e:
        print(f"❌ VALIDATION ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = validate_parameter_consistency()
    exit(0 if success else 1)