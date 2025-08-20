#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Performance Optimization Test Script

This script tests the performance optimizations implemented for the fire simulation engine
and forest model. It compares optimized vs standard implementations on progressively
larger grid sizes to validate performance improvements.

Key Tests:
1. Small grid comparison (baseline)
2. Medium grid comparison (where optimizations start to matter)
3. Large grid comparison (where optimizations are critical)
4. Performance metrics analysis
5. Memory usage comparison

Author: Forest Fire Simulation Team
Date: 2025
Version: 1.0
"""

import os
import sys
import time
import logging
import psutil
from pathlib import Path
from typing import Dict, Any, Tuple

# Add project root to path
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

try:
    # Import optimization factory
    from src.core.optimization_factory import (
        create_optimized_fire_simulation_engine,
        create_optimized_forest_model,
        create_simulation_components,
        get_optimization_status,
        log_optimization_status,
        OptimizationConfig,
        set_optimization_config
    )
    
    # Import original components for comparison
    from src.core.fire_simulation_engine import FireSimulationEngine
    from src.core.forest_model import MemoryOptimizedForestModel
    from src.config.config_tools import ModelConfig
    from src.utils.logging_utils import get_logger
    
except ImportError as e:
    print(f"❌ Error importing modules: {e}")
    sys.exit(1)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = get_logger(__name__)


def get_memory_usage() -> float:
    """Get current memory usage in GB."""
    try:
        process = psutil.Process()
        return process.memory_info().rss / (1024**3)
    except:
        return 0.0


def create_test_config(grid_size: Tuple[int, int], num_layers: int) -> ModelConfig:
    """Create test configuration for given grid size."""
    grid_width, grid_height = grid_size
    
    config_dict = {
        'grid_size': [grid_width, grid_height],
        'num_layers': num_layers,
        'model_resolution': 100.0,  # 100m resolution
        'layer_height': 2.0,
        'max_steps': 10,  # Short simulation for testing
        'use_terrain': False,  # Disable terrain for simplicity
        'use_preprocessed_terrain': False,
        'memory_optimization_level': 2,
        'use_sparse_storage': True,
        'simulation_type': 'memory_optimized',
        'ignition_points': [{"x": grid_width // 2, "y": grid_height // 2, "layer": 1}]
    }
    
    return ModelConfig.from_dict(config_dict)


def run_simulation_test(engine, test_name: str, max_steps: int = 5) -> Dict[str, Any]:
    """
    Run a short simulation test and collect performance metrics.
    
    Args:
        engine: Fire simulation engine
        test_name: Name of the test
        max_steps: Maximum simulation steps
        
    Returns:
        Dictionary with performance metrics
    """
    logger.info(f"🔥 Running {test_name}...")
    
    start_memory = get_memory_usage()
    start_time = time.time()
    
    try:
        # Initialize engine if needed
        if hasattr(engine, 'forest_model') and engine.forest_model:
            total_cells = (engine.forest_model.width * 
                          engine.forest_model.height * 
                          engine.forest_model.num_layers)
        else:
            total_cells = 0
        
        # Run short simulation
        results = engine.run_simulation(max_steps=max_steps, stop_when_fire_extinguished=False)
        
        end_time = time.time()
        end_memory = get_memory_usage()
        
        # Collect performance metrics
        metrics = {
            'test_name': test_name,
            'total_cells': total_cells,
            'simulation_time': end_time - start_time,
            'memory_start': start_memory,
            'memory_end': end_memory,
            'memory_delta': end_memory - start_memory,
            'steps_completed': results.get('steps', 0) if isinstance(results, dict) else max_steps,
            'active_cells_final': len(engine.active_cells) if hasattr(engine, 'active_cells') else 0,
            'success': True
        }
        
        # Add optimization metrics if available
        if hasattr(engine, 'get_performance_metrics'):
            opt_metrics = engine.get_performance_metrics()
            metrics['optimization_metrics'] = opt_metrics
        
        logger.info(f"✅ {test_name} completed in {metrics['simulation_time']:.2f}s")
        logger.info(f"   Memory: {metrics['memory_start']:.2f}GB → {metrics['memory_end']:.2f}GB (Δ{metrics['memory_delta']:.2f}GB)")
        
        return metrics
    
    except Exception as e:
        end_time = time.time()
        end_memory = get_memory_usage()
        
        logger.error(f"❌ {test_name} failed: {e}")
        
        return {
            'test_name': test_name,
            'total_cells': total_cells if 'total_cells' in locals() else 0,
            'simulation_time': end_time - start_time,
            'memory_start': start_memory,
            'memory_end': end_memory,
            'memory_delta': end_memory - start_memory,
            'steps_completed': 0,
            'active_cells_final': 0,
            'success': False,
            'error': str(e)
        }


def test_grid_size(grid_size: Tuple[int, int], num_layers: int, test_name: str) -> Dict[str, Any]:
    """
    Test both optimized and standard implementations for a given grid size.
    
    Args:
        grid_size: (width, height) tuple
        num_layers: Number of layers
        test_name: Name of the test
        
    Returns:
        Comparison results
    """
    grid_width, grid_height = grid_size
    total_cells = grid_width * grid_height * num_layers
    
    logger.info(f"\n🧪 {test_name}")
    logger.info(f"=" * 50)
    logger.info(f"Grid: {grid_width} × {grid_height} × {num_layers} = {total_cells:,} cells")
    
    # Create configuration
    config = create_test_config(grid_size, num_layers)
    
    results = {
        'test_name': test_name,
        'grid_size': grid_size,
        'num_layers': num_layers,
        'total_cells': total_cells,
        'optimized': None,
        'standard': None,
        'comparison': None
    }
    
    try:
        # Test optimized implementation
        logger.info("\n🚀 Testing Optimized Implementation...")
        optimized_forest_model = create_optimized_forest_model(
            grid_size=grid_size,
            num_layers=num_layers,
            config=config,
            force_optimization=True
        )
        optimized_engine = create_optimized_fire_simulation_engine(
            forest_model=optimized_forest_model,
            config=config,
            force_optimization=True
        )
        
        results['optimized'] = run_simulation_test(optimized_engine, f"{test_name} (Optimized)")
        
        # Clean up
        if hasattr(optimized_engine, 'clear_optimization_caches'):
            optimized_engine.clear_optimization_caches()
        del optimized_engine, optimized_forest_model
        
    except Exception as e:
        logger.error(f"❌ Optimized test failed: {e}")
        results['optimized'] = {'success': False, 'error': str(e)}
    
    try:
        # Test standard implementation
        logger.info("\n📊 Testing Standard Implementation...")
        standard_forest_model = MemoryOptimizedForestModel(
            grid_size=grid_size,
            num_layers=num_layers,
            config=config
        )
        standard_engine = FireSimulationEngine(
            forest_model=standard_forest_model,
            config=config
        )
        
        results['standard'] = run_simulation_test(standard_engine, f"{test_name} (Standard)")
        
        # Clean up
        del standard_engine, standard_forest_model
        
    except Exception as e:
        logger.error(f"❌ Standard test failed: {e}")
        results['standard'] = {'success': False, 'error': str(e)}
    
    # Compare results
    if results['optimized'] and results['standard']:
        if results['optimized']['success'] and results['standard']['success']:
            opt_time = results['optimized']['simulation_time']
            std_time = results['standard']['simulation_time']
            
            speedup = std_time / opt_time if opt_time > 0 else 0
            
            opt_memory = results['optimized']['memory_delta']
            std_memory = results['standard']['memory_delta']
            memory_improvement = std_memory - opt_memory
            
            results['comparison'] = {
                'speedup': speedup,
                'memory_improvement_gb': memory_improvement,
                'optimized_faster': speedup > 1.0,
                'optimized_more_efficient': memory_improvement > 0
            }
            
            logger.info(f"\n📈 Performance Comparison:")
            logger.info(f"   Speedup: {speedup:.2f}x {'✅' if speedup > 1.0 else '❌'}")
            logger.info(f"   Memory improvement: {memory_improvement:.2f}GB {'✅' if memory_improvement > 0 else '❌'}")
        else:
            logger.warning("⚠️  Cannot compare - one or both tests failed")
    
    return results


def main():
    """Run performance optimization tests."""
    
    print("🚀 PERFORMANCE OPTIMIZATION TEST SUITE")
    print("=" * 60)
    print("Testing optimized vs standard implementations")
    print("on progressively larger grid sizes")
    
    # Configure optimizations
    opt_config = OptimizationConfig()
    opt_config.auto_optimize_threshold = 100_000  # Lower threshold for testing
    opt_config.enable_performance_logging = True
    opt_config.log_optimization_decisions = True
    set_optimization_config(opt_config)
    
    # Log optimization status
    log_optimization_status()
    
    # Test cases (progressively larger grids)
    test_cases = [
        ((50, 50), 5, "Small Grid Test"),      # 12.5K cells
        ((100, 100), 8, "Medium Grid Test"),   # 80K cells
        ((200, 200), 10, "Large Grid Test"),   # 400K cells
        ((300, 300), 12, "Very Large Grid Test"),  # 1.08M cells
    ]
    
    # Check available memory
    available_memory_gb = psutil.virtual_memory().available / (1024**3)
    logger.info(f"💾 Available memory: {available_memory_gb:.1f}GB")
    
    if available_memory_gb < 8:
        logger.warning("⚠️  Low available memory - skipping largest test cases")
        test_cases = test_cases[:3]
    
    all_results = []
    
    try:
        for grid_size, num_layers, test_name in test_cases:
            total_cells = grid_size[0] * grid_size[1] * num_layers
            estimated_memory = total_cells * 8 / (1024**3)  # Rough estimate
            
            if estimated_memory > available_memory_gb * 0.5:
                logger.warning(f"⚠️  Skipping {test_name} - estimated memory ({estimated_memory:.1f}GB) too high")
                continue
            
            result = test_grid_size(grid_size, num_layers, test_name)
            all_results.append(result)
            
            # Force garbage collection between tests
            import gc
            gc.collect()
            
            # Brief pause to let system recover
            time.sleep(2)
    
    except KeyboardInterrupt:
        logger.info("\n⚠️  Test suite interrupted by user")
    
    except Exception as e:
        logger.error(f"\n❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Summary
    print("\n" + "=" * 60)
    print("🎯 PERFORMANCE TEST SUMMARY")
    print("=" * 60)
    
    successful_tests = [r for r in all_results if r.get('comparison')]
    
    if successful_tests:
        speedups = [r['comparison']['speedup'] for r in successful_tests]
        memory_improvements = [r['comparison']['memory_improvement_gb'] for r in successful_tests]
        
        avg_speedup = sum(speedups) / len(speedups)
        avg_memory_improvement = sum(memory_improvements) / len(memory_improvements)
        
        print(f"✅ Successful tests: {len(successful_tests)}/{len(all_results)}")
        print(f"📈 Average speedup: {avg_speedup:.2f}x")
        print(f"💾 Average memory improvement: {avg_memory_improvement:.2f}GB")
        
        best_speedup = max(speedups)
        best_memory = max(memory_improvements)
        
        print(f"🏆 Best speedup: {best_speedup:.2f}x")
        print(f"🏆 Best memory improvement: {best_memory:.2f}GB")
        
        # Detailed results
        print(f"\n📊 Detailed Results:")
        for result in successful_tests:
            comp = result['comparison']
            print(f"   {result['test_name']}: {comp['speedup']:.2f}x speedup, {comp['memory_improvement_gb']:.2f}GB memory saved")
    
    else:
        print("❌ No successful comparison tests completed")
        print("   Check logs for error details")
    
    print("\n✅ Performance optimization testing completed!")


if __name__ == "__main__":
    main()
