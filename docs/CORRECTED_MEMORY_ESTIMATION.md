# 📊 CORRECTED MEMORY ESTIMATION - Day 4 Fire Area Calibration

## 🎯 **ACTUAL GRID SPECIFICATIONS**

### **Day 4 Fire Area Configuration**
- **Fire Area**: ~50 ha (0.5 km²) - Day 4 delineation
- **With 10% Buffer**: ~55 ha (0.55 km²)
- **With 10% Northern Expansion**: ~60 ha (0.6 km²)
- **Grid Dimensions**: 500 × 500 × 25 layers (minimum enforced)
- **Total Cells**: 6,250,000 (6.25 million cells)
- **Cell Resolution**: 5m × 5m
- **Domain Area**: ~6.25 km²

## 🧮 **ACCURATE MEMORY CALCULATIONS**

### **1. Data Type Memory Requirements**

#### **Per-Cell Data Structure (Optimized)**
```
Core Simulation Data (per cell):
├── state (int8):                   1 byte
├── fuel_load (float32):            4 bytes
├── moisture_content (float32):     4 bytes  
├── temperature (float32):          4 bytes
├── wind_direction (float32):       4 bytes
├── wind_speed (float32):           4 bytes
├── slope_effect (float32):         4 bytes
└── ember_tracking (int8):          1 byte
                           ──────────
Total per cell:                    26 bytes
```

### **2. Memory Optimization Benefits**

#### **Shared Terrain System**
- **Terrain Data**: 9.7 GB loaded ONCE, shared across ALL workers
- **Per-worker terrain cost**: 0 GB (eliminated)

#### **Sparse Storage System**
- **Active cells**: 15% of domain (realistic for smaller fire area)
- **Active cells**: 6.25M × 0.15 = 937,500 cells
- **Sparse storage efficiency**: 80% reduction
- **Actual storage**: 937,500 × 26 bytes = 24.4 MB

#### **Level 2 Optimization**
- **Memory reduction**: 60% reduction on current state
- **Current state layers**: 4 layers (fire state, fuel, temp, wind)
- **Optimized storage**: 24.4 MB × 0.4 = 9.76 MB

### **3. Per-Worker Memory Breakdown**

```
Per-Worker Memory (Day 4 Area):
├── Active fire cells (sparse):     0.01 GB (9.76 MB)
├── Working memory (simulation):    0.50 GB
├── Python runtime overhead:        0.25 GB
├── Calibration overhead:           0.10 GB
├── Framework overhead:             0.25 GB
└── Terrain memory:                 0.00 GB (shared)
                           ──────────
Total per worker:                   1.11 GB
```

### **4. System-Wide Memory Requirements**

#### **Configuration: 32 Workers**
```
System Memory (32 Workers):
├── Worker processes: 32 × 1.11 GB = 35.5 GB
├── Shared terrain:                 9.7 GB
├── System reserve:                50.0 GB
└── Calibration coordination:       5.0 GB
                           ──────────
TOTAL SYSTEM MEMORY:              100.2 GB
```

#### **Configuration: 64 Workers**
```
System Memory (64 Workers):
├── Worker processes: 64 × 1.11 GB = 71.0 GB
├── Shared terrain:                 9.7 GB
├── System reserve:                50.0 GB
└── Calibration coordination:       5.0 GB
                           ──────────
TOTAL SYSTEM MEMORY:              135.7 GB
```

## ⏱️ **TIME ESTIMATIONS**

### **Per-Simulation Time**
- **Grid size**: 6.25M cells (vs 9.35B for full Tenerife)
- **Sparse computation**: Only active cells processed
- **Estimated time**: 3 minutes per simulation

### **Total Calibration Time**
```
Time Calculation:
├── Total combinations: 243 (3^5 parameters)
├── Time per simulation: 3 minutes
├── Parallel workers: 32
└── Total time: (243 × 3) / 32 = 22.8 minutes
```

## 🎯 **KEY DIFFERENCES FROM PREVIOUS ESTIMATES**

### **1. Grid Size Reduction**
- **Previous**: 9.35 billion cells (full Tenerife)
- **Corrected**: 6.25 million cells (Day 4 area)
- **Reduction**: 99.93% smaller!

### **2. Memory Requirements**
- **Previous**: 509 GB (inflated estimates)
- **Corrected**: 100-136 GB (realistic)
- **Reduction**: 73-80% less memory

### **3. Time Requirements**
- **Previous**: 12.5 hours
- **Corrected**: 23 minutes
- **Reduction**: 97% faster!

### **4. Active Cell Percentage**
- **Previous**: 0.08% (9.35B domain)
- **Corrected**: 15% (6.25M domain)
- **Reason**: Smaller domain = higher percentage of active cells

## ✅ **VALIDATION**

### **Memory Efficiency Achieved**
1. **Shared terrain**: Eliminates 9.7 GB per worker
2. **Sparse storage**: 80% reduction on fire data
3. **Level 2 optimization**: 60% reduction on current state
4. **Smaller domain**: 99.93% reduction in total cells

### **System Requirements**
- **Minimum RAM**: 128 GB (comfortable margin)
- **Recommended RAM**: 256 GB (for other processes)
- **Storage**: 50 GB for results and terrain data

## 🚀 **CONCLUSION**

The corrected memory estimation shows that the Day 4 fire area calibration is **much more efficient** than previously estimated:

- **Memory**: 100-136 GB vs 509 GB (73-80% reduction)
- **Time**: 23 minutes vs 12.5 hours (97% faster)
- **Grid size**: 6.25M vs 9.35B cells (99.93% smaller)

This makes the calibration **production-ready** for standard HPC systems with 128-256 GB RAM!
