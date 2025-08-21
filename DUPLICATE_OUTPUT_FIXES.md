# Duplicate Output Fixes Summary

## Issues Identified

### 1. **Duplicate Calibration Start Messages**
- **Problem**: Both `scripts/run_tenerife_calibration_custom.py` and `src/core/calibration/fire_perimeter_calibration.py` were showing calibration start messages
- **Fix**: Removed duplicate start message from `fire_perimeter_calibration.py`

### 2. **Duplicate Completion Messages**
- **Problem**: Both scripts were showing "Calibration completed" messages
- **Fix**: Removed duplicate completion message from `fire_perimeter_calibration.py`

### 3. **Duplicate Best Objective Value**
- **Problem**: Best objective value was shown by both the main script and the calibrator
- **Fix**: Removed duplicate best objective display from main script

### 4. **Duplicate Progress Reporting**
- **Problem**: Progress was reported by both grid search module and progress callback
- **Fix**: 
  - Simplified grid search progress to show only percentage
  - Disabled progress callback output in quiet mode
  - Reduced frequency of progress updates

### 5. **Duplicate Best Parameters**
- **Problem**: Best parameters were shown by both grid search and main script
- **Fix**: Removed duplicate parameter display from grid search module

## Files Modified

### 1. **scripts/run_tenerife_calibration_custom.py**
- Removed duplicate best objective value display
- Simplified results summary section
- Removed redundant time per simulation estimate

### 2. **src/core/calibration/fire_perimeter_calibration.py**
- Removed duplicate calibration start message
- Removed duplicate completion message
- Kept only essential best objective display

### 3. **src/core/calibration/grid_search.py**
- Simplified progress reporting to avoid duplication
- Removed duplicate best parameters display
- Reduced frequency of progress updates

### 4. **src/core/calibration/calibration_utils.py**
- Simplified progress callback to avoid duplication
- Disabled simple progress output in quiet mode

## Output Flow After Fixes

### **Single Source of Truth for Each Message Type:**

1. **Calibration Start**: Only shown by main script (`run_tenerife_calibration_custom.py`)
2. **Progress Updates**: Only shown by grid search module (simplified)
3. **Calibration Completion**: Only shown by main script
4. **Best Objective Value**: Only shown by calibrator (`fire_perimeter_calibration.py`)
5. **Best Parameters**: Only shown by main script
6. **Results Summary**: Only shown by main script

## Expected Output After Fixes

```
🚀 EXECUTING CUSTOM CALIBRATION
==================================================
📊 Progress: 25.0% (20/81)
📊 Progress: 50.0% (40/81)
📊 Progress: 75.0% (100/81)
🎯 Best objective: 0.8234
✅ CUSTOM CALIBRATION COMPLETE
Total time: 2.45 hours
Results saved to: /path/to/results
```

## Benefits

1. **Cleaner Output**: No more duplicate messages
2. **Better Readability**: Single source of truth for each information type
3. **Reduced Spam**: Less verbose progress reporting
4. **Consistent Experience**: Same output format regardless of which script is used

## Testing

To verify the fixes work correctly:
1. Run `python scripts/run_tenerife_calibration_custom.py --workers 2 --grid-points 2`
2. Verify no duplicate messages appear
3. Verify all essential information is still shown
4. Verify progress updates are clear but not excessive
