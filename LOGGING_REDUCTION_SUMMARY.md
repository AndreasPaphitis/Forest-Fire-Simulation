# Logging Output Reduction Summary

## Changes Made

### 1. Main Calibration Script (`scripts/run_tenerife_calibration_clean.py`)
- **Before**: `logging.basicConfig(level=logging.INFO)` with detailed format
- **After**: `logging.basicConfig(level=logging.WARNING)` with minimal format
- **Before**: `logging.getLogger('src.core.forest_model').setLevel(logging.DEBUG)`
- **After**: `logging.getLogger('src.core.forest_model').setLevel(logging.WARNING)`

### 2. Grid Search Module (`src/core/calibration/grid_search.py`)
- **Before**: Worker logger set to `logging.DEBUG`
- **After**: Worker logger set to `logging.WARNING`
- Added helper function to set worker logger levels consistently

### 3. Additional Logger Suppression
Set the following loggers to WARNING level to reduce verbose output:
- `src.core.forest_model`
- `src.core.calibration`
- `src.core.fire_simulation_engine`
- `src.utils.lidar_utils`
- `src.utils.terrain_preprocessor`

## Result
- **Debug messages**: Suppressed (no longer appear)
- **Info messages**: Suppressed (no longer appear)
- **Warning messages**: Still visible (important issues)
- **Error messages**: Still visible (critical issues)

## Verification
Created and ran `test_reduced_logging.py` to verify:
- Forest model logger level: WARNING (30)
- Calibration logger level: WARNING (30)
- Debug and info messages are properly suppressed
- Warning and error messages still appear

## Impact
The calibration process will now produce much cleaner output, showing only:
- Progress updates from the main script
- Warning messages for important issues
- Error messages for critical problems
- Final results and statistics

This should make it much easier to read and monitor the calibration progress.
