#!/usr/bin/env python3
"""
Simple wrapper script to run terrain visualization.
"""

import sys
import os
from pathlib import Path

# Add the scripts directory to Python path
scripts_dir = Path(__file__).parent
sys.path.insert(0, str(scripts_dir))

from visualize_terrain_data import TerrainVisualizer

def main():
    """Run the terrain visualization with default settings."""
    print("Forest Fire Simulation - Terrain Data Visualization")
    print("=" * 50)
    
    # Create visualizer with default settings
    visualizer = TerrainVisualizer()
    
    # Check if we have large datasets and use simple mode
    try:
        # Check the size of the first data file to determine if we need simple mode
        import os
        import numpy as np
        
        elevation_file = os.path.join(visualizer.data_dir, 'elevation.npy')
        if os.path.exists(elevation_file):
            # Load just the shape to check size
            data = np.load(elevation_file, mmap_mode='r')  # Memory-mapped to avoid loading full data
            total_cells = data.shape[0] * data.shape[1]
            del data  # Close the memory mapping
            
            if total_cells > 1000000:  # 1M cells
                print("🔧 Large dataset detected, using SIMPLE MODE for performance")
                simple_mode = True
            else:
                simple_mode = False
        else:
            simple_mode = False
    except Exception as e:
        print(f"⚠️  Could not determine dataset size: {e}")
        simple_mode = False
    
    # Run complete visualization
    visualizer.run_visualization(create_summary=True, create_individual=True, simple_mode=simple_mode)
    
    print("\nVisualization complete!")
    print("Check the 'visualizations' directory for all outputs.")

if __name__ == "__main__":
    main() 