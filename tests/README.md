# Tests Directory

This directory contains unit and integration tests for the fire simulation system.

## Structure

### Root Level
Basic import and setup tests:
- `test_gdal_direct.py` - Test GDAL direct access
- `test_gdal_import.py` - Test GDAL import functionality
- `test_terrain_preprocessor_import.py` - Test terrain preprocessor imports

### integration/
Integration tests for model components:
- `test_corrected_calibration.py` - Test corrected calibration workflow
- `test_dice_only_objective.py` - Test Dice-only objective function
- `test_dice_vs_jaccard_calibration.py` - Compare Dice vs Jaccard calibration
- `test_objective_fix.py` - Test objective function fixes
- `test_fuel_normalization_fix.py` - Test fuel normalization corrections
- `test_numba_compatibility.py` - Test Numba JIT compatibility

## Running Tests

Run individual tests:
```bash
python tests/test_gdal_import.py
python tests/integration/test_corrected_calibration.py
```

Run all tests (if test runner configured):
```bash
pytest tests/
```

## Test Categories

### Import Tests
Verify that all required libraries and modules can be imported correctly.

### Integration Tests
Test the interaction between different components of the simulation system.

### Calibration Tests
Validate calibration procedures and objective functions.

### Compatibility Tests
Ensure compatibility with performance optimization libraries (Numba, etc.).

## Note

These tests were created during development to verify bug fixes and ensure system integrity. They may require specific data files or configurations to run successfully.


