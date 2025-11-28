# 🏔️ Production Deployment Guide - Full Tenerife Calibration

## Grid Specifications
- **Domain**: Full Tenerife Island
- **Grid Size**: 15,121 × 24,741 × 25 layers
- **Total Cells**: 9,352,716,525 (9.35 billion cells)
- **Memory Requirement**: 200-400 GB (optimized sparse storage)

## 🚨 Critical Memory Fixes Applied

### Memory Leak Resolution
✅ **Fixed shared memory copying** - Prevents memory doubling
✅ **Added sparse-only enforcement** - Blocks dense array creation  
✅ **Implemented production memory manager** - Real-time OOM prevention
✅ **Enhanced terrain loading protection** - Prevents duplicate loading

### Production Safety Features
- 🛡️ **Memory Guardian**: Real-time monitoring with emergency protocols
- 🚨 **OOM Prevention**: Automatic memory cleanup and alerts
- 📊 **Memory Streaming**: Efficient handling of massive datasets
- 🔧 **HPC Optimization**: NUMA-aware memory management

## 🎯 Deployment Steps

### Step 1: Pre-Deployment Verification
```bash
# Check system memory
free -h

# Verify required packages
python -c "import scipy; print('SciPy OK')"
python -c "import numpy; print('NumPy OK')"
python -c "import psutil; print('psutil OK')"

# Test emergency config first
python scripts/immediate_memory_fix.py
```

### Step 2: HPC Resource Allocation
```bash
# Submit production job (4 nodes × 512GB = 2TB total)
sbatch hpc_deployment/tenerife_production.slurm

# Monitor job
squeue -u $USER
```

### Step 3: Memory Monitoring
```bash
# Real-time memory monitoring
watch -n 5 'free -h && ps aux --sort=-%mem | head -10'

# Check shared memory usage
ls -lah /dev/shm/psm_*

# Monitor job logs
tail -f tenerife_calibration_*.out
```

## 📊 Memory Configuration

### Minimum Requirements
- **Nodes**: 4 high-memory nodes
- **RAM per node**: 512 GB
- **Total system memory**: 2 TB
- **Storage**: 1 TB fast SSD/NVMe

### Optimal Configuration
- **Nodes**: 8 high-memory nodes  
- **RAM per node**: 1 TB
- **Total system memory**: 8 TB
- **Storage**: 5 TB NVMe with RAID

### Memory Allocation Strategy
```json
{
  "per_worker_limits": {
    "process_memory_gb": 60,
    "shared_terrain_gb": 10,
    "sparse_storage_gb": 40,
    "overhead_gb": 10
  },
  "system_reserves": {
    "os_reserve_gb": 50,
    "emergency_buffer_gb": 100,
    "fragmentation_buffer_gb": 50
  }
}
```

## ⚙️ Configuration Files

### 1. Production Configuration
**File**: `hpc_deployment/full_tenerife_production.json`

Key settings:
- `grid_size`: [15121, 24741] - Full Tenerife domain
- `memory_optimization_level`: 2 - Maximum optimization
- `use_sparse_storage`: true - CRITICAL for memory efficiency
- `force_sparse_only`: true - Prevents dense array creation
- `shared_terrain_readonly`: true - Memory-safe shared access

### 2. SLURM Job Script
**File**: `hpc_deployment/tenerife_production.slurm`

Features:
- High-memory partition allocation
- Memory monitoring and alerts
- Emergency cleanup procedures
- Result archiving and debugging

### 3. Memory Protection
**Module**: `src.utils.production_memory_manager`

Capabilities:
- Real-time memory monitoring
- Emergency memory recovery
- Shared memory leak cleanup
- Performance optimization

## 🔍 Monitoring and Debugging

### Real-Time Monitoring
```bash
# Memory usage by process
htop -u $USER

# System memory overview  
free -h && echo "---" && df -h

# Shared memory blocks
ls -la /dev/shm/ | grep psm

# Job resource usage
sacct -j $SLURM_JOB_ID --format=JobID,JobName,MaxRSS,Elapsed
```

### Emergency Procedures
```bash
# If OOM detected, run emergency cleanup
python scripts/immediate_memory_fix.py

# Check for memory leaks
find /dev/shm -name "psm_*" -ls

# Force memory release
echo 3 > /proc/sys/vm/drop_caches  # Requires root
```

### Debug Information Collection
```bash
# Collect system state
uname -a > debug_info.txt
free -h >> debug_info.txt
lscpu >> debug_info.txt
cat /proc/meminfo >> debug_info.txt

# Process memory maps
cat /proc/$PID/smaps > process_memory_map.txt

# Shared memory info
ipcs -m >> debug_info.txt
```

## 📈 Performance Optimization

### Memory Efficiency Techniques
1. **Ultra-Sparse Storage**: Only store non-zero cells
2. **Memory Streaming**: Load data on-demand  
3. **Chunk Processing**: Process terrain in tiles
4. **Compression**: Compress inactive regions
5. **Memory Pooling**: Pre-allocate memory blocks

### HPC-Specific Optimizations
```bash
# NUMA optimization
export OMP_PROC_BIND=true
export OMP_PLACES=cores

# Memory allocation
export MALLOC_TRIM_THRESHOLD_=0
export MALLOC_MMAP_THRESHOLD_=65536

# Huge pages (if available)
export LIBHUGETLBFS_MORECORE=yes
```

## 🚨 Emergency Protocols

### OOM Prevention Hierarchy
1. **Level 1 (60GB)**: Warning alerts, light GC
2. **Level 2 (80GB)**: Aggressive cleanup, shared memory purge
3. **Level 3 (100GB)**: Emergency protocols, checkpoint creation
4. **Level 4 (120GB)**: Process termination with state save

### Emergency Actions
```python
# Automatic emergency response
memory_manager.add_callback('emergency', lambda stats: [
    trigger_checkpoint(),
    cleanup_shared_memory(),
    compress_sparse_storage(),
    notify_administrators()
])
```

## ✅ Success Indicators

### Memory Usage Patterns
- **Startup**: <10 GB (initialization)
- **Terrain Loading**: 10-20 GB (shared memory setup)
- **Simulation**: 20-60 GB (sparse processing)
- **Peak Usage**: <80 GB (safety threshold)

### Performance Metrics
- **Memory Growth**: <10 MB/sec sustained
- **Shared Memory**: Stable at ~10 GB
- **GC Frequency**: <1 per minute
- **Simulation Progress**: Steady timestep advancement

### Log Messages to Watch For
✅ `"Using shared terrain data from memory"` - Good shared memory
✅ `"MASSIVE GRID DETECTED"` - Sparse-only mode activated  
✅ `"Terrain data already loaded"` - No duplicate loading
✅ `"Memory: Process=X GB, Level=normal"` - Healthy operation

❌ `"SciPy required for massive grid"` - Missing dependency
❌ `"Memory growth: X MB/sec"` - Memory leak detected
❌ `"EMERGENCY MEMORY SITUATION"` - Critical state

## 🎯 Deployment Checklist

### Pre-Deployment
- [ ] System has 512GB+ RAM per node
- [ ] SciPy and psutil installed
- [ ] Shared memory fixes applied
- [ ] Production config validated
- [ ] Emergency scripts tested

### During Deployment
- [ ] Memory monitoring active
- [ ] Sparse-only mode confirmed
- [ ] Shared memory stable
- [ ] No dense arrays created
- [ ] Progress indicators healthy

### Post-Deployment
- [ ] Results archived
- [ ] Memory logs analyzed
- [ ] Performance metrics recorded
- [ ] Cleanup completed
- [ ] Lessons learned documented

## 📞 Support and Troubleshooting

### Common Issues
1. **OOM Kill**: Use emergency config first, check memory limits
2. **Segmentation Fault**: Verify sparse-only mode, check SciPy
3. **Slow Performance**: Monitor memory growth, enable streaming
4. **Import Errors**: Fix Python paths, verify module installation

### Emergency Contacts
- **System Administrator**: For HPC resource issues
- **Memory Expert**: For optimization consultation  
- **Research Supervisor**: For scientific guidance

The production deployment system is now ready for the full 9.35 billion cell Tenerife calibration simulation! 🏔️🔥
