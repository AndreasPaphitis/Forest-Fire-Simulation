# 🏔️ Full Scale Tenerife Grid Memory Analysis

## Grid Specifications
- **Dimensions**: 15,121 × 24,741 × 25 layers
- **Total Cells**: 9,352,716,525 cells (9.35 billion)
- **Domain**: Full Tenerife Island
- **Resolution**: ~10m per cell

## Memory Requirements Analysis

### Base Memory Calculation
```
Grid cells: 15,121 × 24,741 = 374,078,361 surface cells
Total cells: 374,078,361 × 25 layers = 9,351,959,025 cells

Per-cell data requirements:
- Fire state (uint8): 1 byte
- Fuel load (float32): 4 bytes  
- Temperature (float32): 4 bytes
- Moisture (float32): 4 bytes
- Wind velocity components (2×float32): 8 bytes
Total per cell: ~21 bytes

Base grid memory: 9.35B × 21 bytes = 196.4 GB
```

### Terrain Data Memory
```
Terrain arrays (15,121 × 24,741 each):
- elevation (float32): 1.43 GB
- slope (float32): 1.43 GB  
- aspect (float32): 1.43 GB
- barranco_mask (uint8): 0.36 GB
- barranco_directions (float32): 1.43 GB
- depression_mask (uint8): 0.36 GB
- wind_channeling_mask (uint8): 0.36 GB
- wind_amplification (float32): 1.43 GB
- wind_direction_modification (float32): 1.43 GB

Total terrain memory: 9.66 GB
```

### Total Memory Requirements
```
Sparse Storage (Optimized):
- Active fire cells (~1% of grid): 2.0 GB
- Terrain data: 9.7 GB
- Simulation engine overhead: 5.0 GB
- Shared memory overhead: 3.0 GB
TOTAL OPTIMIZED: ~20 GB per process

Dense Storage (Worst Case):
- Full grid data: 196.4 GB
- Terrain data: 9.7 GB  
- Engine overhead: 20.0 GB
- Memory fragmentation: 50.0 GB
TOTAL WORST CASE: ~276 GB per process
```

## Critical Memory Challenges

### 1. Shared Memory Copying Issue
**Problem**: Each worker process copying 9.7 GB terrain data
**Impact**: 32 workers × 9.7 GB = 310 GB just for terrain
**Solution**: Use shared memory views, not copies

### 2. Dense Array Allocation
**Problem**: Accidentally creating dense 196 GB arrays
**Impact**: Immediate OOM kill
**Solution**: Enforce sparse-only mode from initialization

### 3. Memory Fragmentation
**Problem**: Large memory allocations causing fragmentation
**Impact**: Unable to allocate even when total memory available
**Solution**: Memory pooling and pre-allocation

## Production Memory Strategy

### Phase 1: Immediate Fixes (CRITICAL)
1. **Fix shared memory copying** ✅ (Already implemented)
2. **Prevent dense array creation** 
3. **Add memory monitoring**
4. **Optimize sparse storage efficiency**

### Phase 2: Advanced Optimization
1. **Memory streaming for terrain data**
2. **Chunked processing with overlap**
3. **Dynamic memory management**
4. **HPC-optimized memory allocation**

### Phase 3: Production Deployment
1. **Large memory node allocation** 
2. **NUMA-aware memory management**
3. **Memory monitoring and alerts**
4. **Automatic checkpointing on memory pressure**

## Recommended HPC Configuration

### Memory Requirements
```
Minimum: 256 GB RAM per node
Recommended: 512 GB RAM per node
Optimal: 1 TB RAM per node

Workers per node:
- 256 GB: 8-12 workers max
- 512 GB: 16-24 workers max  
- 1 TB: 32-48 workers max
```

### Node Specifications
```
CPU: 64+ cores (Intel Xeon or AMD EPYC)
RAM: 512 GB - 1 TB DDR4/DDR5
Storage: NVMe SSD for temporary data
Network: High-speed interconnect for data sharing
```

## Memory Optimization Strategies

### 1. Ultra-Sparse Storage
- Store only non-zero/active cells
- Use compressed sparse matrices
- Dynamic memory allocation

### 2. Memory Streaming
- Load terrain data on-demand
- Use memory-mapped files
- Cache frequently accessed regions

### 3. Hierarchical Memory Management
- Fast memory for active fire regions
- Slower memory for inactive regions
- Disk storage for historical data

### 4. Adaptive Memory Usage
- Monitor memory pressure in real-time
- Adjust processing strategies dynamically
- Emergency memory release procedures

## Implementation Priority

### Immediate (Next 24 hours)
1. Fix remaining memory leaks
2. Implement strict sparse-only mode
3. Add production memory monitoring
4. Create optimized HPC configuration

### Short-term (Next week)
1. Implement memory streaming
2. Add chunked processing capability
3. Optimize sparse matrix operations
4. Add automatic checkpointing

### Long-term (Research phase)
1. GPU acceleration for sparse operations
2. Distributed memory management
3. Advanced compression techniques
4. Machine learning-based memory prediction
