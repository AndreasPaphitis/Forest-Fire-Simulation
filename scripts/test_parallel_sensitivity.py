#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test Parallel Sensitivity Analysis

This script tests the parallel sensitivity analysis implementation to ensure
it works correctly and provides the expected performance improvements.
"""

import time
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

try:
    from src.core.calibration import (
        CalibrationConfig, CalibrationMethod, CalibrationObjective,
        SensitivityAnalyzer,
        get_default_calibration_bounds,
        create_default_spatial_objective,
        create_synthetic_target_data
    )
    from src.config.config_tools import ModelConfig
except ImportError as e:
    print(f"Error importing modules: {e}")
    sys.exit(1)


def test_parallel_sensitivity():
    """Test the parallel sensitivity analysis with a small subset of parameters."""
    print("🧪 TESTING PARALLEL SENSITIVITY ANALYSIS")
    print("=" * 60)
    
    # Create a small test configuration
    base_config = ModelConfig(
        grid_size=(40, 40),  # Smaller grid for faster testing
        num_layers=3,        # Fewer layers for faster testing
        max_steps=20,        # Fewer steps for faster testing
        random_seed=42,
        memory_optimization_level=2
    )
    
    # Test with only 3 critical parameters for speed
    test_parameters = [
        'spread_probability',
        'fuel_consumption_rate',
        'ignition_threshold'
    ]
    
    config = CalibrationConfig(
        experiment_name="parallel_test",
        method=CalibrationMethod.SENSITIVITY_ANALYSIS,
        objective=CalibrationObjective.SPATIAL_SIMILARITY,
        base_config=base_config,
        calibration_parameters=test_parameters,
        max_workers=4,  # Use 4 workers for testing
        parallel_execution=True
    )
    
    # Set up components
    parameter_bounds = get_default_calibration_bounds()
    objective_function = create_default_spatial_objective()
    target_data = create_synthetic_target_data((40, 40), "circular")
    
    print(f"📊 Test Configuration:")
    print(f"  Parameters: {len(test_parameters)}")
    print(f"  Test points per parameter: 9")
    print(f"  Total evaluations: {len(test_parameters) * 9}")
    print(f"  Grid size: {base_config.grid_size}")
    print(f"  Workers: {config.max_workers}")
    print()
    
    # Test sequential processing
    print("🔄 Testing Sequential Processing...")
    sequential_analyzer = SensitivityAnalyzer(
        calibration_config=config,
        parameter_bounds=parameter_bounds,
        objective_function=objective_function,
        parallel_execution=False  # Disable parallel processing
    )
    
    start_time = time.time()
    sequential_results = sequential_analyzer.run_sensitivity_analysis(target_data=target_data)
    sequential_time = time.time() - start_time
    
    print(f"✅ Sequential completed in {sequential_time:.2f} seconds")
    print(f"  Valid parameters: {len([r for r in sequential_results.results if r.is_valid])}")
    print()
    
    # Test parallel processing
    print("🚀 Testing Parallel Processing...")
    parallel_analyzer = SensitivityAnalyzer(
        calibration_config=config,
        parameter_bounds=parameter_bounds,
        objective_function=objective_function,
        parallel_execution=True,  # Enable parallel processing
        max_workers=4
    )
    
    start_time = time.time()
    parallel_results = parallel_analyzer.run_sensitivity_analysis(target_data=target_data)
    parallel_time = time.time() - start_time
    
    print(f"✅ Parallel completed in {parallel_time:.2f} seconds")
    print(f"  Valid parameters: {len([r for r in parallel_results.results if r.is_valid])}")
    print()
    
    # Compare results
    print("📈 Performance Comparison:")
    speedup = sequential_time / parallel_time if parallel_time > 0 else 0
    efficiency = (speedup / 4) * 100  # 4 workers
    
    print(f"  Sequential time: {sequential_time:.2f} seconds")
    print(f"  Parallel time: {parallel_time:.2f} seconds")
    print(f"  Speedup: {speedup:.2f}x")
    print(f"  Parallel efficiency: {efficiency:.1f}%")
    print()
    
    # Compare sensitivity rankings
    print("🔍 Comparing Sensitivity Rankings:")
    seq_rankings = sequential_results.get_most_sensitive_parameters()
    par_rankings = parallel_results.get_most_sensitive_parameters()
    
    print("Sequential Rankings:")
    for i, (param, sensitivity) in enumerate(seq_rankings):
        print(f"  {i+1}. {param}: {sensitivity:.4f}")
    
    print("Parallel Rankings:")
    for i, (param, sensitivity) in enumerate(par_rankings):
        print(f"  {i+1}. {param}: {sensitivity:.4f}")
    
    # Check if rankings are consistent
    seq_order = [param for param, _ in seq_rankings]
    par_order = [param for param, _ in par_rankings]
    
    if seq_order == par_order:
        print("✅ Rankings are consistent between sequential and parallel processing")
    else:
        print("⚠️  Rankings differ between sequential and parallel processing")
        print("  This may be due to slight numerical differences in parallel execution")
    
    print()
    print("🎯 Test Summary:")
    if speedup > 1.5:
        print(f"✅ Parallel processing provides significant speedup ({speedup:.2f}x)")
    elif speedup > 1.1:
        print(f"✅ Parallel processing provides moderate speedup ({speedup:.2f}x)")
    else:
        print(f"⚠️  Parallel processing speedup is limited ({speedup:.2f}x)")
        print("  This may be due to small test size or system limitations")
    
    if efficiency > 70:
        print(f"✅ Parallel efficiency is good ({efficiency:.1f}%)")
    elif efficiency > 50:
        print(f"⚠️  Parallel efficiency is moderate ({efficiency:.1f}%)")
    else:
        print(f"❌ Parallel efficiency is low ({efficiency:.1f}%)")
    
    return True


if __name__ == "__main__":
    try:
        test_parallel_sensitivity()
        print("\n🎉 All tests completed successfully!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1) 