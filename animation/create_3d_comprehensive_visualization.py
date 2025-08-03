#!/usr/bin/env python3
"""
Comprehensive 3D Fire Visualization System
Advanced visualization for forest fire simulations with many layers and 3D ember analysis.
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

def load_test1_data():
    """Load Test 1 simulation data."""
    results_dir = Path("results/Test 1/prod_20250614_150108/results")
    
    print("🔥 Loading Test 1 simulation data...")
    
    try:
        # Load simulation history
        history_file = results_dir / "production_simulation_history.pkl"
        with open(history_file, 'rb') as f:
            history = pickle.load(f)
        
        # Load final model state
        model_file = results_dir / "production_final_forest_model_state.pkl"
        with open(model_file, 'rb') as f:
            model = pickle.load(f)
        
        # Load metadata
        metadata_file = results_dir / "animation_data/simulation_metadata.json"
        with open(metadata_file, 'r') as f:
            metadata = json.load(f)
        
        print(f"✅ Loaded {len(history)} simulation steps")
        print(f"✅ Grid size: {metadata['grid_size']}")
        print(f"✅ Layers: {metadata['num_layers']}")
        print(f"✅ Resolution: {metadata['model_resolution']}m per cell")
        
        return history, model, metadata
        
    except Exception as e:
        print(f"❌ Error loading data: {e}")
        return None, None, None

def extract_full_3d_data(model, sample_step=20):
    """Extract complete 3D fire and fuel data from all layers."""
    print("🔍 Extracting COMPLETE 3D model data...")
    
    if not hasattr(model, 'fuel_load') or not hasattr(model.fuel_load, 'shape'):
        print("❌ Model does not have expected fuel_load structure")
        return None
    
    width, height, total_layers = model.fuel_load.shape
    print(f"   Model dimensions: {width}×{height}×{total_layers}")
    
    # Sample the data for performance
    sample_width = width // sample_step
    sample_height = height // sample_step
    
    print(f"   Sampling every {sample_step}th cell: {sample_width}×{sample_height}×{total_layers}")
    
    # Extract ALL layers
    fuel_3d = np.zeros((sample_width, sample_height, total_layers))
    state_3d = np.zeros((sample_width, sample_height, total_layers))
    
    for layer_idx in range(total_layers):
        for x in range(sample_width):
            for y in range(sample_height):
                orig_x = x * sample_step
                orig_y = y * sample_step
                if orig_x < width and orig_y < height:
                    fuel_3d[x, y, layer_idx] = float(model.fuel_load[orig_x, orig_y, layer_idx])
                    state_3d[x, y, layer_idx] = float(model.state[orig_x, orig_y, layer_idx])
    
    # Analyze fire distribution by layer
    layer_stats = {}
    for layer_idx in range(total_layers):
        burning = np.sum(state_3d[:, :, layer_idx] == 1)
        burned = np.sum(state_3d[:, :, layer_idx] == 2)
        fuel_mean = np.mean(fuel_3d[:, :, layer_idx][fuel_3d[:, :, layer_idx] > 0])
        
        # Calculate correct height
        height_bottom = (layer_idx + 1) * 2
        height_top = (layer_idx + 2) * 2
        
        layer_stats[layer_idx] = {
            'burning': burning,
            'burned': burned,
            'fuel_mean': fuel_mean if not np.isnan(fuel_mean) else 0,
            'height_range': (height_bottom, height_top),
            'height_center': (height_bottom + height_top) / 2
        }
        
        if burning > 0 or burned > 0:
            print(f"   Layer {layer_idx} ({height_bottom}-{height_top}m): {burning} burning, {burned} burned, fuel: {fuel_mean:.2f}")
    
    return fuel_3d, state_3d, layer_stats, sample_width, sample_height

def create_vertical_profile_analysis(fuel_3d, state_3d, layer_stats, output_file="test1_vertical_profile.png"):
    """Create comprehensive vertical fire profile analysis."""
    
    print("📊 Creating vertical fire profile analysis...")
    
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
    
    # 1. Fire intensity by height
    layers = list(layer_stats.keys())
    heights = [layer_stats[l]['height_center'] for l in layers]
    burning_counts = [layer_stats[l]['burning'] for l in layers]
    burned_counts = [layer_stats[l]['burned'] for l in layers]
    
    ax1.bar(heights, burning_counts, width=1.5, alpha=0.7, color='red', label='Burning Cells')
    ax1.bar(heights, burned_counts, width=1.5, alpha=0.7, color='black', bottom=burning_counts, label='Burned Cells')
    ax1.set_xlabel('Height (m)')
    ax1.set_ylabel('Number of Cells')
    ax1.set_title('Fire Activity by Canopy Height', fontweight='bold')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # 2. Fuel distribution by height
    fuel_means = [layer_stats[l]['fuel_mean'] for l in layers]
    ax2.plot(heights, fuel_means, 'g-', linewidth=2, marker='o', markersize=4)
    ax2.set_xlabel('Height (m)')
    ax2.set_ylabel('Average Fuel Load')
    ax2.set_title('Fuel Distribution by Height', fontweight='bold')
    ax2.grid(True, alpha=0.3)
    
    # 3. Layer fire intensity comparison
    total_layers = fuel_3d.shape[2]
    layer_subset = list(range(0, total_layers, max(1, total_layers // 4)))  # Show 4 representative layers
    
    # Create stacked bar chart showing fire intensity by layer
    layer_names = [f"L{i}\n{layer_stats[i]['height_range'][0]}-{layer_stats[i]['height_range'][1]}m" 
                   for i in layer_subset[:4]]
    layer_burning = [layer_stats[i]['burning'] for i in layer_subset[:4]]
    layer_burned = [layer_stats[i]['burned'] for i in layer_subset[:4]]
    
    x_pos = range(len(layer_names))
    ax3.bar(x_pos, layer_burning, alpha=0.7, color='red', label='Burning')
    ax3.bar(x_pos, layer_burned, bottom=layer_burning, alpha=0.7, color='darkred', label='Burned')
    
    ax3.set_xticks(x_pos)
    ax3.set_xticklabels(layer_names, fontsize=10)
    ax3.set_ylabel('Number of Cells')
    ax3.set_title('Fire Activity by Representative Layers', fontweight='bold')
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    
    # 4. Fire progression over height (cumulative)
    cumulative_burning = []
    cumulative_burned = []
    running_burning = 0
    running_burned = 0
    
    for height in sorted(heights):
        layer_idx = heights.index(height)
        running_burning += burning_counts[layer_idx]
        running_burned += burned_counts[layer_idx]
        cumulative_burning.append(running_burning)
        cumulative_burned.append(running_burned)
    
    sorted_heights = sorted(heights)
    ax4.plot(sorted_heights, cumulative_burning, 'r-', linewidth=2, marker='o', label='Cumulative Burning')
    ax4.plot(sorted_heights, cumulative_burned, 'k-', linewidth=2, marker='s', label='Cumulative Burned')
    ax4.fill_between(sorted_heights, cumulative_burning, alpha=0.3, color='red')
    ax4.fill_between(sorted_heights, cumulative_burned, alpha=0.3, color='black')
    
    ax4.set_xlabel('Height (m)')
    ax4.set_ylabel('Cumulative Cell Count')
    ax4.set_title('Cumulative Fire Activity by Height', fontweight='bold')
    ax4.legend()
    ax4.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"✅ Vertical profile analysis saved to {output_file}")
    
    return fig

def create_3d_ember_visualization(fuel_3d, state_3d, layer_stats, history, output_file="test1_3d_embers.png"):
    """Create 3D ember generation and transport visualization."""
    
    print("🌪️ Creating 3D ember visualization...")
    
    # Simulate 3D ember generation
    all_embers_3d = []
    
    for step in range(0, len(history), 5):  # Sample every 5 steps
        step_data = history[step]
        active_cells = step_data['active_cells']
        
        if active_cells > 0:
            # Generate embers from all layers
            for layer_idx in range(fuel_3d.shape[2]):
                fire_state = state_3d[:, :, layer_idx]
                burning_cells = np.where(fire_state == 1)
                
                if len(burning_cells[0]) > 0:
                    height_center = layer_stats[layer_idx]['height_center']
                    
                    # Number of embers based on fire intensity and height
                    num_embers = min(len(burning_cells[0]) // 20, 10)
                    
                    for _ in range(num_embers):
                        # Random burning cell
                        idx = np.random.randint(len(burning_cells[0]))
                        source_x = burning_cells[0][idx]
                        source_y = burning_cells[1][idx]
                        source_z = height_center
                        
                        # Ember transport (3D)
                        wind_speed = 5.0
                        wind_direction = 90.0  # East
                        
                        # Transport distance increases with height
                        transport_distance = wind_speed * 2 * np.sqrt(height_center / 10)
                        transport_distance *= np.random.uniform(0.5, 2.0)
                        
                        # 3D landing position
                        wind_angle = math.radians(wind_direction + np.random.normal(0, 30))
                        landing_x = source_x + transport_distance * math.cos(wind_angle)
                        landing_y = source_y + transport_distance * math.sin(wind_angle)
                        
                        # Ember falls down (gravity effect)
                        fall_time = np.random.uniform(2, 8)  # seconds
                        landing_z = max(2, height_center - fall_time * 2)  # Fall rate ~2m/s
                        
                        all_embers_3d.append({
                            'source': (source_x, source_y, source_z),
                            'landing': (landing_x, landing_y, landing_z),
                            'transport_distance': transport_distance,
                            'step': step
                        })
    
    print(f"   Generated {len(all_embers_3d)} 3D ember trajectories")
    
    # Create 3D visualization
    fig = plt.figure(figsize=(20, 12))
    
    # 3D ember trajectory plot
    ax1 = fig.add_subplot(221, projection='3d')
    
    if all_embers_3d:
        # Plot ember trajectories in 3D
        for ember in all_embers_3d[:200]:  # Limit for performance
            source = ember['source']
            landing = ember['landing']
            
            ax1.plot([source[0], landing[0]], 
                    [source[1], landing[1]], 
                    [source[2], landing[2]], 
                    'r-', alpha=0.3, linewidth=0.5)
        
        # Plot source points
        sources = [e['source'] for e in all_embers_3d[:200]]
        if sources:
            sx, sy, sz = zip(*sources)
            ax1.scatter(sx, sy, sz, c='red', s=10, alpha=0.6, label='Ember Sources')
        
        # Plot landing points
        landings = [e['landing'] for e in all_embers_3d[:200]]
        if landings:
            lx, ly, lz = zip(*landings)
            ax1.scatter(lx, ly, lz, c='orange', s=5, alpha=0.4, label='Ember Landings')
    
    ax1.set_xlabel('X (cells)')
    ax1.set_ylabel('Y (cells)')
    ax1.set_zlabel('Height (m)')
    ax1.set_title('3D Ember Trajectories', fontweight='bold')
    ax1.legend()
    
    # Ember transport distance by source height
    ax2 = fig.add_subplot(222)
    
    if all_embers_3d:
        source_heights = [e['source'][2] for e in all_embers_3d]
        distances = [e['transport_distance'] for e in all_embers_3d]
        
        ax2.scatter(source_heights, distances, alpha=0.6, c='orange', s=20)
        
        # Trend line
        if len(source_heights) > 1:
            z = np.polyfit(source_heights, distances, 1)
            p = np.poly1d(z)
            ax2.plot(source_heights, p(source_heights), "r--", alpha=0.8,
                    label=f'Trend: y = {z[0]:.2f}x + {z[1]:.1f}')
    
    ax2.set_xlabel('Source Height (m)')
    ax2.set_ylabel('Transport Distance (cells)')
    ax2.set_title('Height vs Transport Distance', fontweight='bold')
    ax2.grid(True, alpha=0.3)
    ax2.legend()
    
    # Ember landing height distribution
    ax3 = fig.add_subplot(223)
    
    if all_embers_3d:
        landing_heights = [e['landing'][2] for e in all_embers_3d]
        ax3.hist(landing_heights, bins=20, alpha=0.7, color='orange', edgecolor='black')
        ax3.axvline(np.mean(landing_heights), color='red', linestyle='--',
                   label=f'Mean: {np.mean(landing_heights):.1f}m')
    
    ax3.set_xlabel('Landing Height (m)')
    ax3.set_ylabel('Frequency')
    ax3.set_title('Ember Landing Height Distribution', fontweight='bold')
    ax3.grid(True, alpha=0.3)
    ax3.legend()
    
    # Ember generation by layer
    ax4 = fig.add_subplot(224)
    
    layer_ember_counts = {}
    for ember in all_embers_3d:
        source_height = ember['source'][2]
        layer_key = f"{int(source_height-1)}-{int(source_height+1)}m"
        layer_ember_counts[layer_key] = layer_ember_counts.get(layer_key, 0) + 1
    
    if layer_ember_counts:
        layers = list(layer_ember_counts.keys())
        counts = list(layer_ember_counts.values())
        
        ax4.bar(range(len(layers)), counts, alpha=0.7, color='red')
        ax4.set_xticks(range(len(layers)))
        ax4.set_xticklabels(layers, rotation=45)
        ax4.set_xlabel('Source Layer Height')
        ax4.set_ylabel('Ember Count')
        ax4.set_title('Ember Generation by Layer', fontweight='bold')
        ax4.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"✅ 3D ember visualization saved to {output_file}")
    
    return fig, all_embers_3d

def create_comprehensive_layer_summary(layer_stats, output_file="test1_layer_summary.png"):
    """Create comprehensive summary of all layers."""
    
    print("📋 Creating comprehensive layer summary...")
    
    # Calculate summary statistics
    total_layers = len(layer_stats)
    active_layers = sum(1 for stats in layer_stats.values() if stats['burning'] > 0 or stats['burned'] > 0)
    total_burning = sum(stats['burning'] for stats in layer_stats.values())
    total_burned = sum(stats['burned'] for stats in layer_stats.values())
    
    # Find peak fire activity
    peak_layer = max(layer_stats.keys(), key=lambda k: layer_stats[k]['burning'])
    peak_height = layer_stats[peak_layer]['height_center']
    
    # Create summary figure
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
    
    # 1. Fire activity overview
    layers = list(layer_stats.keys())
    heights = [layer_stats[l]['height_center'] for l in layers]
    burning = [layer_stats[l]['burning'] for l in layers]
    
    ax1.plot(heights, burning, 'r-', linewidth=3, marker='o', markersize=6)
    ax1.axvline(peak_height, color='orange', linestyle='--', alpha=0.7, 
               label=f'Peak Activity: {peak_height:.0f}m')
    ax1.set_xlabel('Height (m)')
    ax1.set_ylabel('Burning Cells')
    ax1.set_title(f'Fire Activity Profile\n{total_layers} Layers, {active_layers} Active', fontweight='bold')
    ax1.grid(True, alpha=0.3)
    ax1.legend()
    
    # 2. Cumulative fire load
    cumulative_burning = np.cumsum(burning)
    ax2.fill_between(heights, cumulative_burning, alpha=0.6, color='red')
    ax2.set_xlabel('Height (m)')
    ax2.set_ylabel('Cumulative Burning Cells')
    ax2.set_title('Cumulative Fire Load by Height', fontweight='bold')
    ax2.grid(True, alpha=0.3)
    
    # 3. Layer classification
    understory_layers = [l for l in layers if layer_stats[l]['height_center'] <= 10]
    midcanopy_layers = [l for l in layers if 10 < layer_stats[l]['height_center'] <= 25]
    canopy_layers = [l for l in layers if layer_stats[l]['height_center'] > 25]
    
    categories = ['Understory\n(2-10m)', 'Mid-Canopy\n(10-25m)', 'Canopy\n(25m+)']
    category_counts = [len(understory_layers), len(midcanopy_layers), len(canopy_layers)]
    category_burning = [
        sum(layer_stats[l]['burning'] for l in understory_layers),
        sum(layer_stats[l]['burning'] for l in midcanopy_layers),
        sum(layer_stats[l]['burning'] for l in canopy_layers)
    ]
    
    x = np.arange(len(categories))
    width = 0.35
    
    ax3.bar(x - width/2, category_counts, width, label='Total Layers', alpha=0.7, color='green')
    ax3.bar(x + width/2, category_burning, width, label='Burning Cells', alpha=0.7, color='red')
    ax3.set_xlabel('Canopy Stratum')
    ax3.set_ylabel('Count')
    ax3.set_title('Fire Activity by Canopy Stratum', fontweight='bold')
    ax3.set_xticks(x)
    ax3.set_xticklabels(categories)
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    
    # 4. Statistics table
    ax4.axis('off')
    
    stats_text = f"""
COMPREHENSIVE LAYER ANALYSIS SUMMARY

LAYER STRUCTURE:
• Total Layers: {total_layers}
• Active Layers: {active_layers}
• Height Range: {heights[0]:.0f}m - {heights[-1]:.0f}m
• Layer Interval: 2m

FIRE ACTIVITY:
• Total Burning Cells: {total_burning:,}
• Total Burned Cells: {total_burned:,}
• Peak Activity Layer: {peak_layer} ({peak_height:.0f}m)
• Peak Burning Cells: {layer_stats[peak_layer]['burning']}

CANOPY DISTRIBUTION:
• Understory Layers (2-10m): {len(understory_layers)}
• Mid-Canopy Layers (10-25m): {len(midcanopy_layers)}
• Canopy Layers (25m+): {len(canopy_layers)}

FIRE INTENSITY BY STRATUM:
• Understory Fire: {sum(layer_stats[l]['burning'] for l in understory_layers)} cells
• Mid-Canopy Fire: {sum(layer_stats[l]['burning'] for l in midcanopy_layers)} cells
• Canopy Fire: {sum(layer_stats[l]['burning'] for l in canopy_layers)} cells

MODEL CONFIGURATION:
• Ground Layer (0-2m): EXCLUDED
• Model Resolution: 33.33m per cell
• Sampling: Every 20th cell for visualization
    """
    
    ax4.text(0.05, 0.95, stats_text, transform=ax4.transAxes, fontsize=10,
            verticalalignment='top', fontfamily='monospace',
            bbox=dict(boxstyle='round', facecolor='lightgray', alpha=0.8))
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"✅ Layer summary saved to {output_file}")
    
    return fig

def create_interactive_layer_browser(fuel_3d, state_3d, layer_stats, output_file="test1_layer_browser.gif"):
    """Create an animated browser through all layers."""
    
    print("🎬 Creating interactive layer browser animation...")
    
    total_layers = fuel_3d.shape[2]
    
    # Create figure
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
    
    # Initialize plots
    im1 = ax1.imshow(fuel_3d[:, :, 0], cmap='Greens', origin='lower')
    ax1.set_title('Fuel Load')
    
    im2 = ax2.imshow(state_3d[:, :, 0], cmap='Reds', vmin=0, vmax=2, origin='lower')
    ax2.set_title('Fire State')
    
    # Profile plot
    heights = [layer_stats[l]['height_center'] for l in range(total_layers)]
    burning = [layer_stats[l]['burning'] for l in range(total_layers)]
    line, = ax3.plot(heights, burning, 'r-', linewidth=2)
    marker, = ax3.plot([], [], 'ro', markersize=10)
    ax3.set_xlabel('Height (m)')
    ax3.set_ylabel('Burning Cells')
    ax3.set_title('Fire Profile')
    ax3.grid(True, alpha=0.3)
    
    # Layer info
    ax4.axis('off')
    info_text = ax4.text(0.1, 0.5, '', transform=ax4.transAxes, fontsize=12,
                        verticalalignment='center', fontfamily='monospace')
    
    def animate(frame):
        layer_idx = frame % total_layers
        
        # Update images
        im1.set_array(fuel_3d[:, :, layer_idx])
        im2.set_array(state_3d[:, :, layer_idx])
        
        # Update marker
        height = layer_stats[layer_idx]['height_center']
        burning_count = layer_stats[layer_idx]['burning']
        marker.set_data([height], [burning_count])
        
        # Update info
        stats = layer_stats[layer_idx]
        height_range = stats['height_range']
        info_text.set_text(f"""
LAYER {layer_idx}

Height: {height_range[0]}-{height_range[1]}m
Center: {height:.1f}m

Fire Activity:
• Burning: {stats['burning']} cells
• Burned: {stats['burned']} cells
• Fuel Avg: {stats['fuel_mean']:.2f}

Progress: {layer_idx+1}/{total_layers}
        """)
        
        # Update titles
        ax1.set_title(f'Fuel Load - Layer {layer_idx} ({height_range[0]}-{height_range[1]}m)')
        ax2.set_title(f'Fire State - Layer {layer_idx} ({height_range[0]}-{height_range[1]}m)')
        
        return [im1, im2, line, marker, info_text]
    
    # Create animation
    anim = animation.FuncAnimation(fig, animate, frames=total_layers*2, 
                                 interval=300, blit=False, repeat=True)
    
    # Save animation
    try:
        anim.save(output_file, writer='pillow', fps=3, dpi=100)
        print(f"✅ Layer browser animation saved to {output_file}")
    except Exception as e:
        print(f"❌ Error saving animation: {e}")
    
    return anim

def main():
    """Main function for comprehensive 3D visualization."""
    print("🎬 Comprehensive 3D Fire Visualization System")
    print("=" * 80)
    
    try:
        # Load simulation data
        history, model, metadata = load_test1_data()
        
        if history is None:
            print("❌ Failed to load simulation data")
            return
        
        # Extract complete 3D data
        fuel_3d, state_3d, layer_stats, width, height = extract_full_3d_data(model)
        
        if fuel_3d is None:
            print("❌ Failed to extract 3D data")
            return
        
        print(f"\n📊 Creating comprehensive visualizations...")
        print(f"   Grid: {width}×{height}×{fuel_3d.shape[2]}")
        
        # Create all visualizations
        print("\n1. Vertical Profile Analysis...")
        profile_fig = create_vertical_profile_analysis(fuel_3d, state_3d, layer_stats)
        
        print("\n2. 3D Ember Visualization...")
        ember_fig, embers_3d = create_3d_ember_visualization(fuel_3d, state_3d, layer_stats, history)
        
        print("\n3. Comprehensive Layer Summary...")
        summary_fig = create_comprehensive_layer_summary(layer_stats)
        
        print("\n4. Interactive Layer Browser...")
        browser_anim = create_interactive_layer_browser(fuel_3d, state_3d, layer_stats)
        
        print("\n🎉 Comprehensive 3D visualization complete!")
        print("📁 Generated files:")
        print("   • test1_vertical_profile.png - Fire activity by height")
        print("   • test1_3d_embers.png - 3D ember analysis")
        print("   • test1_layer_summary.png - Complete layer overview")
        print("   • test1_layer_browser.gif - Interactive layer browser")
        
        print(f"\n✅ Analysis Summary:")
        print(f"   • Total layers analyzed: {len(layer_stats)}")
        print(f"   • Active layers: {sum(1 for s in layer_stats.values() if s['burning'] > 0)}")
        print(f"   • 3D embers simulated: {len(embers_3d) if 'embers_3d' in locals() else 0}")
        print(f"   • Height range: 2-{max(s['height_range'][1] for s in layer_stats.values())}m")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()