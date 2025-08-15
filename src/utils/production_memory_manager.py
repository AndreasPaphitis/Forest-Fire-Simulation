#!/usr/bin/env python3
"""
Production Memory Manager for Full-Scale Tenerife Simulation

This module provides enterprise-grade memory management for the 9.3 billion cell
Tenerife forest fire simulation, with real-time monitoring, adaptive optimization,
and emergency protection systems.
"""

import gc
import os
import sys
import time
import threading
import warnings
import numpy as np
from typing import Dict, Any, Optional, List, Tuple, Callable
from dataclasses import dataclass, field
from pathlib import Path
import json

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False
    psutil = None

try:
    from multiprocessing import shared_memory
    HAS_SHARED_MEMORY = True
except ImportError:
    HAS_SHARED_MEMORY = False
    shared_memory = None

from src.utils.logging_utils import get_logger

logger = get_logger(__name__)

@dataclass
class ProductionMemoryThresholds:
    """Production-grade memory thresholds for 512GB+ systems."""
    # Process-level thresholds (per process)
    process_warning_gb: float = 60.0      # Warning at 60GB per process
    process_critical_gb: float = 80.0     # Critical at 80GB per process  
    process_emergency_gb: float = 100.0   # Emergency at 100GB per process
    
    # System-level thresholds (total system memory)
    system_warning_percent: float = 70.0   # Warning at 70% system memory
    system_critical_percent: float = 85.0  # Critical at 85% system memory
    system_emergency_percent: float = 95.0 # Emergency at 95% system memory
    
    # Shared memory thresholds
    shared_memory_max_gb: float = 50.0     # Max shared memory per dataset
    
    # Advanced thresholds
    memory_growth_rate_mb_per_sec: float = 100.0  # Alert if growing >100MB/sec
    fragmentation_warning_percent: float = 30.0   # Alert if >30% fragmented

@dataclass
class MemoryStats:
    """Comprehensive memory statistics."""
    timestamp: float = field(default_factory=time.time)
    
    # Process memory
    process_rss_gb: float = 0.0
    process_vms_gb: float = 0.0
    process_shared_gb: float = 0.0
    
    # System memory
    system_total_gb: float = 0.0
    system_used_gb: float = 0.0
    system_available_gb: float = 0.0
    system_percent: float = 0.0
    
    # Memory growth
    growth_rate_mb_per_sec: float = 0.0
    
    # Sparse storage stats
    sparse_matrices_count: int = 0
    sparse_memory_gb: float = 0.0
    
    # Shared memory stats
    shared_blocks_count: int = 0
    shared_memory_gb: float = 0.0

class ProductionMemoryManager:
    """
    Production-grade memory manager for 9.3B cell forest fire simulation.
    
    Features:
    - Real-time memory monitoring and alerting
    - Adaptive memory optimization based on usage patterns
    - Emergency memory protection and recovery
    - Shared memory leak detection and cleanup
    - Memory usage prediction and forecasting
    - Integration with HPC resource managers
    """
    
    def __init__(self, 
                 thresholds: Optional[ProductionMemoryThresholds] = None,
                 enable_monitoring: bool = True,
                 monitor_interval: float = 10.0):
        
        self.thresholds = thresholds or ProductionMemoryThresholds()
        self.monitor_interval = monitor_interval
        
        # System capabilities check
        if not HAS_PSUTIL:
            logger.warning("⚠️  psutil not available - limited memory monitoring")
        
        # Initialize monitoring
        self.monitoring = False
        self.monitor_thread = None
        self.stats_history: List[MemoryStats] = []
        self.max_history_size = 1000
        
        # Callbacks for different alert levels
        self.callbacks = {
            'warning': [],
            'critical': [],
            'emergency': [],
            'growth_alert': []
        }
        
        # Memory optimization state
        self.last_gc_time = time.time()
        self.gc_interval = 60.0  # Force GC every minute
        self.last_cleanup_time = time.time()
        self.cleanup_interval = 300.0  # Cleanup every 5 minutes
        
        # Emergency state
        self.emergency_mode = False
        self.emergency_callbacks_executed = False
        
        logger.debug("🛡️  Production Memory Manager initialized")
        
        if enable_monitoring:
            self.start_monitoring()
    
    def get_memory_stats(self) -> MemoryStats:
        """Get comprehensive memory statistics."""
        stats = MemoryStats()
        
        if HAS_PSUTIL:
            try:
                # Process memory
                process = psutil.Process()
                memory_info = process.memory_info()
                stats.process_rss_gb = memory_info.rss / (1024**3)
                stats.process_vms_gb = memory_info.vms / (1024**3)
                
                # System memory
                system_memory = psutil.virtual_memory()
                stats.system_total_gb = system_memory.total / (1024**3)
                stats.system_used_gb = system_memory.used / (1024**3)
                stats.system_available_gb = system_memory.available / (1024**3)
                stats.system_percent = system_memory.percent
                
                # Calculate growth rate
                if len(self.stats_history) > 0:
                    last_stats = self.stats_history[-1]
                    time_diff = stats.timestamp - last_stats.timestamp
                    if time_diff > 0:
                        memory_diff_mb = (stats.process_rss_gb - last_stats.process_rss_gb) * 1024
                        stats.growth_rate_mb_per_sec = memory_diff_mb / time_diff
                
            except Exception as e:
                logger.warning(f"⚠️  Error getting memory stats: {e}")
        
        # Estimate sparse storage memory (if available)
        try:
            stats.sparse_memory_gb = self._estimate_sparse_memory()
        except Exception as e:
            logger.debug(f"Could not estimate sparse memory: {e}")
        
        # Check shared memory usage
        try:
            stats.shared_memory_gb, stats.shared_blocks_count = self._get_shared_memory_usage()
        except Exception as e:
            logger.debug(f"Could not get shared memory stats: {e}")
        
        return stats
    
    def _estimate_sparse_memory(self) -> float:
        """Estimate memory used by sparse matrices (rough approximation)."""
        # This is a rough estimate - would need integration with actual sparse storage
        return 0.0
    
    def _get_shared_memory_usage(self) -> Tuple[float, int]:
        """Get shared memory usage statistics."""
        if not HAS_SHARED_MEMORY:
            return 0.0, 0
        
        total_size_gb = 0.0
        block_count = 0
        
        try:
            # On Linux, check /dev/shm for shared memory blocks
            if os.path.exists("/dev/shm"):
                shm_files = list(Path("/dev/shm").glob("psm_*"))
                for shm_file in shm_files:
                    try:
                        size_gb = shm_file.stat().st_size / (1024**3)
                        total_size_gb += size_gb
                        block_count += 1
                    except:
                        continue
        except Exception as e:
            logger.debug(f"Could not check shared memory: {e}")
        
        return total_size_gb, block_count
    
    def add_callback(self, alert_type: str, callback: Callable[[MemoryStats], None]):
        """Add callback for memory alerts."""
        if alert_type in self.callbacks:
            self.callbacks[alert_type].append(callback)
            logger.debug(f"📞 Added {alert_type} memory callback")
    
    def check_memory_status(self) -> Dict[str, Any]:
        """Check memory status and trigger appropriate responses."""
        stats = self.get_memory_stats()
        
        # Add to history
        self.stats_history.append(stats)
        if len(self.stats_history) > self.max_history_size:
            self.stats_history.pop(0)
        
        # Determine alert level
        alert_level = "normal"
        alerts = []
        
        # Process memory alerts
        if stats.process_rss_gb >= self.thresholds.process_emergency_gb:
            alert_level = "emergency"
            alerts.append(f"Process memory: {stats.process_rss_gb:.1f}GB >= {self.thresholds.process_emergency_gb}GB")
        elif stats.process_rss_gb >= self.thresholds.process_critical_gb:
            alert_level = "critical" if alert_level == "normal" else alert_level
            alerts.append(f"Process memory: {stats.process_rss_gb:.1f}GB >= {self.thresholds.process_critical_gb}GB")
        elif stats.process_rss_gb >= self.thresholds.process_warning_gb:
            alert_level = "warning" if alert_level == "normal" else alert_level
            alerts.append(f"Process memory: {stats.process_rss_gb:.1f}GB >= {self.thresholds.process_warning_gb}GB")
        
        # System memory alerts
        if stats.system_percent >= self.thresholds.system_emergency_percent:
            alert_level = "emergency"
            alerts.append(f"System memory: {stats.system_percent:.1f}% >= {self.thresholds.system_emergency_percent}%")
        elif stats.system_percent >= self.thresholds.system_critical_percent:
            alert_level = "critical" if alert_level == "normal" else alert_level
            alerts.append(f"System memory: {stats.system_percent:.1f}% >= {self.thresholds.system_critical_percent}%")
        elif stats.system_percent >= self.thresholds.system_warning_percent:
            alert_level = "warning" if alert_level == "normal" else alert_level
            alerts.append(f"System memory: {stats.system_percent:.1f}% >= {self.thresholds.system_warning_percent}%")
        
        # Memory growth rate alerts
        if abs(stats.growth_rate_mb_per_sec) > self.thresholds.memory_growth_rate_mb_per_sec:
            alerts.append(f"Memory growth: {stats.growth_rate_mb_per_sec:.1f} MB/sec")
            # Trigger growth alert callbacks
            for callback in self.callbacks.get('growth_alert', []):
                try:
                    callback(stats)
                except Exception as e:
                    logger.error(f"❌ Growth alert callback failed: {e}")
        
        # Execute appropriate responses
        response_actions = []
        
        if alert_level == "emergency":
            if not self.emergency_mode:
                logger.error("🚨 EMERGENCY MEMORY SITUATION")
                for alert in alerts:
                    logger.error(f"   {alert}")
                response_actions = self._handle_emergency_memory(stats)
                self.emergency_mode = True
                
                # Execute emergency callbacks
                for callback in self.callbacks.get('emergency', []):
                    try:
                        callback(stats)
                    except Exception as e:
                        logger.error(f"❌ Emergency callback failed: {e}")
        
        elif alert_level == "critical":
            logger.warning("⚠️  CRITICAL MEMORY SITUATION")
            for alert in alerts:
                logger.warning(f"   {alert}")
            response_actions = self._handle_critical_memory(stats)
            
            # Execute critical callbacks
            for callback in self.callbacks.get('critical', []):
                try:
                    callback(stats)
                except Exception as e:
                    logger.error(f"❌ Critical callback failed: {e}")
        
        elif alert_level == "warning":
            logger.warning("⚠️  Memory warning")
            for alert in alerts:
                logger.warning(f"   {alert}")
            response_actions = self._handle_warning_memory(stats)
            
            # Execute warning callbacks
            for callback in self.callbacks.get('warning', []):
                try:
                    callback(stats)
                except Exception as e:
                    logger.error(f"❌ Warning callback failed: {e}")
        
        # Periodic maintenance
        current_time = time.time()
        if current_time - self.last_gc_time > self.gc_interval:
            response_actions.append("periodic_gc")
            self._force_garbage_collection()
            self.last_gc_time = current_time
        
        if current_time - self.last_cleanup_time > self.cleanup_interval:
            response_actions.append("periodic_cleanup")
            self._cleanup_shared_memory()
            self.last_cleanup_time = current_time
        
        return {
            'stats': stats,
            'alert_level': alert_level,
            'alerts': alerts,
            'response_actions': response_actions,
            'emergency_mode': self.emergency_mode
        }
    
    def _handle_warning_memory(self, stats: MemoryStats) -> List[str]:
        """Handle warning-level memory pressure."""
        actions = []
        
        # Light garbage collection
        collected = self._force_garbage_collection()
        if collected > 0:
            actions.append(f"gc_freed_{collected}_objects")
        
        return actions
    
    def _handle_critical_memory(self, stats: MemoryStats) -> List[str]:
        """Handle critical-level memory pressure."""
        actions = []
        
        # Aggressive garbage collection
        collected = self._force_garbage_collection()
        actions.append(f"aggressive_gc_freed_{collected}_objects")
        
        # Shared memory cleanup
        cleaned = self._cleanup_shared_memory()
        if cleaned > 0:
            actions.append(f"cleaned_{cleaned}_shared_blocks")
        
        # Try to release memory back to OS
        self._release_memory_to_os()
        actions.append("memory_release_to_os")
        
        return actions
    
    def _handle_emergency_memory(self, stats: MemoryStats) -> List[str]:
        """Handle emergency-level memory pressure."""
        actions = []
        
        logger.error("🚨 EXECUTING EMERGENCY MEMORY PROTOCOL")
        
        # 1. Multiple rounds of aggressive GC
        total_collected = 0
        for i in range(5):
            collected = self._force_garbage_collection()
            total_collected += collected
            if collected == 0:
                break
        actions.append(f"emergency_gc_freed_{total_collected}_objects")
        
        # 2. Clean all shared memory
        cleaned = self._cleanup_shared_memory()
        actions.append(f"emergency_cleaned_{cleaned}_shared_blocks")
        
        # 3. Force memory release
        self._release_memory_to_os()
        actions.append("emergency_memory_release")
        
        # 4. Try to compact sparse matrices (if available)
        try:
            compacted = self._compact_sparse_storage()
            if compacted:
                actions.append("sparse_storage_compacted")
        except Exception as e:
            logger.error(f"❌ Sparse compaction failed: {e}")
        
        # 5. Log emergency state for debugging
        self._log_emergency_state(stats)
        actions.append("emergency_state_logged")
        
        return actions
    
    def _force_garbage_collection(self) -> int:
        """Force comprehensive garbage collection."""
        collected = 0
        
        # Multiple GC passes
        for i in range(3):
            current = gc.collect()
            collected += current
            if current == 0:
                break
        
        if collected > 0:
            logger.info(f"🗑️  Garbage collection freed {collected} objects")
        
        return collected
    
    def _cleanup_shared_memory(self) -> int:
        """Clean up orphaned shared memory blocks."""
        cleaned = 0
        
        try:
            if os.path.exists("/dev/shm"):
                import glob
                patterns = ["/dev/shm/psm_*", "/dev/shm/wnsm_*"]
                
                for pattern in patterns:
                    blocks = glob.glob(pattern)
                    for block_path in blocks:
                        try:
                            # Check if block is old (>1 hour)
                            stat = os.stat(block_path)
                            age_hours = (time.time() - stat.st_mtime) / 3600
                            
                            if age_hours > 1:
                                os.remove(block_path)
                                cleaned += 1
                                logger.debug(f"🧹 Cleaned: {os.path.basename(block_path)}")
                        except Exception:
                            continue
        except Exception as e:
            logger.warning(f"⚠️  Shared memory cleanup error: {e}")
        
        if cleaned > 0:
            logger.info(f"🧹 Cleaned {cleaned} orphaned shared memory blocks")
        
        return cleaned
    
    def _release_memory_to_os(self):
        """Try to release memory back to OS."""
        try:
            import ctypes
            libc = ctypes.CDLL("libc.so.6")
            libc.malloc_trim(0)
            logger.debug("💾 Released memory back to OS")
        except Exception:
            logger.debug("Memory release not available (non-Linux system)")
    
    def _compact_sparse_storage(self) -> bool:
        """Try to compact sparse storage (placeholder - needs integration)."""
        # This would need integration with actual sparse storage system
        # For now, just return False
        return False
    
    def _log_emergency_state(self, stats: MemoryStats):
        """Log detailed emergency state for debugging."""
        logger.error("🚨 EMERGENCY MEMORY STATE DUMP:")
        logger.error(f"   Process RSS: {stats.process_rss_gb:.2f} GB")
        logger.error(f"   Process VMS: {stats.process_vms_gb:.2f} GB")
        logger.error(f"   System Used: {stats.system_used_gb:.2f} GB / {stats.system_total_gb:.2f} GB ({stats.system_percent:.1f}%)")
        logger.error(f"   Growth Rate: {stats.growth_rate_mb_per_sec:.1f} MB/sec")
        logger.error(f"   Shared Memory: {stats.shared_memory_gb:.2f} GB ({stats.shared_blocks_count} blocks)")
        
        # Save state to file for analysis
        try:
            emergency_file = f"emergency_memory_state_{int(time.time())}.json"
            with open(emergency_file, 'w') as f:
                json.dump({
                    'timestamp': stats.timestamp,
                    'process_rss_gb': stats.process_rss_gb,
                    'process_vms_gb': stats.process_vms_gb,
                    'system_total_gb': stats.system_total_gb,
                    'system_used_gb': stats.system_used_gb,
                    'system_percent': stats.system_percent,
                    'growth_rate_mb_per_sec': stats.growth_rate_mb_per_sec,
                    'shared_memory_gb': stats.shared_memory_gb,
                    'shared_blocks_count': stats.shared_blocks_count
                }, f, indent=2)
            logger.error(f"   Emergency state saved to: {emergency_file}")
        except Exception as e:
            logger.error(f"   Could not save emergency state: {e}")
    
    def start_monitoring(self):
        """Start continuous memory monitoring."""
        if self.monitoring:
            logger.warning("⚠️  Memory monitoring already active")
            return
        
        logger.debug(f"👁️  Starting production memory monitoring (interval: {self.monitor_interval}s)")
        self.monitoring = True
        
        def monitor_loop():
            while self.monitoring:
                try:
                    status = self.check_memory_status()
                    
                    # Log periodic status (every 5 minutes or on alerts)
                    should_log = (status['alert_level'] != "normal" or 
                                len(self.stats_history) % (300 // self.monitor_interval) == 0)
                    
                    if should_log:
                        stats = status['stats']
                        logger.info(f"📊 Memory: Process={stats.process_rss_gb:.1f}GB, "
                                   f"System={stats.system_percent:.1f}%, "
                                   f"Growth={stats.growth_rate_mb_per_sec:.1f}MB/s, "
                                   f"Level={status['alert_level']}")
                
                except Exception as e:
                    logger.error(f"❌ Memory monitoring error: {e}")
                
                time.sleep(self.monitor_interval)
        
        self.monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        self.monitor_thread.start()
    
    def stop_monitoring(self):
        """Stop memory monitoring."""
        if not self.monitoring:
            return
        
        logger.info("🛑 Stopping production memory monitoring")
        self.monitoring = False
        
        if self.monitor_thread:
            self.monitor_thread.join(timeout=10.0)
    
    def get_memory_report(self) -> Dict[str, Any]:
        """Get comprehensive memory report."""
        current_stats = self.get_memory_stats()
        
        # Calculate statistics from history
        process_memory_history = [s.process_rss_gb for s in self.stats_history]
        system_memory_history = [s.system_percent for s in self.stats_history]
        
        report = {
            'current': {
                'process_rss_gb': current_stats.process_rss_gb,
                'system_percent': current_stats.system_percent,
                'growth_rate_mb_per_sec': current_stats.growth_rate_mb_per_sec,
                'shared_memory_gb': current_stats.shared_memory_gb
            },
            'thresholds': {
                'process_warning_gb': self.thresholds.process_warning_gb,
                'process_critical_gb': self.thresholds.process_critical_gb,
                'process_emergency_gb': self.thresholds.process_emergency_gb,
                'system_warning_percent': self.thresholds.system_warning_percent,
                'system_critical_percent': self.thresholds.system_critical_percent,
                'system_emergency_percent': self.thresholds.system_emergency_percent
            },
            'statistics': {},
            'emergency_mode': self.emergency_mode,
            'monitoring_active': self.monitoring
        }
        
        if process_memory_history:
            report['statistics'] = {
                'process_memory': {
                    'min_gb': min(process_memory_history),
                    'max_gb': max(process_memory_history),
                    'avg_gb': sum(process_memory_history) / len(process_memory_history)
                },
                'system_memory': {
                    'min_percent': min(system_memory_history),
                    'max_percent': max(system_memory_history),
                    'avg_percent': sum(system_memory_history) / len(system_memory_history)
                }
            }
        
        return report

# Global production memory manager instance
_production_memory_manager = None

def get_production_memory_manager() -> ProductionMemoryManager:
    """Get global production memory manager instance."""
    global _production_memory_manager
    if _production_memory_manager is None:
        _production_memory_manager = ProductionMemoryManager()
    return _production_memory_manager

def setup_production_memory_protection(
    thresholds: Optional[ProductionMemoryThresholds] = None,
    monitor_interval: float = 10.0
) -> ProductionMemoryManager:
    """Set up production-grade memory protection for full-scale simulation."""
    
    # Use production thresholds optimized for 512GB+ systems
    if thresholds is None:
        thresholds = ProductionMemoryThresholds(
            process_warning_gb=80.0,    # Higher thresholds for production
            process_critical_gb=120.0,
            process_emergency_gb=150.0,
            system_warning_percent=75.0,
            system_critical_percent=90.0,
            system_emergency_percent=95.0
        )
    
    manager = ProductionMemoryManager(
        thresholds=thresholds,
        enable_monitoring=True,
        monitor_interval=monitor_interval
    )
    
    logger.debug("🛡️  Production memory protection activated")
    
    return manager
