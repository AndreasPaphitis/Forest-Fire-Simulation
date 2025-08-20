#!/usr/bin/env python3
"""
HPC Optimizer Module

Addresses the three most critical constraints in HPC environments:
1. Network Filesystem Bottlenecks
2. Memory Bandwidth Limitations  
3. Garbage Collection Overhead
"""

import os
import gc
import threading
import time
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
import logging

# Try to import psutil, fallback gracefully if not available
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    logging.warning("psutil module not found. Memory monitoring will use fallback mechanisms.")

logger = logging.getLogger(__name__)

class HPCOptimizer:
    """
    HPC-specific optimizations for forest fire simulation.
    
    Addresses:
    - Network filesystem bottlenecks
    - Memory bandwidth limitations
    - Garbage collection overhead
    """
    
    def __init__(self):
        self.original_gc_settings = None
        self.memory_monitor_active = False
        self.local_storage_paths = []
        self.numa_nodes = self._detect_numa_nodes()
        
    def _detect_numa_nodes(self) -> int:
        """Detect number of NUMA nodes on the system."""
        try:
            # Check for NUMA nodes
            numa_path = Path("/sys/devices/system/node")
            if numa_path.exists():
                nodes = [d for d in numa_path.iterdir() if d.name.startswith("node")]
                return len(nodes)
        except Exception:
            pass
        return 1  # Single node if detection fails
    
    def optimize_for_hpc(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply all HPC optimizations to the configuration.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            Optimized configuration
        """
        logger.info("🚀 Applying HPC optimizations...")
        
        # 1. Network filesystem optimization
        config = self._optimize_storage_paths(config)
        
        # 2. Memory bandwidth optimization
        config = self._optimize_memory_bandwidth(config)
        
        # 3. Garbage collection optimization
        self._optimize_garbage_collection()
        
        logger.info("✅ HPC optimizations applied successfully")
        return config
    
    def _optimize_storage_paths(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Optimize storage paths to avoid network filesystem bottlenecks.
        
        Prefers local storage over network storage for better performance.
        """
        logger.info("📁 Optimizing storage paths for local access...")
        
        # Find optimal local storage paths
        local_paths = self._find_local_storage_paths()
        self.local_storage_paths = local_paths
        
        # Update configuration to use local storage
        if 'output' in config:
            config['output']['base_path'] = local_paths['scratch']
            logger.info(f"   Output path: {local_paths['scratch']}")
        
        if 'terrain' in config and 'preprocessed_dir' in config['terrain']:
            # Keep terrain data on network storage but cache locally
            original_path = config['terrain']['preprocessed_dir']
            local_cache = Path(local_paths['scratch']) / "terrain_cache"
            config['terrain']['local_cache_dir'] = str(local_cache)
            logger.info(f"   Terrain cache: {local_cache}")
        
        # Set environment variables for optimal storage
        os.environ['TMPDIR'] = local_paths['tmp']
        os.environ['SHM_DIR'] = local_paths['shm']
        
        logger.info(f"   Local storage paths: {local_paths}")
        return config
    
    def _find_local_storage_paths(self) -> Dict[str, str]:
        """
        Find optimal local storage paths, preferring fastest storage.
        
        Returns:
            Dictionary of storage type to path mapping
        """
        storage_candidates = {
            'shm': [
                '/dev/shm',  # Shared memory filesystem (fastest)
                '/run/shm',  # Alternative shared memory
            ],
            'tmp': [
                '/tmp',      # Local temp storage
                '/var/tmp',  # System temp storage
            ],
            'scratch': [
                '/scratch',           # HPC scratch storage
                '/scratch-shared',    # Shared scratch
                '/tmp',              # Fallback to local temp
            ]
        }
        
        found_paths = {}
        
        for storage_type, candidates in storage_candidates.items():
            for candidate in candidates:
                if self._is_storage_accessible(candidate):
                    found_paths[storage_type] = candidate
                    logger.info(f"   Found {storage_type} storage: {candidate}")
                    break
            else:
                # Fallback to /tmp if nothing else works
                found_paths[storage_type] = '/tmp'
                logger.warning(f"   No {storage_type} storage found, using /tmp")
        
        return found_paths
    
    def _is_storage_accessible(self, path: str) -> bool:
        """Check if storage path is accessible and writable."""
        try:
            path_obj = Path(path)
            if not path_obj.exists():
                return False
            
            # Test write access
            test_file = path_obj / f"hpc_test_{os.getpid()}.tmp"
            test_file.write_text("test")
            test_file.unlink()
            return True
        except Exception:
            return False
    
    def _optimize_memory_bandwidth(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Optimize for memory bandwidth limitations.
        
        Reduces worker count and implements memory access coordination.
        """
        logger.info("🧠 Optimizing memory bandwidth usage...")
        
        # Calculate optimal worker count based on memory bandwidth
        optimal_workers = self._calculate_optimal_worker_count()
        
        # Update configuration
        if 'calibration' in config:
            current_workers = config['calibration'].get('max_workers', 70)
            if current_workers > optimal_workers:
                logger.warning(f"   Reducing workers from {current_workers} to {optimal_workers} for memory bandwidth")
                config['calibration']['max_workers'] = optimal_workers
        
        # Add memory bandwidth monitoring
        config['monitoring'] = config.get('monitoring', {})
        config['monitoring']['memory_bandwidth_monitoring'] = True
        config['monitoring']['memory_threshold_gb'] = self._get_memory_threshold()
        
        logger.info(f"   Optimal worker count: {optimal_workers}")
        return config
    
    def _calculate_optimal_worker_count(self) -> int:
        """
        Calculate optimal worker count based on memory bandwidth.
        
        Uses conservative estimates to prevent memory bandwidth saturation.
        """
        try:
            if not PSUTIL_AVAILABLE:
                logger.warning("   psutil not available - using conservative defaults")
                return 16  # Conservative default
            
            # Get system memory information
            memory = psutil.virtual_memory()
            total_gb = memory.total / (1024**3)
            
            # Conservative estimate: 1 worker per 4GB of memory
            # This prevents memory bandwidth saturation
            memory_based_workers = max(1, int(total_gb / 4))
            
            # NUMA-aware worker count
            numa_based_workers = self.numa_nodes * 6  # 6 workers per NUMA node (increased from 4)
            
            # CPU-based worker count
            cpu_count = psutil.cpu_count(logical=False)  # Physical cores only
            cpu_based_workers = max(1, cpu_count - 2)  # Reserve 2 cores for system
            
            # Take the minimum to prevent overloading
            optimal_workers = min(memory_based_workers, numa_based_workers, cpu_based_workers)
            
            # NUMA-aware cap: allow more workers for high NUMA count systems
            if self.numa_nodes >= 8:
                max_workers = 64  # High NUMA count systems can handle more workers
            elif self.numa_nodes >= 4:
                max_workers = 48  # Medium NUMA count systems
            else:
                max_workers = 32  # Low NUMA count systems
            
            optimal_workers = min(optimal_workers, max_workers)
            
            return optimal_workers
            
        except Exception as e:
            logger.warning(f"   Could not calculate optimal worker count: {e}")
            return 16  # Conservative default
    
    def _get_memory_threshold(self) -> float:
        """Get memory threshold for monitoring (80% of available memory)."""
        try:
            if not PSUTIL_AVAILABLE:
                return 100.0  # Default threshold
            
            memory = psutil.virtual_memory()
            return memory.total * 0.8 / (1024**3)  # 80% of total memory in GB
        except Exception:
            return 100.0  # Default threshold
    
    def _optimize_garbage_collection(self):
        """
        Optimize garbage collection for HPC performance.
        
        Disables automatic GC during critical sections and implements
        manual collection at optimal times.
        """
        logger.info("🗑️  Optimizing garbage collection...")
        
        # Store original GC settings
        self.original_gc_settings = {
            'enabled': gc.isenabled(),
            'thresholds': gc.get_threshold(),
            'count': gc.get_count()
        }
        
        # Optimize GC thresholds for large objects
        # More aggressive collection to prevent memory pressure
        gc.set_threshold(100, 5, 5)  # (threshold0, threshold1, threshold2)
        
        # Disable automatic GC during critical operations
        gc.disable()
        
        logger.info("   Garbage collection optimized for HPC performance")
    
    def start_memory_monitoring(self):
        """Start memory bandwidth monitoring."""
        if self.memory_monitor_active:
            return
        
        self.memory_monitor_active = True
        self.monitor_thread = threading.Thread(target=self._memory_monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("👁️  Memory bandwidth monitoring started")
    
    def stop_memory_monitoring(self):
        """Stop memory bandwidth monitoring."""
        self.memory_monitor_active = False
        if hasattr(self, 'monitor_thread'):
            self.monitor_thread.join(timeout=5.0)
        logger.info("👁️  Memory bandwidth monitoring stopped")
    
    def _memory_monitor_loop(self):
        """Memory monitoring loop."""
        while self.memory_monitor_active:
            try:
                if not PSUTIL_AVAILABLE:
                    # Fallback monitoring without psutil
                    logger.info("   Memory monitoring active (psutil not available)")
                    time.sleep(30)  # Check every 30 seconds
                    continue
                
                memory = psutil.virtual_memory()
                used_gb = memory.used / (1024**3)
                available_gb = memory.available / (1024**3)
                
                # Log memory usage every 30 seconds
                if int(time.time()) % 30 == 0:
                    logger.info(f"   Memory: {used_gb:.1f}GB used, {available_gb:.1f}GB available")
                
                # Alert if memory usage is high
                if memory.percent > 85:
                    logger.warning(f"   ⚠️  High memory usage: {memory.percent:.1f}%")
                    # Force garbage collection
                    collected = gc.collect()
                    if collected > 0:
                        logger.info(f"   🗑️  GC collected {collected} objects")
                
                time.sleep(5)  # Check every 5 seconds
                
            except Exception as e:
                logger.warning(f"   Memory monitoring error: {e}")
                time.sleep(10)
    
    def force_garbage_collection(self) -> int:
        """
        Force garbage collection and return number of collected objects.
        
        Returns:
            Number of objects collected
        """
        # Re-enable GC temporarily
        gc.enable()
        
        # Force collection
        collected = gc.collect()
        
        # Disable GC again
        gc.disable()
        
        if collected > 0:
            logger.info(f"🗑️  Forced GC collected {collected} objects")
        
        return collected
    
    def restore_original_settings(self):
        """Restore original garbage collection settings."""
        if self.original_gc_settings:
            gc.enable() if self.original_gc_settings['enabled'] else gc.disable()
            gc.set_threshold(*self.original_gc_settings['thresholds'])
            logger.info("🔄 Restored original garbage collection settings")
    
    def cleanup_local_storage(self):
        """Clean up local storage files."""
        logger.info("🧹 Cleaning up local storage...")
        
        for storage_type, path in self.local_storage_paths.items():
            try:
                path_obj = Path(path)
                if path_obj.exists():
                    # Remove temporary files created by this process
                    for temp_file in path_obj.glob(f"hpc_*_{os.getpid()}.*"):
                        temp_file.unlink()
                        logger.debug(f"   Removed: {temp_file}")
            except Exception as e:
                logger.warning(f"   Error cleaning {storage_type} storage: {e}")
    
    def get_optimization_summary(self) -> Dict[str, Any]:
        """Get summary of applied optimizations."""
        return {
            'local_storage_paths': self.local_storage_paths,
            'numa_nodes': self.numa_nodes,
            'memory_monitoring_active': self.memory_monitor_active,
            'gc_optimized': self.original_gc_settings is not None,
            'optimizations_applied': [
                'Network filesystem optimization',
                'Memory bandwidth optimization', 
                'Garbage collection optimization'
            ]
        }


# Global HPC optimizer instance
_hpc_optimizer = None

def get_hpc_optimizer() -> HPCOptimizer:
    """Get the global HPC optimizer instance."""
    global _hpc_optimizer
    if _hpc_optimizer is None:
        _hpc_optimizer = HPCOptimizer()
    return _hpc_optimizer

def apply_hpc_optimizations(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Apply HPC optimizations to configuration.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        Optimized configuration
    """
    optimizer = get_hpc_optimizer()
    return optimizer.optimize_for_hpc(config)

def start_hpc_monitoring():
    """Start HPC monitoring."""
    optimizer = get_hpc_optimizer()
    optimizer.start_memory_monitoring()

def stop_hpc_monitoring():
    """Stop HPC monitoring and cleanup."""
    optimizer = get_hpc_optimizer()
    optimizer.stop_memory_monitoring()
    optimizer.cleanup_local_storage()
    optimizer.restore_original_settings()
