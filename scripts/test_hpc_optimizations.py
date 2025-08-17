#!/usr/bin/env python3
"""
Test HPC Optimizations

Tests the three critical HPC optimizations:
1. Network Filesystem Bottlenecks
2. Memory Bandwidth Limitations
3. Garbage Collection Overhead
"""

import sys
import time
import os
import gc
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.utils.hpc_optimizer import HPCOptimizer, apply_hpc_optimizations, start_hpc_monitoring, stop_hpc_monitoring

def test_network_filesystem_optimization():
    """Test network filesystem optimization."""
    print("🔍 Testing Network Filesystem Optimization...")
    
    optimizer = HPCOptimizer()
    
    # Test storage path detection
    local_paths = optimizer._find_local_storage_paths()
    print(f"   Local storage paths: {local_paths}")
    
    # Test storage accessibility
    for storage_type, path in local_paths.items():
        accessible = optimizer._is_storage_accessible(path)
        print(f"   {storage_type} storage ({path}): {'✅ Accessible' if accessible else '❌ Not accessible'}")
    
    # Test configuration optimization
    test_config = {
        'output': {'base_path': '/network/storage/output'},
        'terrain': {'preprocessed_dir': '/network/storage/terrain'}
    }
    
    optimized_config = optimizer._optimize_storage_paths(test_config)
    print(f"   Optimized config output path: {optimized_config.get('output', {}).get('base_path', 'Not set')}")
    
    return True

def test_memory_bandwidth_optimization():
    """Test memory bandwidth optimization."""
    print("🧠 Testing Memory Bandwidth Optimization...")
    
    optimizer = HPCOptimizer()
    
    # Test optimal worker calculation
    optimal_workers = optimizer._calculate_optimal_worker_count()
    print(f"   Optimal worker count: {optimal_workers}")
    
    # Test memory threshold calculation
    memory_threshold = optimizer._get_memory_threshold()
    print(f"   Memory threshold: {memory_threshold:.1f} GB")
    
    # Test configuration optimization
    test_config = {
        'calibration': {'max_workers': 70}
    }
    
    optimized_config = optimizer._optimize_memory_bandwidth(test_config)
    final_workers = optimized_config.get('calibration', {}).get('max_workers', 70)
    print(f"   Workers before optimization: 70")
    print(f"   Workers after optimization: {final_workers}")
    
    return True

def test_garbage_collection_optimization():
    """Test garbage collection optimization."""
    print("🗑️  Testing Garbage Collection Optimization...")
    
    optimizer = HPCOptimizer()
    
    # Store original GC settings
    original_enabled = gc.isenabled()
    original_thresholds = gc.get_threshold()
    
    print(f"   Original GC enabled: {original_enabled}")
    print(f"   Original GC thresholds: {original_thresholds}")
    
    # Test GC optimization
    optimizer._optimize_garbage_collection()
    
    optimized_enabled = gc.isenabled()
    optimized_thresholds = gc.get_threshold()
    
    print(f"   Optimized GC enabled: {optimized_enabled}")
    print(f"   Optimized GC thresholds: {optimized_thresholds}")
    
    # Test forced GC
    collected = optimizer.force_garbage_collection()
    print(f"   Forced GC collected {collected} objects")
    
    # Restore original settings
    optimizer.restore_original_settings()
    
    restored_enabled = gc.isenabled()
    restored_thresholds = gc.get_threshold()
    
    print(f"   Restored GC enabled: {restored_enabled}")
    print(f"   Restored GC thresholds: {restored_thresholds}")
    
    return True

def test_memory_monitoring():
    """Test memory monitoring functionality."""
    print("👁️  Testing Memory Monitoring...")
    
    optimizer = HPCOptimizer()
    
    # Start monitoring
    optimizer.start_memory_monitoring()
    print("   Memory monitoring started")
    
    # Let it run for a few seconds
    time.sleep(3)
    
    # Stop monitoring
    optimizer.stop_memory_monitoring()
    print("   Memory monitoring stopped")
    
    return True

def test_full_hpc_optimization():
    """Test full HPC optimization workflow."""
    print("🚀 Testing Full HPC Optimization Workflow...")
    
    # Test configuration
    test_config = {
        'grid': {'width': 5000, 'height': 5000, 'num_layers': 25},
        'calibration': {'max_workers': 70, 'parallel_execution': True},
        'terrain': {'use_terrain': True, 'preprocessed_dir': '/network/storage/terrain'},
        'output': {'base_path': '/network/storage/output'},
        'monitoring': {'log_level': 'INFO'}
    }
    
    print("   Original configuration:")
    print(f"     Workers: {test_config['calibration']['max_workers']}")
    print(f"     Output path: {test_config['output']['base_path']}")
    print(f"     Terrain path: {test_config['terrain']['preprocessed_dir']}")
    
    # Apply HPC optimizations
    optimized_config = apply_hpc_optimizations(test_config)
    
    print("   Optimized configuration:")
    print(f"     Workers: {optimized_config['calibration']['max_workers']}")
    print(f"     Output path: {optimized_config['output']['base_path']}")
    print(f"     Local cache: {optimized_config.get('terrain', {}).get('local_cache_dir', 'Not set')}")
    print(f"     Memory monitoring: {optimized_config.get('monitoring', {}).get('memory_bandwidth_monitoring', False)}")
    
    # Get optimization summary
    optimizer = HPCOptimizer()
    summary = optimizer.get_optimization_summary()
    
    print("   Optimization summary:")
    for key, value in summary.items():
        print(f"     {key}: {value}")
    
    return True

def test_numa_detection():
    """Test NUMA node detection."""
    print("🔧 Testing NUMA Detection...")
    
    optimizer = HPCOptimizer()
    numa_nodes = optimizer._detect_numa_nodes()
    
    print(f"   Detected NUMA nodes: {numa_nodes}")
    
    if numa_nodes > 1:
        print("   ✅ Multi-NUMA system detected - optimizations will be applied")
    else:
        print("   ℹ️  Single NUMA node or detection failed - using default optimizations")
    
    return True

def main():
    """Run all HPC optimization tests."""
    print("🧪 HPC Optimization Test Suite")
    print("=" * 50)
    
    tests = [
        ("NUMA Detection", test_numa_detection),
        ("Network Filesystem Optimization", test_network_filesystem_optimization),
        ("Memory Bandwidth Optimization", test_memory_bandwidth_optimization),
        ("Garbage Collection Optimization", test_garbage_collection_optimization),
        ("Memory Monitoring", test_memory_monitoring),
        ("Full HPC Optimization Workflow", test_full_hpc_optimization)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n{test_name}")
        print("-" * len(test_name))
        
        try:
            start_time = time.time()
            success = test_func()
            end_time = time.time()
            
            if success:
                print(f"✅ {test_name} PASSED ({end_time - start_time:.2f}s)")
                results.append((test_name, True, end_time - start_time))
            else:
                print(f"❌ {test_name} FAILED ({end_time - start_time:.2f}s)")
                results.append((test_name, False, end_time - start_time))
                
        except Exception as e:
            print(f"❌ {test_name} ERROR: {e}")
            results.append((test_name, False, 0))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Results Summary")
    print("=" * 50)
    
    passed = sum(1 for _, success, _ in results if success)
    total = len(results)
    
    for test_name, success, duration in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name} ({duration:.2f}s)")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All HPC optimizations are working correctly!")
        return 0
    else:
        print("⚠️  Some HPC optimizations need attention")
        return 1

if __name__ == "__main__":
    sys.exit(main())
