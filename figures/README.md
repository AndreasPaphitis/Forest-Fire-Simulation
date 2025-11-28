# Figures Directory

This directory contains all scripts for generating charts, visualizations, and animations for the thesis.

## Structure

### methodology/
Scripts for generating methodology section figures:
- `create_emsr_binary_masks_visualization.py` - EMSR fire perimeter binary masks
- `create_figure19_correct_validation_data.py` - Validation data figures
- `chart_styling_system.py` - Styling system for consistent figure appearance
- `create_figure1_pipeline_focused.py` - LiDAR preprocessing pipeline diagram
- `create_day4_terrain_visualization.py` - Day 4 terrain visualization
- `create_fixed_terrain_comparison.py` - Terrain comparison figures

### results/
Scripts for generating results section figures:
- `create_all_thesis_charts_master.py` - Master script for all thesis charts
- `create_additional_validation_charts.py` - Additional validation visualizations
- `create_sensitivity_analysis_charts.py` - Sensitivity analysis figures

### supplementary/
Scripts for animations and supplementary visualizations:
- `comprehensive_fire_animator.py` - Comprehensive fire spread animations
- `create_interactive_fire_explorer.py` - Interactive fire exploration tool
- `create_updated_animations.py` - Updated animation generation
- `create_validation_fire_animation.py` - Validation fire animations
- `create_validation_fire_visualization.py` - Validation fire visualizations

## Usage

Run scripts from the project root directory:
```bash
python figures/methodology/create_emsr_binary_masks_visualization.py
python figures/results/create_all_thesis_charts_master.py
```

## Output

Generated figures are saved to `results/figures/thesis/` directory.


