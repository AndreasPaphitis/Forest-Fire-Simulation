# Repository Reorganization Migration Guide

## Overview

On October 12, 2025, the repository was comprehensively reorganized to improve navigability and maintainability. This guide documents the changes and provides a migration path for anyone working with the codebase.

## What Changed

### Major Structural Changes

1. **Eliminated numbered folders** (01-06) in favor of descriptive names
2. **Consolidated scattered scripts** into organized directories
3. **Centralized all data** into `data/` directory
4. **Unified results** into `results/` directory
5. **Archived historical files** for reference

### Directory Mapping

#### Data Directories
| Old Location | New Location |
|-------------|--------------|
| `01_raw_data/` | `data/raw/` |
| `02_processed_data/` | `data/processed/` |
| `preprocessed_lidar/` | `data/processed/lidar/` |
| `preprocessed_terrain/` | `data/processed/terrain/` |
| `EMSR Delineations/` | `data/emsr_delineations/` |

#### Results Directories
| Old Location | New Location |
|-------------|--------------|
| `04_results/calibration_results/` | `results/calibration/` |
| `04_results/validation_results/` | `results/validation/` |
| `04_results/sensitivity_analysis/` | `results/sensitivity/` |
| `Academic_Thesis_Charts/` | `results/figures/thesis/` |
| `FINAL VALIDATION RESULTS/` | `results/validation/final/` |
| `simulation_states/` | `results/simulation_states/` |

#### Script Directories
| Old Location | New Location |
|-------------|--------------|
| `scripts/preprocess_lidar.py` | `scripts/preprocessing/preprocess_lidar.py` |
| `scripts/preprocess_terrain.py` | `scripts/preprocessing/preprocess_terrain.py` |
| `scripts/run_tenerife_calibration_clean.py` | `scripts/calibration/run_tenerife_calibration_clean.py` |
| `scripts/run_tenerife_validation_optimized.py` | `scripts/validation/run_tenerife_validation_optimized.py` |
| `hpc_deployment/*` | `scripts/hpc/*` |
| `analysis_scripts/*` | `scripts/analysis/*` |

#### Figure Generation Scripts
| Old Location | New Location |
|-------------|--------------|
| `create_emsr_binary_masks_visualization.py` | `figures/methodology/create_emsr_binary_masks_visualization.py` |
| `create_all_thesis_charts_master.py` | `figures/results/create_all_thesis_charts_master.py` |
| `animation/*` | `figures/supplementary/*` |

#### Test Files
| Old Location | New Location |
|-------------|--------------|
| `test_*.py` (root) | `tests/integration/test_*.py` |

#### Documentation
| Old Location | New Location |
|-------------|--------------|
| `CLEAN_CHART_GENERATION_GUIDE.md` | `docs/guides/CLEAN_CHART_GENERATION_GUIDE.md` |
| `HPC_CORRECTED_CALIBRATION_INSTRUCTIONS.md` | `docs/guides/HPC_CORRECTED_CALIBRATION_INSTRUCTIONS.md` |
| `docs/CALIBRATION_FRAMEWORK_FIXES_SUMMARY.md` | `docs/fixes/CALIBRATION_FRAMEWORK_FIXES_SUMMARY.md` |
| `docs/COMPREHENSIVE_FOREST_FIRE_SIMULATION_WORKFLOW.md` | `docs/summaries/COMPREHENSIVE_FOREST_FIRE_SIMULATION_WORKFLOW.md` |

#### Archived
| Old Location | New Location |
|-------------|--------------|
| `03_analysis_code/` | `archive/old_numbered_structure/03_analysis_code/` |
| `05_documentation/` | `archive/old_numbered_structure/05_documentation/` |
| `06_supplementary/` | `archive/old_numbered_structure/06_supplementary/` |
| `*_backup.py` | `archive/backup_files/*_backup.py` |
| `IMMEDIATE_ACTION_PLAN.md` | `archive/historical_docs/IMMEDIATE_ACTION_PLAN.md` |

## Path Updates Required

### For Scripts

If you have scripts that reference old paths, update them as follows:

#### Data Paths
```python
# Old
data_path = "01_raw_data/lidar/file.las"
processed_path = "02_processed_data/fire_targets/mask.npy"

# New
data_path = "data/raw/lidar/file.las"
processed_path = "data/processed/fire_targets/mask.npy"
```

#### Results Paths
```python
# Old
output_path = "04_results/calibration_results/result.json"
figure_path = "Academic_Thesis_Charts/figure.png"

# New
output_path = "results/calibration/result.json"
figure_path = "results/figures/thesis/figure.png"
```

#### Script Imports
```python
# Old
from scripts.preprocess_lidar import preprocess

# New
from scripts.preprocessing.preprocess_lidar import preprocess
```

### For Configuration Files

Update any configuration files that reference old paths:

```json
{
  "data_dir": "data/processed/lidar/",
  "output_dir": "results/calibration/",
  "figure_dir": "results/figures/thesis/"
}
```

## Centralized Path Configuration

The file `src/utils/project_paths.py` has been updated with the new structure. Use this for consistent path references:

```python
from src.utils.project_paths import get_data_path, get_results_path

data_path = get_data_path("processed/lidar/layer_01.npy")
results_path = get_results_path("calibration/results.json")
```

## Verification Steps

### 1. Check Data Accessibility
```python
import os
from pathlib import Path

# Verify data directories exist
assert Path("data/raw").exists()
assert Path("data/processed").exists()
assert Path("data/emsr_delineations").exists()
```

### 2. Test Import Paths
```python
# Verify src imports still work
from src.core.forest_model import ForestModel
from src.config.config_tools import get_global_config
from src.utils.shared_utilities import calculate_memory_requirements
```

### 3. Run Basic Tests
```bash
python tests/test_gdal_import.py
python tests/integration/test_corrected_calibration.py
```

## Common Issues and Solutions

### Issue 1: FileNotFoundError for data files
**Solution**: Update paths from old numbered folders to new `data/` structure

### Issue 2: Import errors for scripts
**Solution**: Update imports to reflect new `scripts/` subdirectory structure

### Issue 3: Output files going to wrong location
**Solution**: Update output paths to use `results/` directory

### Issue 4: Missing configuration files
**Solution**: Check if files were moved to `archive/` or `docs/`

## Benefits of New Structure

1. **Clearer Organization**: Descriptive names instead of numbers
2. **Easier Navigation**: Related files grouped together
3. **Better Scalability**: Room for growth in each category
4. **Standard Python Structure**: Follows common project conventions
5. **Improved Documentation**: README files in each major directory

## Rollback (If Needed)

If you need to access the old structure:
1. Check `archive/old_numbered_structure/` for archived folders
2. Backup files are in `archive/backup_files/`
3. Historical docs are in `archive/historical_docs/`

## Questions or Issues?

If you encounter any issues with the reorganization:
1. Check this migration guide
2. Review the README.md in affected directories
3. Check `archive/` for historical files
4. Consult the updated root README.md

## Reorganization Date

- **Date**: October 12, 2025
- **Commit**: [Add commit hash if applicable]
- **Performed by**: Automated reorganization script

## Files Not Moved

The following remain in their original locations:
- `src/` - Core library code (already well-organized)
- `README.md` - Root readme (updated with new structure)
- `requirements.txt` - Dependencies
- `CITATION.cff` - Citation information
- `REQUIREMENTS.md` - Requirements documentation

## Next Steps

1. Update any personal scripts or notebooks to use new paths
2. Update bookmarks or IDE project settings
3. Review README files in each directory for usage information
4. Test your workflows with the new structure
5. Report any issues or inconsistencies

## Summary

This reorganization transforms a semi-organized codebase into a clean, standard Python project structure. While it requires some path updates, the long-term benefits in maintainability and navigability are substantial.


