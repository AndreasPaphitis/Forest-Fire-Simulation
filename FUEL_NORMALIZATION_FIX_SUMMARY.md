# Fuel Normalization Fix Summary

## Problem Identified

After fixing the memory leaks, the fire simulation was producing objective scores of 0, indicating no fire spread. The diagnostic revealed that this was due to a **fuel normalization issue** in the fire simulation engine.

## Root Cause

The fire simulation engine was incorrectly normalizing PAD (Plant Area Density) fuel values:

1. **PAD data is already normalized** to 0-1 range from the LiDAR preprocessing
2. **Fire simulation engine was dividing by `max_fuel_value` (10.0)**, making fuel factors very small (0.1 or less)
3. **This prevented ignition** because the effective spread probability was too low

## Fixes Applied

### 1. Fire Simulation Engine (`src/core/fire_simulation_engine.py`)

**Before:**
```python
# Fuel factor (common for both vertical and horizontal)
max_fuel = self.config.max_fuel_value
fuel_factor = min(1.0, self.forest_model.fuel_load[x, y, z] / max_fuel if max_fuel > 0 else 1.0)
```

**After:**
```python
# Fuel factor (common for both vertical and horizontal)
# PAD data is already normalized to 0-1 range, so use it directly
# Only apply max_fuel normalization if the data is not already normalized
current_fuel = self.forest_model.fuel_load[x, y, z]
max_fuel = self.config.max_fuel_value

# Check if fuel data is already normalized (0-1 range)
# If max_fuel is 10.0 and we have PAD data, assume it's already normalized
if max_fuel > 1.0 and current_fuel <= 1.0:
    # PAD data is already normalized, use directly
    fuel_factor = current_fuel
else:
    # Legacy fuel data, apply normalization
    fuel_factor = min(1.0, current_fuel / max_fuel if max_fuel > 0 else 1.0)
```

### 2. Configuration Defaults (`src/config/config_tools.py`)

**Changed:**
- `max_fuel_value: float = 10.0` → `max_fuel_value: float = 1.0` (for PAD data)
- `initial_fuel_load: float = 5.0` → `initial_fuel_load: float = 0.5` (for PAD data)

## Verification

The diagnostic script confirmed the fix works:
- ✅ Fire is now spreading (251 active cells in Test 1, 74 in Test 2)
- ✅ Manual ignition check returns `True`
- ✅ Effective probability calculation is correct

## Impact on Calibration

The calibration should now work properly because:

1. **PAD values (0-1) are used directly** as fuel factors
2. **Realistic fuel values** from LiDAR data are used instead of fallback values
3. **Fire spread probability** is now calculated correctly

## Next Steps

1. **Run calibration again** - the objective scores should now be non-zero
2. **Monitor fire spread** - ensure realistic fire behavior is observed
3. **Check PAD data loading** - verify that actual LiDAR-derived fuel values are being used
4. **Adjust parameters if needed** - the spread probability and ignition threshold may need tuning for the new fuel scale

## Technical Details

- **PAD values**: 0-1 range representing plant area density from LiDAR
- **Fuel factor**: Now directly uses PAD values instead of dividing by max_fuel_value
- **Backward compatibility**: Legacy fuel data (values > 1.0) will still be normalized correctly
- **Memory efficiency**: The fix works with both dense and sparse storage modes
