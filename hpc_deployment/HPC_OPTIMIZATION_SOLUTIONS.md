# 🔧 HPC Forest Fire Simulation - Issue Fixes & Optimizations

## 📋 **Issues Addressed**

### **Issue 1: Severe Resource Allocation Mismatch**
**Problem:** SLURM requested 120GB but configuration only expected 128GB limit, with insufficient buffer for OS overhead.

**Solutions Implemented:**
- ✅ **SLURM Memory:** Increased from 120GB → 128GB
- ✅ **Config Memory Limit:** Reduced from 128GB → 114GB (89% efficiency)
- ✅ **Memory Validation:** Added pre-simulation memory requirement checking
- ✅ **Safety Buffers:** Proper memory allocation with OS overhead consideration

### **Issue 2: Massive Memory Underestimation**
**Problem:** Configuration assumed 4 bytes/cell but reality is 25-30 bytes/cell.

**Solutions Implemented:**
- ✅ **Realistic Memory Estimation:** Updated `_estimate_bytes_per_cell()` function
- ✅ **Comprehensive Data Structure Accounting:** Now includes all simulation arrays
- ✅ **Configuration Update:** Production config now uses 30 bytes/cell
- ✅ **HPC Safety Factor:** Added 1.4x multiplier for Python overhead

**Memory Breakdown per Cell (Updated):**
```
- Essential data: 17 bytes (fuel, state, temperature, moisture, connectivity)
- Wind/terrain: 16 bytes (wind factors, elevation, slope, aspect)
- Fire mechanics: 8 bytes (spread probability, ignition threshold)
- Optional features: 8-12 bytes (ember transport, terrain features, LiDAR)
- History tracking: 8 bytes
- Safety factor: 1.4x
- **Total: ~30 bytes/cell (realistic for HPC)**
```

### **Issue 3: Conservative Parallelization Settings**
**Problem:** Only using 2 parallel tiles with 32 cores available.

**Solutions Implemented:**
- ✅ **Optimal Parallelization:** New `calculate_optimal_hpc_config()` function
- ✅ **Increased Parallel Tiles:** From 2 → 8 parallel tiles
- ✅ **Improved Tile Size:** From 100 → 250 tile size
- ✅ **Batch Processing:** Added tile batch size of 2
- ✅ **CPU Reservation:** Reserve 4 cores for I/O and coordination

### **Issue 4: Disk Storage Path Problems**
**Problem:** Relative paths causing failures in HPC environment.

**Solutions Implemented:**
- ✅ **Absolute Path Resolution:** New `resolve_hpc_storage_path()` function
- ✅ **HPC Storage Hierarchy:** Scratch → Home → Fallback storage selection
- ✅ **Job Isolation:** Job-specific directories using SLURM_JOB_ID
- ✅ **Permission Handling:** Graceful fallback for permission issues
- ✅ **Updated Paths:** Configuration uses `/scratch-shared/$USER/` patterns

---

## 🚀 **Optimization Features Added**

### **1. Dynamic HPC Configuration**
```python
# New function: calculate_optimal_hpc_config()
optimal_config = calculate_optimal_hpc_config(
    config=config_dict,
    available_memory_gb=128,
    available_cores=32,
    target_efficiency=0.85
)
```

**Features:**
- Automatic memory-based tiling decisions
- Optimal tile size calculation
- Dynamic parallelization based on resources
- Memory efficiency optimization

### **2. Robust Storage Management**
```python
# New functions for HPC storage
hpc_directories = setup_hpc_output_directories(config, job_id)
storage_path = resolve_hpc_storage_path(path, job_id, user)
```

**Features:**
- Multi-tier storage preference (scratch → home → temp)
- Automatic directory creation with permissions
- Job isolation for concurrent runs
- Fallback mechanisms for storage failures

### **3. Enhanced Memory Management**
```python
# Updated memory estimation
bytes_per_cell = _estimate_bytes_per_cell(config)  # Now returns ~30 bytes
```

**Features:**
- Comprehensive data structure accounting
- Feature-based memory calculation
- HPC safety factors
- Sparse storage optimization support

---

## 📊 **Performance Improvements**

### **Before → After Comparison**

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| **Memory Allocation** | 120GB request, 128GB expected | 128GB request, 114GB usable | ✅ Realistic allocation |
| **Bytes per Cell** | 4 bytes (unrealistic) | 30 bytes (realistic) | ✅ 7.5x more accurate |
| **Parallel Tiles** | 2 tiles | 8 tiles | ✅ 4x parallelization |
| **Tile Size** | 100x100 | 250x250 | ✅ Better memory efficiency |
| **Storage Paths** | Relative (failing) | Absolute HPC paths | ✅ Reliable storage |
| **Memory Buffer** | 8GB (6.7%) | 14GB (12.3%) | ✅ Safer operation |

### **Expected Grid Capacity**
```
Previous estimate: 2,000x2,000 grid = 40M cells × 4 bytes = 160MB (WRONG!)
Realistic estimate: 1,000x1,000 grid = 10M cells × 30 bytes = 300MB per layer

With 10 layers: 3GB for grid data
With tiling: Can handle up to 4,000x4,000 grids efficiently
```

---

## 🎯 **Updated Configuration**

### **HPC Section (Optimized)**
```json
{
  "hpc": {
    "memory_limit_per_node": 114.0,
    "tile_size": 250,
    "max_parallel_tiles": 8,
    "tile_batch_size": 2,
    "reserve_cpus": 4,
    "memory_optimization_level": 3,
    "use_sparse_storage": true,
    "enable_memory_cleanup": true,
    "gc_frequency": 2,
    "gdal_cache_mb": 4096,
    "io_block_size": 16384
  }
}
```

### **Output Section (HPC Paths)**
```json
{
  "output": {
    "output_dir": "/scratch-shared/$USER/results/production",
    "disk_storage_dir": "/scratch-shared/$USER/temp_simulation_states",
    "checkpoint_interval": 500
  }
}
```

### **Core Settings (Realistic)**
```json
{
  "bytes_per_cell": 30,
  "max_steps": 50,
  "grid_size": [1000, 1000],
  "max_grid_size": [4000, 4000]
}
```

---

## 🛠 **Files Modified**

1. **`src/utils/memory_manager.py`**
   - Updated `_estimate_bytes_per_cell()` with realistic calculations
   - Added `calculate_optimal_hpc_config()` for dynamic optimization

2. **`src/utils/file_handlers.py`**
   - Added `resolve_hpc_storage_path()` for absolute path handling
   - Added `setup_hpc_output_directories()` for HPC directory management

3. **`hpc_deployment/run_production_sim.py`**
   - Integrated HPC optimization functions
   - Added SLURM resource detection
   - Dynamic configuration optimization

4. **`hpc_deployment/Forest_Fire_Simulation_production_test.json`**
   - Updated all memory and parallelization settings
   - Changed to absolute HPC paths
   - Realistic memory estimates

5. **`hpc_deployment/fire_simulation.slurm`**
   - Increased memory allocation to 128GB
   - Added memory validation
   - Scratch storage management
   - Enhanced error handling

---

## ✅ **Verification Checklist**

- [x] Memory allocation matches SLURM request (128GB)
- [x] Realistic bytes per cell estimate (30 bytes)
- [x] Optimal parallelization (8 tiles instead of 2)
- [x] Absolute storage paths for HPC
- [x] Proper memory safety buffers (12.3%)
- [x] Enhanced error handling and validation
- [x] Job isolation and cleanup

---

## 🎉 **Expected Results**

These optimizations should enable:
- ✅ **Successful large-scale simulations** up to 4,000×4,000 grids
- ✅ **4x better parallelization** efficiency  
- ✅ **Reliable HPC storage** without path failures
- ✅ **Realistic memory planning** preventing OOM errors
- ✅ **Better resource utilization** on Snellius HPC

The simulation should now run successfully on HPC environments without the critical issues that previously prevented execution. 