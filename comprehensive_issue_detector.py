#!/usr/bin/env python3
"""
Comprehensive Issue Detector for Forest Fire Simulation Framework

This script systematically tests for potential issues that could go wrong:
1. Memory leaks and excessive memory usage
2. Deadlocks and hanging processes
3. Exception handling and error recovery
4. Resource cleanup and file handling
5. Parameter validation and edge cases
6. Multiprocessing issues
7. Timeout and performance issues
"""

import time
import gc
import psutil
import threading
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor, TimeoutError
import traceback
import sys
import os

from src.core.calibration.grid_search import evaluate_worker_function
from src.config.config_tools import ModelConfig

# Standalone worker function for multiprocessing test
def standalone_worker_function():
    """Standalone worker function for multiprocessing test."""
    try:
        config = ModelConfig(
            grid_size=(10, 10),
            num_layers=2,
            max_steps=3,
            simulation_type='memory_optimized',
            spread_probability=0.8,
            fuel_consumption_rate=0.01,
            ignition_threshold=0.1
        )
        
        params = {
            'spread_probability': 0.8,
            'fuel_consumption_rate': 0.01,
            'ignition_threshold': 0.1
        }
        
        result = evaluate_worker_function(
            parameter_values=params,
            target_data=None,
            config_dict=config.__dict__,
            objective_function_name="SpatialSimilarityObjective"
        )
        return result['is_valid']
    except Exception as e:
        return False

def test_memory_leaks():
    """Test for memory leaks during simulation."""
    print("🔍 Testing for memory leaks...")
    
    # Get initial memory
    process = psutil.Process()
    initial_memory = process.memory_info().rss / 1024 / 1024  # MB
    
    config = ModelConfig(
        grid_size=(30, 30),
        num_layers=3,
        max_steps=10,
        simulation_type='memory_optimized',
        spread_probability=0.8,
        fuel_consumption_rate=0.01,
        ignition_threshold=0.1,
        stop_when_fire_extinguished=False
    )
    
    params = {
        'spread_probability': 0.8,
        'fuel_consumption_rate': 0.01,
        'ignition_threshold': 0.1
    }
    
    # Run multiple simulations to check for memory accumulation
    memory_readings = []
    
    for i in range(5):
        try:
            # Force garbage collection before each run
            gc.collect()
            
            # Run simulation
            result = evaluate_worker_function(
                parameter_values=params,
                target_data=None,
                config_dict=config.__dict__,
                objective_function_name="SpatialSimilarityObjective"
            )
            
            # Check memory after simulation
            current_memory = process.memory_info().rss / 1024 / 1024
            memory_readings.append(current_memory)
            
            print(f"  Run {i+1}: {current_memory:.1f} MB")
            
            if not result['is_valid']:
                print(f"  ❌ Run {i+1} failed: {result.get('error_message', 'Unknown error')}")
                
        except Exception as e:
            print(f"  ❌ Run {i+1} exception: {e}")
            memory_readings.append(process.memory_info().rss / 1024 / 1024)
    
    # Analyze memory growth
    if len(memory_readings) >= 2:
        memory_growth = memory_readings[-1] - memory_readings[0]
        growth_rate = memory_growth / len(memory_readings)
        
        print(f"  📊 Memory analysis:")
        print(f"    Initial: {memory_readings[0]:.1f} MB")
        print(f"    Final: {memory_readings[-1]:.1f} MB")
        print(f"    Total growth: {memory_growth:.1f} MB")
        print(f"    Growth per run: {growth_rate:.1f} MB")
        
        if memory_growth > 50:  # More than 50MB growth
            print(f"  ⚠️  Potential memory leak detected!")
            return False
        else:
            print(f"  ✅ No significant memory leak detected")
            return True
    else:
        print(f"  ❌ Insufficient data for memory analysis")
        return False

def test_deadlock_scenarios():
    """Test for potential deadlock scenarios."""
    print("\n🔍 Testing for deadlock scenarios...")
    
    config = ModelConfig(
        grid_size=(20, 20),
        num_layers=3,
        max_steps=5,
        simulation_type='memory_optimized',
        spread_probability=0.9,
        fuel_consumption_rate=0.001,  # Very low to prevent early termination
        ignition_threshold=0.001,
        stop_when_fire_extinguished=False
    )
    
    params = {
        'spread_probability': 0.9,
        'fuel_consumption_rate': 0.001,
        'ignition_threshold': 0.001
    }
    
    # Test with timeout
    def run_with_timeout():
        try:
            result = evaluate_worker_function(
                parameter_values=params,
                target_data=None,
                config_dict=config.__dict__,
                objective_function_name="SpatialSimilarityObjective"
            )
            return result
        except Exception as e:
            return {'error': str(e)}
    
    # Run in thread with timeout
    thread = threading.Thread(target=run_with_timeout)
    thread.daemon = True
    thread.start()
    
    # Wait for completion with timeout
    thread.join(timeout=30.0)  # 30 second timeout
    
    if thread.is_alive():
        print(f"  ❌ Potential deadlock detected - simulation did not complete within 30 seconds")
        return False
    else:
        print(f"  ✅ No deadlock detected - simulation completed within timeout")
        return True

def test_exception_handling():
    """Test exception handling with invalid parameters."""
    print("\n🔍 Testing exception handling...")
    
    config = ModelConfig(
        grid_size=(10, 10),
        num_layers=2,
        max_steps=5,
        simulation_type='memory_optimized'
    )
    
    # Test with invalid parameters
    invalid_params = [
        {'spread_probability': -1.0},  # Negative probability
        {'spread_probability': 2.0},   # Probability > 1
        {'fuel_consumption_rate': -0.1},  # Negative consumption
        {'ignition_threshold': 2.0},   # Threshold > 1
        {'spread_probability': 'invalid'},  # Wrong type
    ]
    
    exception_handled = 0
    
    for i, invalid_param in enumerate(invalid_params):
        try:
            result = evaluate_worker_function(
                parameter_values=invalid_param,
                target_data=None,
                config_dict=config.__dict__,
                objective_function_name="SpatialSimilarityObjective"
            )
            
            # Check if error was properly handled
            if not result['is_valid'] and 'error_message' in result:
                print(f"  ✅ Invalid param {i+1} handled gracefully: {result['error_message'][:50]}...")
                exception_handled += 1
            else:
                print(f"  ❌ Invalid param {i+1} not properly handled")
                
        except Exception as e:
            print(f"  ✅ Invalid param {i+1} exception caught: {type(e).__name__}")
            exception_handled += 1
    
    success_rate = exception_handled / len(invalid_params)
    print(f"  📊 Exception handling success rate: {success_rate:.1%}")
    
    return success_rate >= 0.8  # At least 80% success rate

def test_resource_cleanup():
    """Test resource cleanup after simulation."""
    print("\n🔍 Testing resource cleanup...")
    
    config = ModelConfig(
        grid_size=(15, 15),
        num_layers=3,
        max_steps=5,
        simulation_type='memory_optimized',
        spread_probability=0.8,
        fuel_consumption_rate=0.01,
        ignition_threshold=0.1
    )
    
    params = {
        'spread_probability': 0.8,
        'fuel_consumption_rate': 0.01,
        'ignition_threshold': 0.1
    }
    
    # Get initial file handles
    process = psutil.Process()
    initial_files = len(process.open_files())
    
    # Run simulation
    try:
        result = evaluate_worker_function(
            parameter_values=params,
            target_data=None,
            config_dict=config.__dict__,
            objective_function_name="SpatialSimilarityObjective"
        )
        
        # Force garbage collection
        gc.collect()
        
        # Check file handles after simulation
        final_files = len(process.open_files())
        file_leak = final_files - initial_files
        
        print(f"  📊 File handle analysis:")
        print(f"    Initial handles: {initial_files}")
        print(f"    Final handles: {final_files}")
        print(f"    Leaked handles: {file_leak}")
        
        if file_leak > 5:  # More than 5 leaked handles
            print(f"  ⚠️  Potential file handle leak detected!")
            return False
        else:
            print(f"  ✅ No significant file handle leak detected")
            return True
            
    except Exception as e:
        print(f"  ❌ Resource cleanup test failed: {e}")
        return False

def test_multiprocessing_issues():
    """Test multiprocessing scenarios."""
    print("\n🔍 Testing multiprocessing issues...")
    
    # Test with ProcessPoolExecutor using standalone function
    try:
        with ProcessPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(standalone_worker_function) for _ in range(4)]
            
            # Wait for completion with timeout
            results = []
            for future in futures:
                try:
                    result = future.result(timeout=30.0)
                    results.append(result)
                except TimeoutError:
                    print(f"  ❌ Multiprocessing timeout detected")
                    return False
                except Exception as e:
                    print(f"  ❌ Multiprocessing error: {e}")
                    return False
            
            success_count = sum(results)
            success_rate = success_count / len(results)
            
            print(f"  📊 Multiprocessing results:")
            print(f"    Successful runs: {success_count}/{len(results)}")
            print(f"    Success rate: {success_rate:.1%}")
            
            return success_rate >= 0.75  # At least 75% success rate
            
    except Exception as e:
        print(f"  ❌ Multiprocessing test failed: {e}")
        return False

def test_edge_cases():
    """Test edge cases and boundary conditions."""
    print("\n🔍 Testing edge cases...")
    
    edge_cases = [
        {
            'name': 'Minimal grid',
            'config': ModelConfig(
                grid_size=(1, 1),
                num_layers=1,
                max_steps=1,
                simulation_type='memory_optimized'
            )
        },
        {
            'name': 'Single layer',
            'config': ModelConfig(
                grid_size=(5, 5),
                num_layers=1,
                max_steps=3,
                simulation_type='memory_optimized'
            )
        },
        {
            'name': 'Zero steps',
            'config': ModelConfig(
                grid_size=(10, 10),
                num_layers=2,
                max_steps=0,
                simulation_type='memory_optimized'
            )
        },
        {
            'name': 'High spread probability',
            'config': ModelConfig(
                grid_size=(8, 8),
                num_layers=2,
                max_steps=5,
                simulation_type='memory_optimized',
                spread_probability=0.99,
                fuel_consumption_rate=0.001
            )
        }
    ]
    
    successful_cases = 0
    
    for case in edge_cases:
        try:
            params = {
                'spread_probability': getattr(case['config'], 'spread_probability', 0.8),
                'fuel_consumption_rate': getattr(case['config'], 'fuel_consumption_rate', 0.01),
                'ignition_threshold': getattr(case['config'], 'ignition_threshold', 0.1)
            }
            
            result = evaluate_worker_function(
                parameter_values=params,
                target_data=None,
                config_dict=case['config'].__dict__,
                objective_function_name="SpatialSimilarityObjective"
            )
            
            if result['is_valid']:
                print(f"  ✅ {case['name']}: Passed")
                successful_cases += 1
            else:
                print(f"  ❌ {case['name']}: Failed - {result.get('error_message', 'Unknown error')}")
                
        except Exception as e:
            print(f"  ❌ {case['name']}: Exception - {e}")
    
    success_rate = successful_cases / len(edge_cases)
    print(f"  📊 Edge case success rate: {success_rate:.1%}")
    
    return success_rate >= 0.75  # At least 75% success rate

def test_performance_issues():
    """Test for performance issues."""
    print("\n🔍 Testing for performance issues...")
    
    config = ModelConfig(
        grid_size=(25, 25),
        num_layers=3,
        max_steps=10,
        simulation_type='memory_optimized',
        spread_probability=0.8,
        fuel_consumption_rate=0.01,
        ignition_threshold=0.1
    )
    
    params = {
        'spread_probability': 0.8,
        'fuel_consumption_rate': 0.01,
        'ignition_threshold': 0.1
    }
    
    # Run multiple simulations to check performance consistency
    execution_times = []
    
    for i in range(3):
        start_time = time.time()
        
        try:
            result = evaluate_worker_function(
                parameter_values=params,
                target_data=None,
                config_dict=config.__dict__,
                objective_function_name="SpatialSimilarityObjective"
            )
            
            execution_time = time.time() - start_time
            execution_times.append(execution_time)
            
            print(f"  Run {i+1}: {execution_time:.2f}s")
            
            if not result['is_valid']:
                print(f"  ❌ Run {i+1} failed: {result.get('error_message', 'Unknown error')}")
                
        except Exception as e:
            print(f"  ❌ Run {i+1} exception: {e}")
    
    if len(execution_times) >= 2:
        avg_time = sum(execution_times) / len(execution_times)
        max_time = max(execution_times)
        min_time = min(execution_times)
        variance = max_time - min_time
        
        print(f"  📊 Performance analysis:")
        print(f"    Average time: {avg_time:.2f}s")
        print(f"    Min time: {min_time:.2f}s")
        print(f"    Max time: {max_time:.2f}s")
        print(f"    Variance: {variance:.2f}s")
        
        # Check for performance issues
        if avg_time > 30:  # More than 30 seconds average
            print(f"  ⚠️  Performance issue detected - slow execution")
            return False
        elif variance > avg_time * 0.5:  # High variance
            print(f"  ⚠️  Performance issue detected - inconsistent execution times")
            return False
        else:
            print(f"  ✅ No significant performance issues detected")
            return True
    else:
        print(f"  ❌ Insufficient data for performance analysis")
        return False

def main():
    """Run comprehensive issue detection."""
    print("🚀 Comprehensive Issue Detector for Forest Fire Simulation")
    print("=" * 60)
    
    tests = [
        ("Memory Leaks", test_memory_leaks),
        ("Deadlock Scenarios", test_deadlock_scenarios),
        ("Exception Handling", test_exception_handling),
        ("Resource Cleanup", test_resource_cleanup),
        ("Multiprocessing Issues", test_multiprocessing_issues),
        ("Edge Cases", test_edge_cases),
        ("Performance Issues", test_performance_issues)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            print(f"\n{'='*20} {test_name} {'='*20}")
            result = test_func()
            results[test_name] = result
        except Exception as e:
            print(f"  ❌ Test failed with exception: {e}")
            print(f"  Traceback: {traceback.format_exc()}")
            results[test_name] = False
    
    # Summary
    print(f"\n{'='*60}")
    print("📊 COMPREHENSIVE TEST SUMMARY")
    print("=" * 60)
    
    passed_tests = sum(results.values())
    total_tests = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"  {test_name}: {status}")
    
    print(f"\n  Overall: {passed_tests}/{total_tests} tests passed")
    print(f"  Success rate: {(passed_tests/total_tests)*100:.1f}%")
    
    if passed_tests == total_tests:
        print(f"\n🎉 All tests passed! No significant issues detected.")
    elif passed_tests >= total_tests * 0.8:
        print(f"\n⚠️  Most tests passed. Minor issues detected.")
    else:
        print(f"\n💥 Multiple issues detected. Framework needs attention.")
    
    return passed_tests >= total_tests * 0.8

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
