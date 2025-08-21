# Reduced Output Summary

## Changes Made to Reduce Duplicate/Redundant Output

### 1. **Worker Logging Reduction**
- **File**: `src/core/calibration/grid_search.py`
- **Changes**:
  - Reduced worker parameter logging from first 3 workers to first 1 worker only
  - Reduced seed generation logging from first 3 workers to first 1 worker only
  - Reduced worker assignment logging from first 5 workers to first 1 worker only

### 2. **Progress Callback Optimization**
- **File**: `scripts/run_tenerife_calibration_custom.py`
- **Changes**:
  - Force quiet mode in progress callback to reduce output spam
  - Changed from `quiet_mode=args.quiet` to `quiet_mode=True`

### 3. **Calibration Overview Simplification**
- **File**: `src/core/calibration/fire_perimeter_calibration.py`
- **Changes**:
  - Condensed 4-line calibration overview into 1 line
  - Removed redundant memory requirement and runtime estimates
  - Simplified target data debugging output

## Remaining Potential Issues

### 1. **Multiple Print Statements**
The following files still contain multiple `print()` statements that could cause output duplication:
- `scripts/run_tenerife_calibration_custom.py` (lines 376-386, 393-430, etc.)
- `src/core/calibration/fire_perimeter_calibration.py` (lines 1149-1173, 1199-1206, etc.)
- `src/core/calibration/grid_search.py` (lines 482-488, 2151-2172, etc.)

### 2. **Logger Propagation**
- Worker loggers are set to `propagate=False` but child loggers may still cause issues
- Multiple logger instances could still produce duplicate output

### 3. **Progress Reporting Overlap**
- Main process progress reporting
- Worker process progress reporting  
- Grid search progress reporting
- All could report similar information simultaneously

## Recommendations for Further Reduction

### 1. **Consolidate Print Statements**
Replace multiple `print()` statements with single logger calls:
```python
# Instead of:
print(f"📊 CALIBRATION OVERVIEW:")
print(f"   Total combinations: {total_combinations:,}")
print(f"   Estimated runtime: {runtime:.1f} hours")

# Use:
logger.info(f"📊 Calibration: {total_combinations:,} combinations, {runtime:.1f}h estimated")
```

### 2. **Disable Debug Logging**
Set main logger level to WARNING or ERROR:
```python
logger.setLevel(logging.WARNING)  # Only show warnings and errors
```

### 3. **Use Single Progress System**
Choose one progress reporting system and disable others:
- Keep main process progress
- Disable worker-level progress
- Use quiet mode for grid search progress

### 4. **Reduce Worker Output**
Further reduce worker logging:
```python
# Only log critical errors from workers
worker_logger.setLevel(logging.ERROR)
```

## Expected Output After Changes

With these changes, you should see:
- ✅ Single calibration start message
- ✅ Single progress indicator (not multiple)
- ✅ Only critical errors from workers
- ✅ Reduced debug spam
- ✅ Cleaner, more readable output

## Testing the Changes

Run the calibration and verify:
1. No duplicate progress messages
2. No redundant worker parameter logging
3. Clean, single-line status updates
4. Only essential error messages

If you still see duplicate output, we can make additional reductions to specific logging areas.
