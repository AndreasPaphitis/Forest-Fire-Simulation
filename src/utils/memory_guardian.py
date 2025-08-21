#!/usr/bin/env python3
"""
Memory Guardian - Real-time memory monitoring and OOM prevention

This module provides active memory monitoring and automatic memory management
to prevent OOM kills during forest fire simulations.
"""

import gc
import os
import psutil
import threading
import time
import numpy as np
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass
from pathlib import Path
import warnings

from src.utils.logging_utils import get_logger

logger = get_logger(__name__)

@dataclass
class MemoryThresholds:
    """Memory usage thresholds for different actions."""
    warning_gb: float = 75.0      # Warning threshold
    critical_gb: float = 90.0     # Critical threshold - start aggressive cleanup
    emergency_gb: float = 100.0   # Emergency threshold - force checkpoint and exit
    max_system_gb: float = 120.0  # Maximum system memory before OOM likely

class MemoryGuardian:
    """
    Real-time memory monitor and guardian to prevent OOM kills.
    
    Features:
    - Continuous memory monitoring
    - Automatic garbage collection
    - Shared memory leak detection and cleanup
    - Emergency checkpointing
    - Memory pressure alerts
    """
    
    def __init__(self, thresholds: Optional[MemoryThresholds] = None):
        self.thresholds = thresholds or MemoryThresholds()
        self.process = psutil.Process()
        self.monitoring = False
        self.monitor_thread = None
        self.callbacks = {
            'warning': [],
            'critical': [],
            'emergency': []
        }
        
        # Memory tracking
        self.memory_history: List[float] = []
        self.max_history_size = 100
        self.last_cleanup_time = time.time()
        self.cleanup_interval = 300  # 5 minutes
        
        # System info
        self.system_memory_gb = psutil.virtual_memory().total / (1024**3)
        logger.info(f"🛡️  Memory Guardian initialized")
        logger.info(f"   System RAM: {self.system_memory_gb:.1f} GB")
        logger.info(f"   Thresholds: Warning={self.thresholds.warning_gb}GB, "
                   f"Critical={self.thresholds.critical_gb}GB, "
                   f"Emergency={self.thresholds.emergency_gb}GB")
    
    def get_memory_usage_gb(self) -> float:
        """Get current process memory usage in GB."""
        return self.process.memory_info().rss / (1024**3)
    
    def get_system_memory_usage(self) -> Dict[str, float]:
        """Get system-wide memory statistics."""
        mem = psutil.virtual_memory()
        return {
            'total_gb': mem.total / (1024**3),
            'used_gb': mem.used / (1024**3),
            'available_gb': mem.available / (1024**3),
            'percent': mem.percent
        }
    
    def add_callback(self, threshold: str, callback: Callable):
        """Add callback for memory threshold events."""
        if threshold in self.callbacks:
            self.callbacks[threshold].append(callback)
            logger.info(f"📞 Added {threshold} threshold callback")
    
    def force_garbage_collection(self) -> int:
        """Force comprehensive garbage collection."""
        logger.info("🗑️  Forcing garbage collection...")
        
        # Multiple GC passes for better cleanup
        collected_total = 0
        for i in range(3):
            collected = gc.collect()
            collected_total += collected
            if collected == 0:
                break
        
        # Force numpy memory release on Linux
        try:
            import ctypes
            libc = ctypes.CDLL("libc.so.6")
            libc.malloc_trim(0)
            logger.debug("🧹 Released numpy memory back to OS")
        except:
            pass  # Not Linux or other issue
        
        logger.info(f"✅ Garbage collection freed {collected_total} objects")
        return collected_total
    
    def cleanup_shared_memory_leaks(self) -> int:
        """Clean up potential shared memory leaks."""
        cleaned_count = 0
        
        try:
            # Linux shared memory cleanup
            if os.path.exists("/dev/shm"):
                import glob
                patterns = ["/dev/shm/psm_*", "/dev/shm/wnsm_*"]  # Python shared memory patterns
                
                for pattern in patterns:
                    leaked_blocks = glob.glob(pattern)
                    for block_path in leaked_blocks:
                        try:
                            # Check if the block is old (more than 1 hour)
                            stat = os.stat(block_path)
                            age_hours = (time.time() - stat.st_mtime) / 3600
                            
                            if age_hours > 1:  # Only clean up old blocks
                                os.remove(block_path)
                                cleaned_count += 1
                                logger.debug(f"🧹 Cleaned orphaned shared memory: {block_path}")
                        except Exception as e:
                            logger.debug(f"Could not clean {block_path}: {e}")
            
            if cleaned_count > 0:
                logger.info(f"✅ Cleaned {cleaned_count} orphaned shared memory blocks")
                
        except Exception as e:
            logger.warning(f"⚠️  Error during shared memory cleanup: {e}")
        
        return cleaned_count
    
    def emergency_memory_release(self) -> float:
        """Emergency memory release procedures."""
        logger.warning("🚨 EMERGENCY MEMORY RELEASE ACTIVATED")
        
        initial_memory = self.get_memory_usage_gb()
        
        # 1. Force aggressive garbage collection
        self.force_garbage_collection()
        
        # 2. Clean up shared memory leaks
        self.cleanup_shared_memory_leaks()
        
        # 3. Try to release numpy memory caches
        try:
            # Clear numpy internal caches
            np.clear_cache() if hasattr(np, 'clear_cache') else None
        except:
            pass
        
        # 4. Force memory release back to OS
        try:
            import ctypes
            libc = ctypes.CDLL("libc.so.6")
            libc.malloc_trim(0)
        except:
            pass
        
        final_memory = self.get_memory_usage_gb()
        freed_memory = initial_memory - final_memory
        
        logger.warning(f"🚨 Emergency release: {freed_memory:.2f} GB freed "
                      f"({initial_memory:.2f} → {final_memory:.2f} GB)")
        
        return freed_memory
    
    def check_memory_status(self) -> Dict[str, Any]:
        """Check current memory status and trigger appropriate actions."""
        current_memory = self.get_memory_usage_gb()
        system_memory = self.get_system_memory_usage()
        
        # Track memory history
        self.memory_history.append(current_memory)
        if len(self.memory_history) > self.max_history_size:
            self.memory_history.pop(0)
        
        # Determine memory pressure level
        pressure_level = "normal"
        if current_memory >= self.thresholds.emergency_gb:
            pressure_level = "emergency"
        elif current_memory >= self.thresholds.critical_gb:
            pressure_level = "critical"
        elif current_memory >= self.thresholds.warning_gb:
            pressure_level = "warning"
        
        # Calculate memory trend
        trend = "stable"
        if len(self.memory_history) >= 10:
            recent_avg = np.mean(self.memory_history[-5:])
            older_avg = np.mean(self.memory_history[-10:-5])
            if recent_avg > older_avg * 1.1:
                trend = "increasing"
            elif recent_avg < older_avg * 0.9:
                trend = "decreasing"
        
        status = {
            'current_memory_gb': current_memory,
            'system_memory': system_memory,
            'pressure_level': pressure_level,
            'trend': trend,
            'time_since_last_cleanup': time.time() - self.last_cleanup_time
        }
        
        # Take action based on pressure level
        if pressure_level == "emergency":
            logger.error(f"🚨 EMERGENCY: Memory usage {current_memory:.2f} GB >= {self.thresholds.emergency_gb} GB")
            self.emergency_memory_release()
            # Trigger emergency callbacks
            for callback in self.callbacks['emergency']:
                try:
                    callback(status)
                except Exception as e:
                    logger.error(f"❌ Emergency callback failed: {e}")
                    
        elif pressure_level == "critical":
            logger.warning(f"⚠️  CRITICAL: Memory usage {current_memory:.2f} GB >= {self.thresholds.critical_gb} GB")
            self.force_garbage_collection()
            # Trigger critical callbacks
            for callback in self.callbacks['critical']:
                try:
                    callback(status)
                except Exception as e:
                    logger.error(f"❌ Critical callback failed: {e}")
                    
        elif pressure_level == "warning":
            logger.warning(f"⚠️  WARNING: Memory usage {current_memory:.2f} GB >= {self.thresholds.warning_gb} GB")
            # Trigger warning callbacks
            for callback in self.callbacks['warning']:
                try:
                    callback(status)
                except Exception as e:
                    logger.error(f"❌ Warning callback failed: {e}")
        
        # Periodic cleanup
        if time.time() - self.last_cleanup_time > self.cleanup_interval:
            logger.info("🧹 Performing periodic memory cleanup")
            self.force_garbage_collection()
            self.cleanup_shared_memory_leaks()
            self.last_cleanup_time = time.time()
        
        return status
    
    def start_monitoring(self, interval_seconds: float = 30.0):
        """Start continuous memory monitoring."""
        if self.monitoring:
            logger.warning("⚠️  Memory monitoring already active")
            return
        
        logger.info(f"👁️  Starting memory monitoring (interval: {interval_seconds}s)")
        self.monitoring = True
        
        def monitor_loop():
            while self.monitoring:
                try:
                    status = self.check_memory_status()
                    
                    # Log periodic status
                    if status['pressure_level'] != "normal" or time.time() % 300 < interval_seconds:  # Every 5 min
                        # Memory monitoring suppressed for calibration runs
                    
                except Exception as e:
                    logger.error(f"❌ Memory monitoring error: {e}")
                
                time.sleep(interval_seconds)
        
        self.monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        self.monitor_thread.start()
    
    def stop_monitoring(self):
        """Stop memory monitoring."""
        if not self.monitoring:
            return
        
        logger.info("🛑 Stopping memory monitoring")
        self.monitoring = False
        
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5.0)
    
    def get_memory_report(self) -> Dict[str, Any]:
        """Get comprehensive memory report."""
        current_memory = self.get_memory_usage_gb()
        system_memory = self.get_system_memory_usage()
        
        report = {
            'current_usage_gb': current_memory,
            'system_memory': system_memory,
            'thresholds': {
                'warning': self.thresholds.warning_gb,
                'critical': self.thresholds.critical_gb,
                'emergency': self.thresholds.emergency_gb
            },
            'memory_history': self.memory_history.copy(),
            'monitoring_active': self.monitoring
        }
        
        if self.memory_history:
            report['statistics'] = {
                'min_gb': min(self.memory_history),
                'max_gb': max(self.memory_history),
                'avg_gb': np.mean(self.memory_history),
                'current_trend': "increasing" if len(self.memory_history) >= 2 and 
                               self.memory_history[-1] > self.memory_history[-2] else "stable"
            }
        
        return report

# Global memory guardian instance
_memory_guardian = None

def get_memory_guardian() -> MemoryGuardian:
    """Get global memory guardian instance."""
    global _memory_guardian
    if _memory_guardian is None:
        _memory_guardian = MemoryGuardian()
    return _memory_guardian

def setup_memory_protection(thresholds: Optional[MemoryThresholds] = None,
                           monitor_interval: float = 30.0) -> MemoryGuardian:
    """Set up memory protection for the current process."""
    guardian = get_memory_guardian()
    
    # Update thresholds if provided
    if thresholds:
        guardian.thresholds = thresholds
    
    # Start monitoring
    guardian.start_monitoring(monitor_interval)
    
    return guardian
