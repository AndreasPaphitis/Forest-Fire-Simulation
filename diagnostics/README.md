# Diagnostics Directory

This directory contains one-off diagnostic and analysis scripts used during development and debugging.

## Scripts

### Calibration Diagnostics
- `analyze_best_results.py` - Analyze best calibration results
- `analyze_calibration_failure.py` - Diagnose calibration failures
- `check_calibration_file.py` - Validate calibration file integrity

### Data Diagnostics
- `check_preprocessed_lidar.py` - Verify LiDAR preprocessing outputs
- `diagnose_target_data.py` - Diagnose target data issues
- `check_dtm_info.py` - Check DTM file information

### Model Diagnostics
- `spatial_alignment_analysis.py` - Analyze spatial alignment issues
- `spatial_alignment_fix_analysis.py` - Verify spatial alignment fixes
- `verify_dice_minimizes_error.py` - Verify Dice coefficient behavior
- `fix_parameter_classification.py` - Fix parameter classification issues

### Quality Assurance
- `ensure_academic_standards_compliance.py` - Check academic standards compliance

### Performance Analysis
- Time estimation scripts for performance benchmarking

## Usage

These scripts are typically run individually as needed:
```bash
python diagnostics/analyze_best_results.py
python diagnostics/check_preprocessed_lidar.py
```

## Note

These are diagnostic tools and not part of the main workflow. They were used during development to identify and fix issues.


