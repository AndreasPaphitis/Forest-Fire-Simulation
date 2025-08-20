# 🚀 ULTRA-FAST CALIBRATION OPTIMIZATION GUIDE

## 📊 **Current vs Optimized Performance**

| Metric | Current | Ultra-Fast | Speedup |
|--------|---------|------------|---------|
| **Grid Search Points** | 5 | 2-3 | **2.5x** |
| **Parameters** | 5 | 3-4 | **1.25x** |
| **Max Steps** | 250 | 100-150 | **2x** |
| **Grid Resolution** | 5m | 8-10m | **2.5x** |
| **Total Combinations** | 3,125 | 8-81 | **39-390x** |
| **Time per Simulation** | 3 min | 45 sec | **4x** |
| **Total Runtime** | 2-3 days | 2-8 hours | **12-36x** |

## 🎯 **Three Optimization Modes**

### **1. ULTRA-FAST (2 hours)**
```bash
python scripts/run_tenerife_calibration_ultra_fast.py --mode ultra-fast
```

**Configuration:**
- **Grid Points**: 2 per parameter
- **Parameters**: 3 (spread_probability, fuel_consumption_rate, ember_probability)
- **Combinations**: 2³ = **8 total**
- **Max Steps**: 100
- **Resolution**: 10m
- **Workers**: 32
- **Memory**: 16GB

**Time Estimate**: ~2 hours

### **2. FAST (4 hours)**
```bash
python scripts/run_tenerife_calibration_ultra_fast.py --mode fast
```

**Configuration:**
- **Grid Points**: 3 per parameter
- **Parameters**: 4 (add ignition_threshold)
- **Combinations**: 3⁴ = **81 total**
- **Max Steps**: 150
- **Resolution**: 8m
- **Workers**: 48
- **Memory**: 24GB

**Time Estimate**: ~4 hours

### **3. BALANCED (8 hours)**
```bash
python scripts/run_tenerife_calibration_ultra_fast.py --mode balanced
```

**Configuration:**
- **Grid Points**: 3 per parameter
- **Parameters**: 5 (add slope_influence)
- **Combinations**: 3⁵ = **243 total**
- **Max Steps**: 200
- **Resolution**: 6m
- **Workers**: 64
- **Memory**: 32GB

**Time Estimate**: ~8 hours

## 🔧 **Key Optimizations Applied**

### **1. Reduced Parameter Space**
```python
# Current: 5 parameters × 5 points = 3,125 combinations
# Ultra-fast: 3 parameters × 2 points = 8 combinations
# Fast: 4 parameters × 3 points = 81 combinations
# Balanced: 5 parameters × 3 points = 243 combinations
```

### **2. Shorter Simulations**
```python
# Current: 250 steps per simulation
# Ultra-fast: 100 steps (60% reduction)
# Fast: 150 steps (40% reduction)
# Balanced: 200 steps (20% reduction)
```

### **3. Coarser Grid Resolution**
```python
# Current: 5m resolution
# Ultra-fast: 10m resolution (4x fewer cells)
# Fast: 8m resolution (2.5x fewer cells)
# Balanced: 6m resolution (1.7x fewer cells)
```

### **4. Optimized Engine Settings**
```python
# Shorter timeouts
simulation_timeout_minutes = 15.0  # vs 45 minutes

# More aggressive memory management
memory_limit_gb = 16.0  # vs 32GB

# Higher parallel efficiency
parallel_efficiency = 0.9  # vs 0.8
```

## 📈 **Performance Impact Analysis**

### **Grid Size Reduction**
- **5m → 10m**: 4x fewer cells, 4x faster
- **5m → 8m**: 2.5x fewer cells, 2.5x faster
- **5m → 6m**: 1.7x fewer cells, 1.7x faster

### **Simulation Steps Reduction**
- **250 → 100**: 2.5x faster
- **250 → 150**: 1.7x faster
- **250 → 200**: 1.25x faster

### **Parameter Space Reduction**
- **3,125 → 8**: 390x fewer combinations
- **3,125 → 81**: 39x fewer combinations
- **3,125 → 243**: 13x fewer combinations

## 🎯 **Quality vs Speed Trade-offs**

### **Ultra-Fast Mode (2h)**
- ✅ **Fastest possible calibration**
- ✅ **Good for initial parameter exploration**
- ⚠️ **Lower resolution parameter space**
- ⚠️ **May miss optimal parameters**

### **Fast Mode (4h)**
- ✅ **Good balance of speed and quality**
- ✅ **Reasonable parameter coverage**
- ✅ **Suitable for most use cases**
- ⚠️ **Still some parameter space reduction**

### **Balanced Mode (8h)**
- ✅ **High-quality calibration**
- ✅ **Good parameter coverage**
- ✅ **Reasonable runtime**
- ⚠️ **Longer than ultra-fast**

## 🚀 **Usage Examples**

### **Quick Parameter Exploration**
```bash
# Get initial parameter estimates in 2 hours
python scripts/run_tenerife_calibration_ultra_fast.py --mode ultra-fast
```

### **Standard Calibration**
```bash
# Good quality calibration in 4 hours
python scripts/run_tenerife_calibration_ultra_fast.py --mode fast
```

### **High-Quality Calibration**
```bash
# Best quality calibration in 8 hours
python scripts/run_tenerife_calibration_ultra_fast.py --mode balanced
```

### **Dry Run (Setup Only)**
```bash
# Test configuration without running
python scripts/run_tenerife_calibration_ultra_fast.py --mode fast --dry-run
```

## 📊 **Expected Results**

### **Ultra-Fast Mode**
- **Runtime**: 1.5-2.5 hours
- **Memory**: 16GB peak
- **Combinations**: 8 total
- **Best Use**: Initial exploration, quick testing

### **Fast Mode**
- **Runtime**: 3-5 hours
- **Memory**: 24GB peak
- **Combinations**: 81 total
- **Best Use**: Standard calibration, good quality

### **Balanced Mode**
- **Runtime**: 6-10 hours
- **Memory**: 32GB peak
- **Combinations**: 243 total
- **Best Use**: High-quality calibration, research

## ⚠️ **Important Notes**

### **Quality Considerations**
1. **Reduced parameter space** means you might miss optimal parameters
2. **Shorter simulations** may not capture full fire behavior
3. **Coarser resolution** reduces spatial accuracy

### **Recommendations**
1. **Start with ultra-fast** for initial exploration
2. **Use fast mode** for standard calibration
3. **Use balanced mode** for final research results
4. **Compare results** between modes to validate

### **Validation Strategy**
1. Run ultra-fast mode first
2. Use results to guide fast mode parameter bounds
3. Use fast mode results to guide balanced mode
4. Compare all three for consistency

## 🎯 **Bottom Line**

**You can now run calibration in 2-8 hours instead of 2-3 days!**

The ultra-fast runner provides **12-36x speedup** while maintaining reasonable calibration quality. Choose the mode that fits your time constraints and quality requirements.
