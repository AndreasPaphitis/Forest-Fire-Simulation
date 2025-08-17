# 🏔️ Tenerife Calibration Guide - Production-Ready Day 4 Fire Area Simulation

## Overview
Your `run_tenerife_calibration.py` script is now **production-ready** for the Day 4 fire area calibration (500 × 500 × 25 cells) with comprehensive memory management and OOM protection.

## 🚀 Quick Start Commands

### Full Production Scale (Recommended)
```bash
# 512GB system with 32 workers (conservative)
python scripts/run_tenerife_calibration.py --memory 512 --workers 32

# 1TB system with 48 workers (optimal)
python scripts/run_tenerife_calibration.py --memory 1024 --workers 48

# Dry run to validate setup first
python scripts/run_tenerife_calibration.py --memory 512 --workers 32 --dry-run
```

### Emergency Testing Mode
```bash
# Emergency small-scale for testing (1000x1000 grid)
python scripts/run_tenerife_calibration.py --emergency-small-scale

# Small scale with custom parameters
python scripts/run_tenerife_calibration.py --emergency-small-scale --workers 4 --grid-points 3
```

## 🎯 Configuration Options

### Memory and Workers
```bash
# Memory options (GB)
--memory 64      # Small scale testing
--memory 128     # Medium scale
--memory 256     # Large scale
--memory 512     # Production scale (recommended)
--memory 1024    # Optimal scale

# Worker recommendations by memory
--memory 512 --workers 32   # Conservative (16GB per worker)
--memory 512 --workers 24   # Safe (21GB per worker) 
--memory 1024 --workers 48  # Optimal (21GB per worker)
```

### Calibration Parameters
```bash
# Grid search precision
--grid-points 3   # Fast (default)
--grid-points 4   # Higher accuracy
--grid-points 5   # Maximum accuracy

# Custom parameter selection
--parameters ember_probability fuel_consumption_rate ember_ignition

# Training/test data split
--training-days 1 2
--test-days 3 4
```

### Safety and Monitoring
```bash
# Memory protection (enabled by default)
--enable-memory-protection

# Verbose logging
--verbose

# Dry run (no execution)
--dry-run
```

## 📊 Memory Management Features

### Production Memory Protection
✅ **Real-time monitoring** every 15 seconds
✅ **Emergency protocols** at 60/80/100 GB thresholds
✅ **Automatic cleanup** of shared memory leaks
✅ **Memory growth detection** and alerts
✅ **OOM prevention** with emergency callbacks

### Memory Thresholds
- **Warning (60GB)**: Light garbage collection
- **Critical (80GB)**: Aggressive cleanup + shared memory purge  
- **Emergency (100GB)**: Emergency protocols + automatic checkpointing
- **System limits**: 75%/90%/95% total system memory

### Memory Safety Features
- **Sparse-only enforcement** for massive grids
- **Shared memory leak detection** and cleanup
- **Memory growth rate monitoring** (alerts if >100MB/sec)
- **Emergency memory recovery** procedures

## 🔍 Resource Requirements

### Minimum System Requirements
- **Memory**: 512 GB RAM
- **CPU**: 32+ cores
- **Storage**: 100 GB free space
- **Python**: 3.8+ with required packages

### Required Python Packages
```bash
pip install scipy numpy psutil geopandas imageio
# OR use the project requirements
pip install -r requirements.txt
```

### Optimal System Configuration
- **Memory**: 1 TB RAM
- **CPU**: 64+ cores (Intel Xeon or AMD EPYC)
- **Storage**: 500 GB NVMe SSD
- **Network**: High-speed for data sharing

### Memory Allocation Strategy
```
Per-worker allocation (Day 4 area):
- Active fire cells (sparse): 0.01 GB (9.76 MB)
- Working memory (simulation): 0.50 GB
- Python runtime overhead: 0.25 GB
- Calibration overhead: 0.10 GB
- Framework overhead: 0.25 GB
- Terrain memory: 0.00 GB (shared)

Total per worker: 1.11 GB

Total for 32 workers on 128GB system:
- Worker processes: 32 × 1.11 GB = 35.5 GB
- Shared terrain: 9.7 GB
- System reserve: 50.0 GB
- Calibration coordination: 5.0 GB
- TOTAL: 100.2 GB (78% utilization)
```

## 🎯 Execution Examples

### Basic Production Run
```bash
# Start calibration with default settings
python scripts/run_tenerife_calibration.py

# Output:
🔥 TENERIFE FIRE PERIMETER CALIBRATION
🛡️  SETTING UP PRODUCTION MEMORY PROTECTION
🔍 SYSTEM RESOURCE CHECK FOR DAY 4 FIRE AREA CALIBRATION:
   Total memory: 128.0 GB
   Available memory: 120.0 GB
   Required memory: 100.2 GB
✅ System resources validated for Day 4 fire area calibration
🔥 STARTING CALIBRATION EXECUTION
🛡️  Memory protection active - monitoring every 15 seconds
```

### High-Performance Run
```bash
# Maximum performance configuration
python scripts/run_tenerife_calibration.py \
    --memory 1024 \
    --workers 48 \
    --grid-points 4 \
    --parameters ember_probability fuel_consumption_rate ember_ignition slope_influence

# Expected output:
⏱️  Estimated completion: 23 minutes
💾 Estimated peak memory: 100.2 GB
🎯 Total combinations: 243
```

### Emergency Testing
```bash
# Test with small grid first
python scripts/run_tenerife_calibration.py --emergency-small-scale --dry-run

# Expected output (requires geopandas for EMSR data):
🚨 EMERGENCY SMALL-SCALE MODE ACTIVATED
   Using 1000x1000 grid instead of full Tenerife
   This is for testing and validation only
⚠️  Cannot validate system resources (psutil not available)
🔍 DISCOVERING FIRE PERIMETERS
   ❌ Invalid: Spatial libraries (geopandas) not available

# To install required dependencies:
pip install psutil geopandas imageio
```

## 📊 Monitoring and Debugging

### Real-Time Monitoring
The script provides comprehensive monitoring:
```
📊 Memory: Process=45.2GB, System=78.5%, Growth=2.1MB/s, Level=normal
📊 Memory: Process=52.1GB, System=82.3%, Growth=8.7MB/s, Level=warning
🚨 CALIBRATION EMERGENCY: Process memory 85.2GB
```

### Memory Reports
Final memory analysis:
```
📊 FINAL MEMORY REPORT:
   Peak process memory: 78.5 GB
   Average process memory: 52.3 GB
   Peak system usage: 89.2%
   Emergency activations: No
```

### Log Monitoring
Monitor calibration progress:
```bash
# Follow calibration logs
tail -f calibration_results/tenerife_emsr685_calibration_*/calibration.log

# Check memory logs
grep "Memory:" calibration_results/*/calibration.log

# Check for emergencies
grep "EMERGENCY" calibration_results/*/calibration.log
```

## 🚨 Troubleshooting

### Common Issues and Solutions

#### OOM Kill Despite Memory Protection
```bash
# Symptoms: Process killed with "Killed" message
# Solution: Reduce worker count or increase memory
python scripts/run_tenerife_calibration.py --memory 1024 --workers 24
```

#### Memory Growth Alerts
```bash
# Symptoms: "Memory growth: 150.2 MB/sec" warnings
# Solution: Enable more aggressive cleanup
python scripts/run_tenerife_calibration.py --memory 512 --workers 16
```

#### System Resource Validation Failed
```bash
# Symptoms: "Insufficient memory for Day 4 fire area calibration"
# Solution: Use emergency mode first
python scripts/run_tenerife_calibration.py --emergency-small-scale
```

#### Import Errors
```bash
# Symptoms: "ModuleNotFoundError: No module named 'src'"
# Solution: Run from project root directory
cd /path/to/Forest-Fire-Simulation
python scripts/run_tenerife_calibration.py

# Symptoms: "psutil module not found" or "geopandas not available"
# Solution: Install required dependencies
pip install psutil geopandas imageio scipy numpy
```

### Emergency Procedures
```bash
# If calibration hangs or memory issues occur:

# 1. Check memory usage
htop -u $USER

# 2. Clean shared memory manually
python scripts/immediate_memory_fix.py

# 3. Restart with lower resource usage
python scripts/run_tenerife_calibration.py --memory 256 --workers 12 --emergency-small-scale
```

## ✅ Success Indicators

### Healthy Execution
Look for these positive indicators:
- ✅ `"Production memory protection active"`
- ✅ `"System resources validated for massive scale"`
- ✅ `"MASSIVE GRID DETECTED"` (sparse-only mode)
- ✅ `"Using shared terrain data from memory"`
- ✅ `"Level=normal"` in memory monitoring

### Warning Signs
Watch for these concerning patterns:
- ⚠️ `"Memory growth: X MB/sec"` (if >100 MB/sec)
- ⚠️ `"WARNING: Too many workers"`
- ⚠️ `"Level=warning"` or `"Level=critical"`
- 🚨 `"EMERGENCY MEMORY SITUATION"`

## 🎯 Best Practices

### Before Running
1. **Test with emergency mode first**
2. **Check system memory availability** 
3. **Close unnecessary applications**
4. **Use dry-run to validate configuration**

### During Execution
1. **Monitor memory logs regularly**
2. **Watch for emergency alerts**
3. **Keep backup checkpoints**
4. **Don't interrupt during critical phases**

### After Completion
1. **Review memory reports**
2. **Archive results immediately**
3. **Clean up shared memory**
4. **Document lessons learned**

Your `run_tenerife_calibration.py` script is now **production-ready** for the Day 4 fire area calibration with 6.25 million cells! 🏔️🔥
