#!/usr/bin/env python3
"""
Memory Optimization Test for Forest Fire Simulation

This script tests all the memory optimizations implemented to ensure they work correctly
and prevent memory leaks during simulation.
"""

import os
import gc
import sys
import time
import psutil
import numpy as np
from pathlib import Path
from typing import Dict, Any, List
import json

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.utils.logging_utils import get_logger
from src.core.forest_model import create_forest_model
from src.core.fire_simulation_engine import FireSimulationEngine
from src.config.config_tools import get_global_config

logger = get_logger(__name__)

class MemoryOptimizationTester:
    """
    Comprehensive memory optimization tester for forest fire simulation.
    """
    
    def __init__(self):
        self.process = psutil.Process()
        self.test_results = []
        
        logger.info("🧪 Memory Optimization Tester initialized")
    
    def get_memory_usage_gb(self) -> float:
        """Get current memory usage in GB."""
        return self.process.memory_info().rss / (1024**3)
    
    def log_memory_status(self, stage: str):
        """Log current memory status."""
        current_memory = self.get_memory_usage_gb()
        logger.info(f"📊 Memory at {stage}: {current_memory:.2f} GB")
        return current_memory
    
    def test_1_active_cells_cleanup(self):
        """Test 1: Active cells cleanup during simulation."""
        logger.info("🧪 Test 1: Active cells cleanup...")
        
        initial_memory = self.log_memory_status("before_active_cells_test")
        
        # Create a small forest model for testing
        config = get_global_config()
        if config is None:
            from src.config.config_tools import ModelConfig
            config = ModelConfig()
        
        # Set test parameters
        config.grid_size = 100
        config.num_layers = 5
        config.max_steps = 50
        
        forest_model = create_forest_model(config=config)
        engine = FireSimulationEngine(forest_model=forest_model, config=config)
        
        # Run simulation to test active cells cleanup
        result = engine.run_simulation(max_steps=20)
        
        final_memory = self.log_memory_status("after_active_cells_test")
        memory_change = final_memory - initial_memory
        
        # Cleanup
        engine.cleanup()
        forest_model.cleanup()
        gc.collect()
        
        cleanup_memory = self.log_memory_status("after_cleanup")
        
        test_result = {
            "test": "active_cells_cleanup",
            "initial_memory_gb": initial_memory,
            "final_memory_gb": final_memory,
            "cleanup_memory_gb": cleanup_memory,
            "memory_change_gb": memory_change,
            "cleanup_effectiveness": initial_memory - cleanup_memory,
            "success": memory_change < 1.0  # Less than 1GB increase
        }
        
        self.test_results.append(test_result)
        logger.info(f"✅ Test 1 completed: Memory change {memory_change:+.2f} GB")
        
        return test_result
    
    def test_2_shared_terrain_usage(self):
        """Test 2: Shared terrain usage."""
        logger.info("🧪 Test 2: Shared terrain usage...")
        
        initial_memory = self.log_memory_status("before_shared_terrain_test")
        
        # Create multiple forest models to test shared terrain
        config = get_global_config()
        if config is None:
            from src.config.config_tools import ModelConfig
            config = ModelConfig()
        
        config.grid_size = 50
        config.num_layers = 3
        
        models = []
        for i in range(3):
            forest_model = create_forest_model(config=config)
            models.append(forest_model)
        
        # Check if terrain is shared
        terrain_refs = [id(model.terrain_elevation) for model in models if hasattr(model, 'terrain_elevation')]
        terrain_shared = len(set(terrain_refs)) <= 1  # Should be 1 if shared
        
        final_memory = self.log_memory_status("after_shared_terrain_test")
        memory_change = final_memory - initial_memory
        
        # Cleanup
        for model in models:
            model.cleanup()
        gc.collect()
        
        cleanup_memory = self.log_memory_status("after_cleanup")
        
        test_result = {
            "test": "shared_terrain_usage",
            "initial_memory_gb": initial_memory,
            "final_memory_gb": final_memory,
            "cleanup_memory_gb": cleanup_memory,
            "memory_change_gb": memory_change,
            "terrain_shared": terrain_shared,
            "terrain_refs_count": len(set(terrain_refs)),
            "success": terrain_shared and memory_change < 0.5
        }
        
        self.test_results.append(test_result)
        logger.info(f"✅ Test 2 completed: Terrain shared = {terrain_shared}")
        
        return test_result
    
    def test_3_sparse_storage_optimization(self):
        """Test 3: Sparse storage optimization."""
        logger.info("🧪 Test 3: Sparse storage optimization...")
        
        initial_memory = self.log_memory_status("before_sparse_test")
        
        # Create a larger model with sparse storage
        config = get_global_config()
        if config is None:
            from src.config.config_tools import ModelConfig
            config = ModelConfig()
        
        config.grid_size = 200
        config.num_layers = 10
        config.use_sparse_storage = True
        
        forest_model = create_forest_model(config=config)
        
        # Test sparse storage optimization
        if hasattr(forest_model, 'optimize_sparse_storage'):
            forest_model.optimize_sparse_storage()
            optimization_available = True
        else:
            optimization_available = False
        
        final_memory = self.log_memory_status("after_sparse_test")
        memory_change = final_memory - initial_memory
        
        # Cleanup
        forest_model.cleanup()
        gc.collect()
        
        cleanup_memory = self.log_memory_status("after_cleanup")
        
        test_result = {
            "test": "sparse_storage_optimization",
            "initial_memory_gb": initial_memory,
            "final_memory_gb": final_memory,
            "cleanup_memory_gb": cleanup_memory,
            "memory_change_gb": memory_change,
            "optimization_available": optimization_available,
            "success": optimization_available and memory_change < 2.0
        }
        
        self.test_results.append(test_result)
        logger.info(f"✅ Test 3 completed: Sparse optimization available = {optimization_available}")
        
        return test_result
    
    def test_4_periodic_cleanup(self):
        """Test 4: Periodic cleanup during simulation."""
        logger.info("🧪 Test 4: Periodic cleanup during simulation...")
        
        initial_memory = self.log_memory_status("before_periodic_cleanup_test")
        
        # Create forest model and engine
        config = get_global_config()
        if config is None:
            from src.config.config_tools import ModelConfig
            config = ModelConfig()
        
        config.grid_size = 100
        config.num_layers = 5
        config.max_steps = 30
        
        forest_model = create_forest_model(config=config)
        engine = FireSimulationEngine(forest_model=forest_model, config=config)
        
        # Run simulation with periodic cleanup
        result = engine.run_simulation(max_steps=25)
        
        final_memory = self.log_memory_status("after_periodic_cleanup_test")
        memory_change = final_memory - initial_memory
        
        # Cleanup
        engine.cleanup()
        forest_model.cleanup()
        gc.collect()
        
        cleanup_memory = self.log_memory_status("after_cleanup")
        
        test_result = {
            "test": "periodic_cleanup",
            "initial_memory_gb": initial_memory,
            "final_memory_gb": final_memory,
            "cleanup_memory_gb": cleanup_memory,
            "memory_change_gb": memory_change,
            "simulation_steps": result.get('stats', {}).get('steps', 0),
            "success": memory_change < 1.0 and result.get('stats', {}).get('steps', 0) > 0
        }
        
        self.test_results.append(test_result)
        logger.info(f"✅ Test 4 completed: Memory change {memory_change:+.2f} GB over {result.get('stats', {}).get('steps', 0)} steps")
        
        return test_result
    
    def test_5_history_cleanup(self):
        """Test 5: History cleanup and disk storage."""
        logger.info("🧪 Test 5: History cleanup and disk storage...")
        
        initial_memory = self.log_memory_status("before_history_test")
        
        # Create forest model and engine with history enabled
        config = get_global_config()
        if config is None:
            from src.config.config_tools import ModelConfig
            config = ModelConfig()
        
        config.grid_size = 80
        config.num_layers = 4
        config.max_steps = 40
        config.store_full_states = True
        config.use_disk_storage = True
        
        forest_model = create_forest_model(config=config)
        engine = FireSimulationEngine(forest_model=forest_model, config=config)
        
        # Run simulation with history storage
        result = engine.run_simulation(max_steps=35)
        
        final_memory = self.log_memory_status("after_history_test")
        memory_change = final_memory - initial_memory
        
        # Check if history files were created
        history_files = list(Path('.').glob('simulation_history_*.json'))
        history_saved = len(history_files) > 0
        
        # Cleanup
        engine.cleanup()
        forest_model.cleanup()
        gc.collect()
        
        # Remove history files
        for file in history_files:
            try:
                file.unlink()
            except:
                pass
        
        cleanup_memory = self.log_memory_status("after_cleanup")
        
        test_result = {
            "test": "history_cleanup",
            "initial_memory_gb": initial_memory,
            "final_memory_gb": final_memory,
            "cleanup_memory_gb": cleanup_memory,
            "memory_change_gb": memory_change,
            "history_saved": history_saved,
            "history_files_count": len(history_files),
            "success": history_saved and memory_change < 1.5
        }
        
        self.test_results.append(test_result)
        logger.info(f"✅ Test 5 completed: History saved = {history_saved}")
        
        return test_result
    
    def test_6_shared_memory_cleanup(self):
        """Test 6: Shared memory cleanup."""
        logger.info("🧪 Test 6: Shared memory cleanup...")
        
        initial_memory = self.log_memory_status("before_shared_memory_test")
        
        # Create forest model and engine
        config = get_global_config()
        if config is None:
            from src.config.config_tools import ModelConfig
            config = ModelConfig()
        
        config.grid_size = 100
        config.num_layers = 5
        
        forest_model = create_forest_model(config=config)
        engine = FireSimulationEngine(forest_model=forest_model, config=config)
        
        # Run simulation
        result = engine.run_simulation(max_steps=20)
        
        # Test shared memory cleanup
        if hasattr(engine, 'cleanup_shared_memory_blocks'):
            engine.cleanup_shared_memory_blocks()
            cleanup_available = True
        else:
            cleanup_available = False
        
        final_memory = self.log_memory_status("after_shared_memory_test")
        memory_change = final_memory - initial_memory
        
        # Cleanup
        engine.cleanup()
        forest_model.cleanup()
        gc.collect()
        
        cleanup_memory = self.log_memory_status("after_cleanup")
        
        test_result = {
            "test": "shared_memory_cleanup",
            "initial_memory_gb": initial_memory,
            "final_memory_gb": final_memory,
            "cleanup_memory_gb": cleanup_memory,
            "memory_change_gb": memory_change,
            "cleanup_available": cleanup_available,
            "success": cleanup_available and memory_change < 1.0
        }
        
        self.test_results.append(test_result)
        logger.info(f"✅ Test 6 completed: Shared memory cleanup available = {cleanup_available}")
        
        return test_result
    
    def run_all_tests(self):
        """Run all memory optimization tests."""
        logger.info("🚀 Running all memory optimization tests...")
        
        # Run all tests
        self.test_1_active_cells_cleanup()
        self.test_2_shared_terrain_usage()
        self.test_3_sparse_storage_optimization()
        self.test_4_periodic_cleanup()
        self.test_5_history_cleanup()
        self.test_6_shared_memory_cleanup()
        
        # Generate summary
        self.generate_test_summary()
        
        return self.test_results
    
    def generate_test_summary(self):
        """Generate comprehensive test summary."""
        logger.info("📊 Memory Optimization Test Summary:")
        logger.info("=" * 60)
        
        total_tests = len(self.test_results)
        successful_tests = sum(1 for result in self.test_results if result.get('success', False))
        
        logger.info(f"Total Tests: {total_tests}")
        logger.info(f"Successful: {successful_tests}")
        logger.info(f"Failed: {total_tests - successful_tests}")
        logger.info(f"Success Rate: {successful_tests/total_tests*100:.1f}%")
        
        # Individual test results
        for result in self.test_results:
            status = "✅ PASS" if result.get('success', False) else "❌ FAIL"
            logger.info(f"{status} {result['test']}: {result.get('memory_change_gb', 0):+.2f} GB")
        
        # Save detailed results
        self.save_test_results()
    
    def save_test_results(self, filename: str = "memory_optimization_test_results.json"):
        """Save detailed test results to file."""
        summary = {
            "timestamp": time.time(),
            "total_tests": len(self.test_results),
            "successful_tests": sum(1 for r in self.test_results if r.get('success', False)),
            "test_results": self.test_results
        }
        
        try:
            with open(filename, 'w') as f:
                json.dump(summary, f, indent=2, default=str)
            logger.info(f"📄 Test results saved to {filename}")
        except Exception as e:
            logger.error(f"❌ Failed to save test results: {e}")

def run_memory_optimization_tests():
    """Run comprehensive memory optimization tests."""
    tester = MemoryOptimizationTester()
    results = tester.run_all_tests()
    return results

if __name__ == "__main__":
    run_memory_optimization_tests()
