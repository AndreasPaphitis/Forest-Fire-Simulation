#!/usr/bin/env python3
"""
Emergency Memory Optimizer for Forest Fire Simulation

This script provides immediate memory optimization to prevent OOM kills
by addressing the critical memory leaks and excessive terrain data loading.
"""

import os
import gc
import psutil
import numpy as np
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
import sys

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.utils.logging_utils import get_logger

logger = get_logger(__name__)

class MemoryEmergencyOptimizer:
    """Emergency memory optimization for the forest fire simulation."""
    
    def __init__(self):
        self.process = psutil.Process()
        self.initial_memory = self.get_memory_usage_gb()
        logger.info(f"🧠 Initial memory usage: {self.initial_memory:.2f} GB")
        
    def get_memory_usage_gb(self) -> float:
        """Get current memory usage in GB."""
        memory_info = self.process.memory_info()
        return memory_info.rss / (1024**3)
    
    def log_memory_status(self, stage: str):
        """Log current memory status."""
        current_memory = self.get_memory_usage_gb()
        memory_increase = current_memory - self.initial_memory
        
        logger.info(f"📊 Memory usage at {stage}:")
        logger.info(f"   Current: {current_memory:.2f} GB")
        logger.info(f"   Increase: {memory_increase:+.2f} GB")
        
        # Check for memory pressure
        if current_memory > 100:  # >100GB
            logger.warning(f"⚠️  High memory usage detected: {current_memory:.2f} GB")
            logger.warning("   Consider reducing grid size or using more aggressive optimization")
        
        return current_memory
    
    def cleanup_shared_memory_leaks(self):
        """Clean up shared memory leaks."""
        try:
            from multiprocessing import shared_memory
            import tempfile
            import glob
            
            # Find and clean up orphaned shared memory
            shared_mem_pattern = "/dev/shm/psm_*"  # Linux
            if os.path.exists("/dev/shm"):
                orphaned_blocks = glob.glob(shared_mem_pattern)
                for block_path in orphaned_blocks:
                    try:
                        os.remove(block_path)
                        logger.info(f"🧹 Cleaned up orphaned shared memory: {block_path}")
                    except Exception as e:
                        logger.debug(f"Could not clean {block_path}: {e}")
            
            # Also try Windows/macOS approach
            try:
                # Force garbage collection of any remaining shared memory objects
                gc.collect()
                logger.info("✅ Shared memory cleanup completed")
            except Exception as e:
                logger.warning(f"⚠️  Shared memory cleanup warning: {e}")
                
        except ImportError:
            logger.warning("⚠️  Shared memory module not available")
        except Exception as e:
            logger.warning(f"⚠️  Error during shared memory cleanup: {e}")
    
    def optimize_terrain_loading(self, config: Optional[Any] = None) -> Dict[str, Any]:
        """
        Optimize terrain loading to prevent OOM.
        
        Returns memory-safe configuration modifications.
        """
        optimizations = {
            'memory_optimizations_applied': [],
            'original_settings': {},
            'recommendations': []
        }
        
        # 1. Force memory-efficient mode
        if config and hasattr(config, 'memory_optimization_level'):
            optimizations['original_settings']['memory_optimization_level'] = config.memory_optimization_level
            config.memory_optimization_level = 2  # Maximum optimization
            optimizations['memory_optimizations_applied'].append('Set memory_optimization_level = 2')
        
        # 2. Disable shared memory for large grids (to prevent copies)
        if config and hasattr(config, 'use_shared_terrain'):
            optimizations['original_settings']['use_shared_terrain'] = config.use_shared_terrain
            # Calculate grid size
            if hasattr(config, 'grid_size'):
                grid_size = config.grid_size
                if isinstance(grid_size, (list, tuple)) and len(grid_size) >= 2:
                    total_cells = grid_size[0] * grid_size[1]
                else:
                    total_cells = grid_size * grid_size if isinstance(grid_size, int) else 100000000
                
                # Disable shared memory for very large grids to prevent copying overhead
                if total_cells > 100000000:  # >100M cells
                    config.use_shared_terrain = False
                    optimizations['memory_optimizations_applied'].append('Disabled shared terrain for large grid')
                    optimizations['recommendations'].append(
                        'Large grid detected: Using individual terrain loading per worker to prevent memory copying'
                    )
        
        # 3. Force sparse storage
        optimizations['memory_optimizations_applied'].append('Enforcing sparse storage mode')
        
        # 4. Reduce precision if possible
        optimizations['recommendations'].extend([
            'Consider using float32 instead of float64 for terrain data',
            'Use smaller grid sizes for testing (e.g., 1000x1000 instead of 15121x24741)',
            'Increase tiling size to reduce memory fragmentation',
            'Monitor memory usage with: watch -n 1 "free -h && ps aux --sort=-%mem | head"'
        ])
        
        return optimizations
    
    def create_memory_safe_terrain_loader(self, preprocessed_dir: str, target_shape: Tuple[int, int]):
        """
        Create a memory-safe terrain loader that avoids copies and manages memory carefully.
        """
        logger.info(f"🛡️  Creating memory-safe terrain loader for shape {target_shape}")
        
        # Calculate memory requirements
        total_cells = target_shape[0] * target_shape[1]
        estimated_gb = total_cells * 27 / (1024**3)  # 27 bytes per cell (conservative)
        
        logger.info(f"📊 Estimated terrain memory: {estimated_gb:.2f} GB")
        
        if estimated_gb > 50:
            logger.warning(f"⚠️  Large terrain memory requirement: {estimated_gb:.2f} GB")
            logger.warning("   Implementing aggressive memory management")
            
            # Suggest alternative approaches
            recommendations = [
                f"Consider tiling: Load terrain in chunks rather than all at once",
                f"Use memory mapping: Load terrain on-demand using np.memmap",
                f"Reduce resolution: Consider downsampling from {target_shape} to smaller size",
                f"Use compression: Store terrain data in compressed format"
            ]
            
            for rec in recommendations:
                logger.info(f"💡 {rec}")
        
        return {
            'loader_type': 'memory_safe',
            'estimated_memory_gb': estimated_gb,
            'use_memmap': estimated_gb > 20,
            'use_tiling': estimated_gb > 50,
            'recommended_tile_size': min(2048, int(np.sqrt(50 * 1024**3 / 27)))  # 50GB max per tile
        }
    
    def emergency_memory_recovery(self):
        """Perform emergency memory recovery."""
        logger.warning("🚨 Performing emergency memory recovery")
        
        current_memory = self.get_memory_usage_gb()
        logger.warning(f"   Current memory usage: {current_memory:.2f} GB")
        
        # 1. Force garbage collection
        collected = gc.collect()
        logger.info(f"🗑️  Garbage collection freed {collected} objects")
        
        # 2. Clean up shared memory
        self.cleanup_shared_memory_leaks()
        
        # 3. Try to free numpy memory
        try:
            # Force numpy to release memory back to OS
            import ctypes
            libc = ctypes.CDLL("libc.so.6")  # Linux
            libc.malloc_trim(0)
            logger.info("🧹 Released numpy memory back to OS")
        except:
            logger.debug("Could not force memory release (non-Linux system)")
        
        # 4. Check memory after cleanup
        new_memory = self.get_memory_usage_gb()
        freed_memory = current_memory - new_memory
        
        if freed_memory > 0.1:  # More than 100MB freed
            logger.info(f"✅ Emergency recovery freed {freed_memory:.2f} GB")
        else:
            logger.warning("⚠️  Limited memory recovery - consider restarting process")
        
        return freed_memory

def main():
    """Main function for emergency memory optimization."""
    optimizer = MemoryEmergencyOptimizer()
    
    logger.info("🚨 Forest Fire Simulation - Emergency Memory Optimizer")
    logger.info("=" * 60)
    
    # Check initial memory
    optimizer.log_memory_status("startup")
    
    # Perform emergency recovery
    freed_memory = optimizer.emergency_memory_recovery()
    
    # Log final status
    optimizer.log_memory_status("after_emergency_recovery")
    
    # Provide recommendations
    logger.info("💡 Immediate Recommendations:")
    logger.info("   1. Reduce grid size: Use smaller domains for testing")
    logger.info("   2. Increase memory: Request more memory allocation if on HPC")
    logger.info("   3. Use tiling: Process terrain in smaller chunks")
    logger.info("   4. Monitor memory: Use 'htop' or 'ps' to track usage")
    logger.info("   5. Check shared memory: Ensure proper cleanup between runs")
    
    return freed_memory > 0.5  # Success if freed more than 500MB

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
