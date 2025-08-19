#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
HPC Optimization Configuration

This script configures the HPC environment for optimal performance with our
forest fire simulation optimizations.

Key configurations:
1. NumExpr thread limits for vectorized operations
2. NumPy thread limits for BLAS operations
3. Memory management settings
4. Shared memory configuration
5. Process pool settings

Author: Forest Fire Simulation Team
Date: 2025
Version: 1.0
"""

import os
import sys
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

def configure_numexpr():
    """Configure NumExpr for optimal vectorized operations."""
    print("🔧 Configuring NumExpr for HPC...")
    
    # Set NumExpr thread limits based on environment
    cpu_count = os.cpu_count() or 1
    
    # For HPC, use 75% of available cores for NumExpr
    numexpr_threads = max(1, int(cpu_count * 0.75))
    
    # Set environment variables
    os.environ['NUMEXPR_MAX_THREADS'] = str(numexpr_threads)
    os.environ['NUMEXPR_NUM_THREADS'] = str(numexpr_threads)
    
    print(f"   ✅ NumExpr threads: {numexpr_threads} (out of {cpu_count} total)")
    
    # Verify configuration
    try:
        import numexpr as ne
        print(f"   ✅ NumExpr version: {ne.__version__}")
        print(f"   ✅ NumExpr threads: {ne.nthreads}")
    except ImportError:
        print("   ⚠️  NumExpr not available")

def configure_numpy():
    """Configure NumPy for optimal BLAS operations."""
    print("🔧 Configuring NumPy for HPC...")
    
    # Set NumPy thread limits
    cpu_count = os.cpu_count() or 1
    numpy_threads = max(1, int(cpu_count * 0.5))  # Use 50% for NumPy
    
    os.environ['OPENBLAS_NUM_THREADS'] = str(numpy_threads)
    os.environ['MKL_NUM_THREADS'] = str(numpy_threads)
    os.environ['OMP_NUM_THREADS'] = str(numpy_threads)
    
    print(f"   ✅ NumPy/BLAS threads: {numpy_threads}")
    
    # Verify configuration
    try:
        import numpy as np
        print(f"   ✅ NumPy version: {np.__version__}")
        print(f"   ✅ NumPy config: {np.show_config()}")
    except Exception as e:
        print(f"   ⚠️  NumPy configuration check failed: {e}")

def configure_memory():
    """Configure memory management for HPC."""
    print("🔧 Configuring memory management...")
    
    # Set garbage collection thresholds
    import gc
    gc.set_threshold(700, 10, 10)  # More aggressive GC for HPC
    
    # Set memory limits for shared memory
    os.environ['SHARED_MEMORY_SIZE_LIMIT'] = '8589934592'  # 8GB limit
    
    print("   ✅ Garbage collection thresholds set")
    print("   ✅ Shared memory size limit: 8GB")

def configure_multiprocessing():
    """Configure multiprocessing for HPC."""
    print("🔧 Configuring multiprocessing...")
    
    # Set multiprocessing start method
    import multiprocessing as mp
    
    # Use 'spawn' for better HPC compatibility
    try:
        mp.set_start_method('spawn', force=True)
        print("   ✅ Multiprocessing start method: spawn")
    except RuntimeError:
        print("   ⚠️  Multiprocessing start method already set")
    
    # Configure process pool settings
    cpu_count = os.cpu_count() or 1
    max_workers = min(cpu_count, 32)  # Cap at 32 workers
    
    print(f"   ✅ Max workers: {max_workers}")

def configure_optimization_factory():
    """Configure the optimization factory for HPC."""
    print("🔧 Configuring optimization factory...")
    
    try:
        from src.core.optimization_factory import (
            set_optimization_config,
            OptimizationConfig
        )
        
        # Create HPC-optimized configuration
        hpc_config = OptimizationConfig()
        
        # Lower thresholds for HPC (more aggressive optimization)
        hpc_config.auto_optimize_threshold = 500_000  # 500K cells
        hpc_config.force_optimize_threshold = 5_000_000  # 5M cells
        
        # Enable all optimizations
        hpc_config.enable_vectorized_processing = True
        hpc_config.enable_batch_updates = True
        hpc_config.enable_neighbor_caching = True
        hpc_config.enable_optimized_sparse_ops = True
        
        # Enable performance logging
        hpc_config.enable_performance_logging = True
        hpc_config.log_optimization_decisions = True
        
        # Enable graceful fallback
        hpc_config.graceful_fallback = True
        hpc_config.fallback_on_error = True
        
        # Set the configuration
        set_optimization_config(hpc_config)
        
        print("   ✅ Optimization factory configured for HPC")
        print(f"   ✅ Auto-optimize threshold: {hpc_config.auto_optimize_threshold:,} cells")
        print(f"   ✅ Force-optimize threshold: {hpc_config.force_optimize_threshold:,} cells")
        
    except ImportError as e:
        print(f"   ❌ Failed to configure optimization factory: {e}")

def verify_optimizations():
    """Verify that optimizations are available and configured."""
    print("🔍 Verifying optimizations...")
    
    try:
        from src.core.optimization_factory import (
            get_optimization_status,
            log_optimization_status
        )
        
        status = get_optimization_status()
        
        print(f"   ✅ Optimizations available: {status['optimizations_available']}")
        print(f"   ✅ Auto threshold: {status['configuration']['auto_optimize_threshold']:,}")
        print(f"   ✅ Force threshold: {status['configuration']['force_optimize_threshold']:,}")
        
        # Log detailed status
        log_optimization_status()
        
        return status['optimizations_available']
        
    except ImportError as e:
        print(f"   ❌ Failed to verify optimizations: {e}")
        return False

def main():
    """Main configuration function."""
    print("HPC OPTIMIZATION CONFIGURATION")
    print("=" * 60)
    
    # Configure all components
    configure_numexpr()
    configure_numpy()
    configure_memory()
    configure_multiprocessing()
    configure_optimization_factory()
    
    # Verify configuration
    optimizations_available = verify_optimizations()
    
    print("\n" + "=" * 60)
    print("📊 CONFIGURATION SUMMARY")
    print("=" * 60)
    
    if optimizations_available:
        print("HPC OPTIMIZATIONS CONFIGURED SUCCESSFULLY!")
        print("   The calibration will use optimized components on HPC.")
        print("   Performance improvements should be significant for large grids.")
    else:
        print("HPC OPTIMIZATIONS NOT FULLY CONFIGURED!")
        print("   Some optimizations may not be available.")
        print("   Check the configuration output above.")
    
    print("\n📋 Environment variables set:")
    for key, value in os.environ.items():
        if any(prefix in key for prefix in ['NUMEXPR', 'OPENBLAS', 'MKL', 'OMP', 'SHARED']):
            print(f"   {key}: {value}")

if __name__ == "__main__":
    main()
