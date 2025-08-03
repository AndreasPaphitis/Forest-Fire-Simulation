# 📁 Output Path Configuration Guide

The Forest Fire Simulation now supports **configurable output paths** for all result types. This allows you to specify exactly where different types of simulation outputs are saved, removing all hardcoded paths.

## 🎯 **Configuration Options**

### **Basic Configuration**
```json
{
  "output": {
    "output_dir": "/your/main/results/directory"
  }
}
```
- **Default behavior:** All outputs saved in subdirectories under `output_dir`

### **Advanced Path Configuration**
```json
{
  "output": {
    "output_dir": "/your/main/results/directory",
    "results_output_dir": "/custom/path/for/simulation/results",
    "logs_output_dir": "/custom/path/for/logs",
    "checkpoints_output_dir": "/custom/path/for/checkpoints", 
    "monitoring_output_dir": "/custom/path/for/monitoring",
    "temp_storage_dir": "/fast/scratch/storage/for/temp/files"
  }
}
```

## 📂 **Directory Types Explained**

| Directory Type | Purpose | Default Location |
|---------------|---------|------------------|
| **`output_dir`** | Main output directory | `"results"` |
| **`results_output_dir`** | Final simulation results | `output_dir/results` |
| **`logs_output_dir`** | Log files | `output_dir/logs` |
| **`checkpoints_output_dir`** | Checkpoint files | `output_dir/checkpoints` |
| **`monitoring_output_dir`** | Performance monitoring | `output_dir/monitoring` |
| **`temp_storage_dir`** | Temporary/cache files | `output_dir/temp` |

## 🔧 **Usage Examples**

### **Example 1: Use Project Space (HPC)**
```json
{
  "output": {
    "output_dir": "/gpfs/home1/username/simulation_results",
    "temp_storage_dir": "/scratch-shared/username/temp_cache"
  }
}
```
- **Results:** `/gpfs/home1/username/simulation_results/results/`
- **Logs:** `/gpfs/home1/username/simulation_results/logs/`
- **Temp files:** `/scratch-shared/username/temp_cache/`

### **Example 2: Fully Custom Paths**
```json
{
  "output": {
    "output_dir": "/data/fire_sims",
    "results_output_dir": "/archive/simulation_outputs", 
    "logs_output_dir": "/logs/fire_simulation",
    "checkpoints_output_dir": "/backup/checkpoints",
    "temp_storage_dir": "/tmp/fire_sim_cache"
  }
}
```

### **Example 3: Research Project Organization**
```json
{
  "output": {
    "output_dir": "/research/forest_fires/experiment_2024",
    "results_output_dir": "/research/forest_fires/experiment_2024/datasets",
    "logs_output_dir": "/research/forest_fires/experiment_2024/analysis_logs",
    "temp_storage_dir": "/scratch/fast_storage"
  }
}
```

## 🎯 **Path Resolution**

- **Automatic expansion:** `~` expands to home directory
- **Relative paths:** Resolved relative to working directory
- **Absolute paths:** Used as-is
- **Environment variables:** `$USER`, `$HOME` etc. supported

### **Examples:**
- `"~/simulation_results"` → `/home/username/simulation_results`
- `"results"` → `/current/working/dir/results`
- `"/gpfs/home1/$USER/sims"` → `/gpfs/home1/username/sims`

## 📋 **Configuration Methods**

### **Method 1: JSON Configuration File**
```json
{
  "output": {
    "output_dir": "/your/path/here",
    "results_output_dir": "/custom/results/path"
  }
}
```

### **Method 2: Command Line Override**
```bash
python run_production_sim.py --output /custom/output/path
```
- **Note:** Command line `--output` overrides `output_dir` but preserves other custom paths

### **Method 3: Programmatic Configuration**
```python
from src.config.config_tools import ModelConfig

config = ModelConfig(
    output_dir="/main/output/path",
    results_output_dir="/custom/results",
    logs_output_dir="/custom/logs"
)

# Access resolved paths
main_dir = config.get_output_dir()
results_dir = config.get_results_dir() 
logs_dir = config.get_logs_dir()
```

## 🛠 **Helper Methods**

The `ModelConfig` class provides helper methods:

```python
config = ModelConfig(output_dir="/my/simulation/results")

# Get specific directories
output_dir = config.get_output_dir()           # Main output
results_dir = config.get_results_dir()         # Results subdirectory  
logs_dir = config.get_logs_dir()               # Logs subdirectory
checkpoints_dir = config.get_checkpoints_dir() # Checkpoints subdirectory
monitoring_dir = config.get_monitoring_dir()   # Monitoring subdirectory
temp_dir = config.get_temp_storage_dir()       # Temporary storage

# Create all directories and get paths
all_dirs = config.ensure_output_directories(create_dirs=True)
```

## ✅ **Migration from Hardcoded Paths**

### **Before (Hardcoded):**
```python
results_dir = Path("results") / "simulation_output"
logs_dir = Path("logs") / "simulation.log"
```

### **After (Configurable):**
```python
results_dir = config.get_results_dir()
logs_dir = config.get_logs_dir()
```

## 🚨 **Important Notes**

1. **Permissions:** Ensure write access to all specified directories
2. **Disk Space:** Monitor storage usage, especially for temp directories
3. **HPC Systems:** Use appropriate storage tiers (scratch vs. project space)
4. **Backup:** Consider backup policies for important results
5. **Path Conflicts:** Avoid overlapping directories between different simulations

## 💡 **Best Practices**

1. **Use absolute paths** for production environments
2. **Separate fast storage** (temp) from persistent storage (results)
3. **Include job ID** in directory names for HPC environments
4. **Test path accessibility** before running large simulations
5. **Document your path structure** for team projects

---

This configuration system replaces all hardcoded paths in the simulation framework, giving you complete control over where your simulation outputs are stored! 🎉 