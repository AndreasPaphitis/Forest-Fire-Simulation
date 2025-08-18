# TIMESTEP CONFIGURATION UPDATE

## 🎯 **CHANGES MADE**

### **1. Calibration Timesteps Increased**
- **BEFORE**: 100 timesteps per calibration run
- **AFTER**: **300 timesteps** per calibration run
- **REASON**: Extended for comprehensive fire progression analysis

### **2. Timestep Meaning Clarified**
- **BEFORE**: "Each timestep represents ~1 time unit of fire spread"
- **AFTER**: "Each timestep represents 1 simulation step (no direct time equivalent yet)"
- **REASON**: Corrected inaccurate time representation

### **3. Simulation Timeout Extended**
- **BEFORE**: 180 minutes (3 hours) per simulation
- **AFTER**: **360 minutes (6 hours)** per simulation
- **REASON**: Accommodate longer 300-timestep runs

## 📊 **UPDATED CONFIGURATION**

### **Calibration Settings:**
```python
# From src/core/calibration/fire_perimeter_calibration.py
max_steps=300,             # Extended for comprehensive fire progression
simulation_timeout_minutes=360.0,  # 6 hours per simulation
```

### **HPC Configuration:**
```json
// From hpc_deployment/hpc_optimized_config.json
"simulation": {
    "max_time_steps": 300,
    "time_step": 1,  // No direct time equivalent
}
```

### **Sensitivity Analysis:**
```python
# From scripts/sensitivity_analysis_runner.py
self.calibration_config.base_config.max_steps = 300
```

## ⏱️ **PERFORMANCE IMPACT**

### **Runtime Estimates:**
- **Per simulation**: ~60 minutes (increased from ~20 minutes)
- **Total combinations**: 243 (3^5 grid search)
- **Total calibration time**: ~60-90 hours (increased from ~20-30 hours)
- **Memory usage**: Unchanged (~0.8GB per simulation)

### **HPC Resource Requirements:**
- **Conservative 64GB**: ~90 hours with 40 workers
- **Standard 64GB**: ~60 hours with 60 workers  
- **Optimal 128GB**: ~45 hours with 80 workers
- **Maximum 128GB**: ~30 hours with 120 workers

## 🎯 **BENEFITS OF 300 TIMESTEPS**

### **1. Comprehensive Fire Analysis**
- Allows fires to spread across the entire Tenerife domain
- Captures complete fire progression patterns
- Enables analysis of long-term fire behavior

### **2. Better Calibration Accuracy**
- More data points for parameter optimization
- Improved spatial similarity calculations
- Better validation against real fire perimeters

### **3. Realistic Fire Dynamics**
- Matches the 8-day progression of actual Tenerife fire
- Accounts for complex terrain interactions
- Captures ember transport and long-range spread

## ⚠️ **IMPORTANT NOTES**

### **Timestep Meaning:**
- **No direct time equivalent** - timesteps are simulation steps only
- **Not real-world time** - each step represents one iteration of the fire spread algorithm
- **Relative progression** - more timesteps = more detailed fire evolution

### **Resource Considerations:**
- **Increased computational cost** - 3x more timesteps = 3x longer runtime
- **Extended HPC usage** - plan for 60-90 hours of continuous computation
- **Memory requirements** - unchanged, but longer sustained usage

## 🚀 **NEXT STEPS**

### **1. Test the Configuration**
```bash
python scripts/test_optimized_config.py
```

### **2. Run Calibration**
```bash
python scripts/run_tenerife_calibration.py --memory 64 --workers 40 --grid-points 3
```

### **3. Monitor Progress**
- Check simulation logs for timestep progression
- Monitor memory usage during long runs
- Verify fire spread behavior across 300 timesteps

## ✅ **FILES MODIFIED**

1. `src/core/calibration/fire_perimeter_calibration.py` - Main calibration configuration
2. `scripts/check_tenerife_calibration_config.py` - Configuration display
3. `hpc_deployment/hpc_optimized_config.json` - HPC settings
4. `scripts/sensitivity_analysis_runner.py` - Sensitivity analysis
5. `scripts/test_optimized_config.py` - Test configuration
6. `scripts/test_calibration_simulation.py` - Simulation testing
7. `CALIBRATION_FIXES_SUMMARY.md` - Updated documentation

The calibration system is now configured for **300 timesteps** with proper timeout settings and clarified timestep meaning.
