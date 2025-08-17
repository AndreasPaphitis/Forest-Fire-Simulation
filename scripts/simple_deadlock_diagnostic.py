#!/usr/bin/env python3
"""
Simple Deadlock Diagnostic for Forest Fire Calibration

This script tests the most likely deadlock scenarios that could cause
the 5+ minute hang during calibration, focusing on the key issues.
"""

import time
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_system_resources():
    """Test system resources and limits."""
    print("🔍 Testing System Resources...")
    
    try:
        # Check memory (if psutil available)
        try:
            import psutil
            memory = psutil.virtual_memory()
            print(f"   📊 Memory: {memory.total / (1024**3):.1f}GB total, {memory.available / (1024**3):.1f}GB available")
            
            if memory.available < 1.0:
                print("   ⚠️  Low memory available - may cause deadlocks")
                return False
        except ImportError:
            print("   ℹ️  psutil not available - skipping memory check")
        
        # Check CPU
        try:
            import multiprocessing
            cpu_count = multiprocessing.cpu_count()
            print(f"   📊 CPU: {cpu_count} cores")
            
            if cpu_count < 4:
                print("   ⚠️  Low CPU count - may cause resource contention")
                return False
        except:
            print("   ℹ️  Could not check CPU count")
        
        # Check shared memory (Linux/Unix only)
        if os.path.exists("/dev/shm"):
            import os
            shm_stats = os.statvfs("/dev/shm")
            shm_size_gb = (shm_stats.f_blocks * shm_stats.f_frsize) / (1024**3)
            print(f"   📊 Shared memory: {shm_size_gb:.1f}GB available")
            
            if shm_size_gb < 1.0:
                print("   ⚠️  Low shared memory available - may cause deadlocks")
                return False
        else:
            print("   ℹ️  Shared memory not available (Windows)")
        
        print("   ✅ System resources look good")
        return True
        
    except Exception as e:
        print(f"   ❌ System resource test failed: {e}")
        return False

def test_shared_memory_connection():
    """Test shared memory connection without deadlock."""
    print("🔍 Testing Shared Memory Connection...")
    
    try:
        from multiprocessing import shared_memory
        import numpy as np
        
        # Create a small test shared memory block
        test_data = np.array([1, 2, 3, 4, 5], dtype=np.int32)
        shm = shared_memory.SharedMemory(create=True, size=test_data.nbytes, name="test_shared_memory")
        
        # Copy data to shared memory
        shared_array = np.ndarray(test_data.shape, dtype=test_data.dtype, buffer=shm.buf)
        shared_array[:] = test_data[:]
        
        print(f"   ✅ Created test shared memory: {shm.name}")
        
        # Test connection with timeout
        start_time = time.time()
        try:
            # Try to connect to the shared memory
            test_shm = shared_memory.SharedMemory(name=shm.name)
            test_array = np.ndarray(test_data.shape, dtype=test_data.dtype, buffer=test_shm.buf)
            
            connection_time = time.time() - start_time
            print(f"   ✅ Shared memory connection successful in {connection_time:.3f} seconds")
            
            # Clean up
            test_shm.close()
            shm.close()
            shm.unlink()
            
            return True
            
        except Exception as e:
            print(f"   ❌ Shared memory connection failed: {e}")
            shm.close()
            shm.unlink()
            return False
            
    except Exception as e:
        print(f"   ❌ Shared memory test failed: {e}")
        return False

def test_forest_model_creation():
    """Test forest model creation without shared terrain."""
    print("🔍 Testing Forest Model Creation...")
    
    try:
        from src.core.forest_model import create_forest_model
        from src.config.config_tools import ModelConfig
        
        # Create minimal config without shared terrain
        config = ModelConfig(
            grid_size=[100, 100],
            num_layers=5,
            use_terrain=False,
            shared_terrain_info=None
        )
        
        start_time = time.time()
        
        forest_model = create_forest_model(
            model_type='memory_optimized',
            config=config,
            grid_size=config.grid_size,
            num_layers=config.num_layers
        )
        
        creation_time = time.time() - start_time
        print(f"   ✅ Forest model creation successful in {creation_time:.3f} seconds")
        
        # Clean up
        del forest_model
        
        return True
        
    except Exception as e:
        print(f"   ❌ Forest model creation test failed: {e}")
        return False

def test_shared_terrain_loading():
    """Test shared terrain loading with timeout."""
    print("🔍 Testing Shared Terrain Loading...")
    
    try:
        from src.utils.shared_terrain import load_shared_terrain_data
        
        # Create fake shared terrain info
        fake_shared_info = {
            'is_loaded': False,
            'shared_names': {},
            'shapes': {},
            'dtypes': {}
        }
        
        start_time = time.time()
        
        # This should return empty dict quickly
        terrain_data = load_shared_terrain_data(fake_shared_info)
        
        loading_time = time.time() - start_time
        print(f"   ✅ Shared terrain loading test successful in {loading_time:.3f} seconds")
        print(f"   📊 Result: {len(terrain_data)} terrain arrays loaded")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Shared terrain loading test failed: {e}")
        return False

def test_concurrent_access():
    """Test concurrent access scenarios."""
    print("🔍 Testing Concurrent Access...")
    
    try:
        import threading
        import queue
        
        # Test thread-safe queue operations
        test_queue = queue.Queue(maxsize=10)
        results = []
        errors = []
        
        def producer():
            try:
                for i in range(20):
                    test_queue.put(i, timeout=5)
                    time.sleep(0.01)
            except Exception as e:
                errors.append(f"Producer error: {e}")
        
        def consumer():
            try:
                for i in range(20):
                    item = test_queue.get(timeout=5)
                    results.append(item)
                    time.sleep(0.01)
            except Exception as e:
                errors.append(f"Consumer error: {e}")
        
        start_time = time.time()
        producer_thread = threading.Thread(target=producer)
        consumer_thread = threading.Thread(target=consumer)
        
        producer_thread.start()
        consumer_thread.start()
        
        producer_thread.join(timeout=10)
        consumer_thread.join(timeout=10)
        
        queue_time = time.time() - start_time
        print(f"   ✅ Queue operations: {queue_time:.3f}s, {len(results)} items processed")
        
        if errors:
            print(f"   ⚠️  Queue errors: {errors}")
            return False
        
        print("   ✅ Concurrent access test successful")
        return True
        
    except Exception as e:
        print(f"   ❌ Concurrent access test failed: {e}")
        return False

def main():
    """Run simple deadlock diagnostic."""
    print("🚨 SIMPLE DEADLOCK DIAGNOSTIC - Forest Fire Calibration")
    print("=" * 60)
    
    tests = [
        ("System Resources", test_system_resources),
        ("Shared Memory Connection", test_shared_memory_connection),
        ("Forest Model Creation", test_forest_model_creation),
        ("Shared Terrain Loading", test_shared_terrain_loading),
        ("Concurrent Access", test_concurrent_access),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            success = test_func()
            results[test_name] = success
        except Exception as e:
            print(f"❌ {test_name} crashed: {e}")
            results[test_name] = False
    
    # Summary
    print(f"\n{'='*60}")
    print("📊 DIAGNOSTIC SUMMARY")
    print("=" * 60)
    
    for test_name, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
    
    passed = sum(1 for success in results.values() if success)
    failed = len(results) - passed
    
    print(f"\n📈 SUMMARY:")
    print(f"   Total tests: {len(results)}")
    print(f"   Passed: {passed}")
    print(f"   Failed: {failed}")
    
    failed_tests = [name for name, success in results.items() if not success]
    
    if failed_tests:
        print(f"\n🚨 ISSUES DETECTED:")
        for test in failed_tests:
            print(f"   - {test}")
        
        print(f"\n💡 RECOMMENDATIONS:")
        if "System Resources" in failed_tests:
            print("   - Check available memory and CPU resources")
            print("   - Consider reducing worker count")
        if "Shared Memory Connection" in failed_tests:
            print("   - Shared memory may be corrupted or full")
            print("   - Try: sudo rm -rf /dev/shm/* (Linux)")
        if "Forest Model Creation" in failed_tests:
            print("   - Forest model initialization may be hanging")
            print("   - Use emergency configuration")
        if "Shared Terrain Loading" in failed_tests:
            print("   - Shared terrain loading may be problematic")
            print("   - Disable shared terrain: shared_terrain_info=null")
        if "Concurrent Access" in failed_tests:
            print("   - Check for race conditions")
            print("   - Reduce concurrency level")
    else:
        print(f"\n✅ ALL TESTS PASSED - System appears healthy")
        print(f"   The deadlock may be specific to the calibration workload")
        print(f"   Consider using the emergency configuration for testing")

if __name__ == "__main__":
    main()
