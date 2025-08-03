# Terrain Data Visualization

This directory contains scripts for creating high-quality visualizations of preprocessed terrain data for academic reporting and presentations.

## Files

- `visualize_terrain_data.py` - Main visualization script with comprehensive functionality
- `run_visualization.py` - Simple wrapper script for quick execution
- `README_visualization.md` - This documentation file

## Quick Start

### Option 1: Simple Execution
```bash
python scripts/run_visualization.py
```

### Option 2: Advanced Usage
```bash
python scripts/visualize_terrain_data.py --help
```

## Available Command Line Options

- `--data-dir`: Directory containing terrain data (default: `preprocessed_terrain`)
- `--output-dir`: Output directory for visualizations (default: `visualizations`)
- `--summary-only`: Create only the summary plot
- `--individual-only`: Create only individual plots

## Examples

```bash
# Use custom data and output directories
python scripts/visualize_terrain_data.py --data-dir my_terrain_data --output-dir my_plots

# Create only summary plot
python scripts/visualize_terrain_data.py --summary-only

# Create only individual plots
python scripts/visualize_terrain_data.py --individual-only
```

## Output Files

The script generates the following outputs in the `visualizations/` directory:

### Individual Plots
- `elevation.png` - Terrain elevation map
- `slope.png` - Slope map in degrees
- `aspect.png` - Aspect map with circular colormap
- `barranco_mask.png` - Barranco detection results
- `depression_mask.png` - Depression detection results
- `wind_channeling_mask.png` - Wind channeling detection
- `wind_amplification.png` - Wind amplification factors
- `wind_direction_modification.png` - Wind direction modifications

### Summary Plot
- `terrain_summary.png` - Multi-panel overview of all datasets

### Statistics Report
- `terrain_statistics.txt` - Detailed statistics for each dataset

## Features

### Academic Styling
- High-resolution output (300 DPI)
- Professional color schemes
- Clean, publication-ready formatting
- Proper axis labels and titles

### Data Handling
- Automatic NaN value masking
- Appropriate colormaps for different data types
- Statistics calculation and reporting
- Flexible input/output directory configuration

### Visualization Types
- **Continuous data**: Elevation, slope, wind factors (using viridis, terrain colormaps)
- **Aspect data**: Special circular colormap (hsv) with degree annotations
- **Binary masks**: Red/white visualization for detection results
- **Summary plots**: Multi-panel overview for presentations

## Requirements

- Python 3.7+
- NumPy
- Matplotlib
- Pathlib (built-in)

## Troubleshooting

### Common Issues

1. **"No data files found"**
   - Check that your `preprocessed_terrain` directory contains `.npy` files
   - Verify file permissions

2. **Memory errors**
   - Large terrain files may require significant RAM
   - Consider using compressed `.npz` files for large datasets

3. **Import errors**
   - Ensure you're running from the correct directory
   - Check that all required packages are installed

### Performance Tips

- For very large datasets, consider downsampling before visualization
- Use `--individual-only` if you only need specific plots
- The script automatically handles memory-efficient loading

## Integration with Academic Work

### For Papers
- Use individual high-resolution PNG files
- Include statistics from `terrain_statistics.txt`
- Reference the summary plot for overview figures

### For Presentations
- Use the summary plot for overview slides
- Individual plots for detailed discussions
- Statistics for quantitative analysis

### For Reports
- Include all plots with proper captions
- Reference the statistics report for numerical summaries
- Use consistent styling across all figures 