#!/usr/bin/env python3
"""
Validation Fire Visualization System
Create fire progression animations and 3D visualizations from validation results.
"""
import sys
import pickle
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.colors import ListedColormap, LinearSegmentedColormap
from mpl_toolkits.mplot3d import Axes3D
from pathlib import Path
import json
import math

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def load_validation_data(day):
    """Load validation data for a specific day."""
    results_dir = Path("validation_results_optimized")
    
    print(f"🔥 Loading Day {day} validation data...")
    
    try:
        # Load forest model
        forest_model_file = results_dir / f"day_{day}_forest_model.pkl"
        with open(forest_model_file, 'rb') as f:
            forest_model = pickle.load(f)
        
        # Load engine (contains sparse_history)
        engine_file = results_dir / f"day_{day}_engine.pkl"
        with open(engine_file, 'rb') as f:
            engine = pickle.load(f)
        
        # Load config
        config_file = results_dir / f"day_{day}_config.pkl"
        with open(config_file, 'rb') as f:
            config = pickle.load(f)
        
        # Load validation results
        results_file = results_dir / f"day_{day}_validation_result.json"
        with open(results_file, 'r') as f:
            validation_results = json.load(f)
        
        print(f"✅ Loaded Day {day} data:")
        print(f"   Grid size: {config.grid_size}")
        print(f"   Layers: {config.num_layers}")
        print(f"   Sparse history: {len(engine.sparse_history)} entries")
        print(f"   Resolution: {config.model_resolution}m per cell")
        
        return forest_model, engine, config, validation_results
        
    except Exception as e:
        print(f"❌ Error loading Day {day} data: {e}")
        return None, None, None, None

def create_fire_progression_animation(engine, config, day, output_dir="validation_processed_results"):
    """Create fire progression animation from sparse history."""
    print(f"\n🎬 Creating fire progression animation for Day {day}...")
    
    if not hasattr(engine, 'sparse_history') or not engine.sparse_history:
        print("❌ No sparse history found in engine")
        return
    
    # Extract progression data
    steps = []
    burning_counts = []
    burned_counts = []
    
    for entry in engine.sparse_history:
        step = entry.get('step', 0)
        stats = entry.get('stats', {})
        
        steps.append(step)
        burning_counts.append(len(engine.active_cells) if hasattr(engine, 'active_cells') else 0)
        burned_counts.append(len(engine.burned_cells) if hasattr(engine, 'burned_cells') else 0)
    
    # Create progression plot
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
    
    # Plot 1: Fire progression over time
    ax1.plot(steps, burning_counts, 'o-', color='red', label='Burning Cells', linewidth=2, markersize=4)
    ax1.plot(steps, burned_counts, 's-', color='darkred', label='Burned Cells', linewidth=2, markersize=4)
    ax1.set_xlabel('Simulation Step')
    ax1.set_ylabel('Number of Cells')
    ax1.set_title(f'🔥 Day {day} Fire Progression - Cell Count Over Time')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # Plot 2: Cumulative fire area
    total_affected = [b + bu for b, bu in zip(burning_counts, burned_counts)]
    area_hectares = [count * (config.model_resolution ** 2) / 10000 for count in total_affected]  # Convert to hectares
    
    ax2.plot(steps, area_hectares, 'o-', color='orange', label='Total Fire Area', linewidth=2, markersize=4)
    ax2.set_xlabel('Simulation Step')
    ax2.set_ylabel('Area (Hectares)')
    ax2.set_title(f'🔥 Day {day} Fire Area Growth')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    # Save the plot
    output_path = Path(output_dir) / f"day_{day}_fire_progression.png"
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"✅ Fire progression saved: {output_path}")
    plt.close()

def create_3d_fire_perimeter_visualization(forest_model, config, day, output_dir="validation_processed_results"):
    """Create 3D visualization of final fire perimeter."""
    print(f"\n🎨 Creating 3D fire perimeter visualization for Day {day}...")
    
    try:
        # Get 2D fire perimeter
        if hasattr(forest_model, 'get_2d_fire_perimeter'):
            fire_perimeter = forest_model.get_2d_fire_perimeter()
            print(f"✅ Fire perimeter shape: {fire_perimeter.shape}")
            
            # Create 3D plot
            fig = plt.figure(figsize=(14, 10))
            ax = fig.add_subplot(111, projection='3d')
            
            # Get coordinates of burned areas
            y_coords, x_coords = np.where(fire_perimeter > 0)
            
            if len(x_coords) > 0:
                # Sample points for better visualization (if too many points)
                if len(x_coords) > 5000:
                    indices = np.random.choice(len(x_coords), 5000, replace=False)
                    x_coords = x_coords[indices]
                    y_coords = y_coords[indices]
                
                # Convert to meters
                x_meters = x_coords * config.model_resolution
                y_meters = y_coords * config.model_resolution
                z_meters = np.zeros_like(x_meters)  # Ground level
                
                # Create scatter plot
                ax.scatter(x_meters, y_meters, z_meters, c='red', s=1, alpha=0.6, label='Burned Area')
                
                # Add some 3D layers for visual effect
                for layer in range(0, min(config.num_layers, 5)):
                    layer_height = layer * 2  # 2m per layer
                    ax.scatter(x_meters[::10], y_meters[::10], z_meters[::10] + layer_height, 
                              c='orange', s=0.5, alpha=0.3)
                
                ax.set_xlabel('X (meters)')
                ax.set_ylabel('Y (meters)')
                ax.set_zlabel('Height (meters)')
                ax.set_title(f'🔥 Day {day} - 3D Fire Perimeter\nBurned Area: {len(x_coords):,} cells')
                
                # Save the plot
                output_path = Path(output_dir) / f"day_{day}_3d_fire_perimeter.png"
                plt.savefig(output_path, dpi=300, bbox_inches='tight')
                print(f"✅ 3D perimeter saved: {output_path}")
                plt.close()
            else:
                print("⚠️  No burned areas found in fire perimeter")
        else:
            print("❌ Forest model does not have get_2d_fire_perimeter method")
            
    except Exception as e:
        print(f"❌ Error creating 3D visualization: {e}")

def create_fire_statistics_dashboard(validation_results, day, output_dir="validation_processed_results"):
    """Create comprehensive fire statistics dashboard."""
    print(f"\n📊 Creating fire statistics dashboard for Day {day}...")
    
    try:
        stats = validation_results['vertical_spread_stats']
        
        # Create dashboard
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
        
        # Plot 1: Spread type breakdown
        spread_types = ['Horizontal', 'Vertical', 'Ember']
        spread_counts = [stats['horizontal_spread'], stats['vertical_spread'], stats['ember_spread']]
        colors = ['#ff7f0e', '#d62728', '#ff9999']
        
        ax1.pie(spread_counts, labels=spread_types, colors=colors, autopct='%1.1f%%', startangle=90)
        ax1.set_title(f'🔥 Day {day} - Fire Spread Type Distribution')
        
        # Plot 2: Efficiency metrics
        efficiency_types = ['Horizontal', 'Vertical', 'Ember']
        efficiency_values = [stats['horizontal_efficiency'], stats['vertical_efficiency'], stats['ember_efficiency']]
        
        ax2.bar(efficiency_types, efficiency_values, color=colors)
        ax2.set_ylabel('Efficiency (%)')
        ax2.set_title(f'🚀 Day {day} - Spread Efficiency')
        ax2.tick_params(axis='x', rotation=45)
        
        # Plot 3: Total events
        total_stats = {
            'Total Spread': stats['total_spread'],
            'Total Ignitions': stats['total_ignitions'],
            'Successful Spread': sum(spread_counts)
        }
        
        bars = ax3.bar(total_stats.keys(), total_stats.values(), color=['#2ca02c', '#1f77b4', '#ff7f0e'])
        ax3.set_ylabel('Count')
        ax3.set_title(f'📈 Day {day} - Total Fire Events')
        ax3.tick_params(axis='x', rotation=45)
        
        # Add value labels on bars
        for bar in bars:
            height = bar.get_height()
            ax3.text(bar.get_x() + bar.get_width()/2., height,
                    f'{int(height):,}', ha='center', va='bottom')
        
        # Plot 4: Ratios
        ratios = {
            'V/H Ratio': stats['vertical_horizontal_ratio'],
            'E/H Ratio': stats['ember_horizontal_ratio'],
            'E/V Ratio': stats['ember_vertical_ratio']
        }
        
        ax4.bar(ratios.keys(), ratios.values(), color=['#9467bd', '#8c564b', '#e377c2'])
        ax4.set_ylabel('Ratio')
        ax4.set_title(f'⚖️  Day {day} - Spread Ratios')
        ax4.tick_params(axis='x', rotation=45)
        
        plt.tight_layout()
        
        # Save the dashboard
        output_path = Path(output_dir) / f"day_{day}_fire_statistics_dashboard.png"
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"✅ Statistics dashboard saved: {output_path}")
        plt.close()
        
    except Exception as e:
        print(f"❌ Error creating statistics dashboard: {e}")

def main():
    """Main function to create all visualizations."""
    print("🎬 Validation Fire Visualization System")
    print("=" * 80)
    
    # Ensure output directory exists
    output_dir = Path("validation_processed_results")
    output_dir.mkdir(exist_ok=True)
    
    # Process both days
    days = [3, 4]
    
    for day in days:
        print(f"\n🔥 PROCESSING DAY {day}")
        print("=" * 50)
        
        # Load data
        forest_model, engine, config, validation_results = load_validation_data(day)
        
        if forest_model is None:
            print(f"❌ Failed to load Day {day} data, skipping...")
            continue
        
        # Create all visualizations
        create_fire_progression_animation(engine, config, day, output_dir)
        create_3d_fire_perimeter_visualization(forest_model, config, day, output_dir)
        create_fire_statistics_dashboard(validation_results, day, output_dir)
        
        print(f"✅ Day {day} visualizations complete!")
    
    print(f"\n🎉 All visualizations saved to: {output_dir}")
    print("\n📁 Generated files:")
    for file in sorted(output_dir.glob("day_*")):
        print(f"   • {file.name}")

if __name__ == "__main__":
    main()
