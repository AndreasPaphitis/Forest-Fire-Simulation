#!/usr/bin/env python3
"""
Interactive Fire Explorer System
Advanced interactive visualization for exploring fire behavior across many layers.
"""
import sys
import pickle
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.widgets import Slider, Button, CheckButtons
from matplotlib.colors import ListedColormap, LinearSegmentedColormap
from mpl_toolkits.mplot3d import Axes3D
from pathlib import Path
import json
import math

def load_validation_data(day=3):
    """Load validation simulation data."""
    results_dir = Path("validation_results_optimized")
    
    print(f"🔥 Loading Day {day} validation data for interactive exploration...")
    
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
        
        return history, model, metadata
        
    except Exception as e:
        print(f"❌ Error loading data: {e}")
        return None, None, None

def extract_efficient_data(model, sample_step=15):
    """Extract data efficiently for interactive exploration."""
    print("⚡ Extracting data for interactive exploration...")
    
    if not hasattr(model, 'fuel_load') or not hasattr(model.fuel_load, 'shape'):
        print("❌ Model does not have expected fuel_load structure")
        return None
    
    width, height, total_layers = model.fuel_load.shape
    print(f"   Original dimensions: {width}×{height}×{total_layers}")
    
    # Efficient sampling
    sample_width = width // sample_step
    sample_height = height // sample_step
    
    print(f"   Interactive grid: {sample_width}×{sample_height}×{total_layers}")
    
    # Extract data
    fuel_data = np.zeros((sample_width, sample_height, total_layers))
    fire_data = np.zeros((sample_width, sample_height, total_layers))
    
    for layer_idx in range(total_layers):
        for x in range(sample_width):
            for y in range(sample_height):
                orig_x = x * sample_step
                orig_y = y * sample_step
                if orig_x < width and orig_y < height:
                    fuel_data[x, y, layer_idx] = float(model.fuel_load[orig_x, orig_y, layer_idx])
                    fire_data[x, y, layer_idx] = float(model.state[orig_x, orig_y, layer_idx])
    
    # Calculate layer statistics
    layer_stats = {}
    for layer_idx in range(total_layers):
        burning = np.sum(fire_data[:, :, layer_idx] == 1)
        burned = np.sum(fire_data[:, :, layer_idx] == 2)
        fuel_mean = np.mean(fuel_data[:, :, layer_idx][fuel_data[:, :, layer_idx] > 0])
        
        height_bottom = (layer_idx + 1) * 2
        height_top = (layer_idx + 2) * 2
        
        layer_stats[layer_idx] = {
            'burning': burning,
            'burned': burned,
            'fuel_mean': fuel_mean if not np.isnan(fuel_mean) else 0,
            'height_range': (height_bottom, height_top),
            'height_center': (height_bottom + height_top) / 2
        }
    
    return fuel_data, fire_data, layer_stats, sample_width, sample_height

def create_layer_aggregation_analysis(fuel_data, fire_data, layer_stats, output_file="test1_layer_aggregation.png"):
    """Create aggregated analysis for handling many layers efficiently."""
    
    print("📊 Creating layer aggregation analysis...")
    
    total_layers = fuel_data.shape[2]
    
    # Define layer groups for aggregation
    layer_groups = {
        'Understory (2-10m)': [i for i in range(total_layers) if layer_stats[i]['height_center'] <= 10],
        'Mid-Canopy (10-25m)': [i for i in range(total_layers) if 10 < layer_stats[i]['height_center'] <= 25],
        'Upper Canopy (25-35m)': [i for i in range(total_layers) if 25 < layer_stats[i]['height_center'] <= 35],
        'Emergent (35m+)': [i for i in range(total_layers) if layer_stats[i]['height_center'] > 35]
    }
    
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
    
    # 1. Aggregated fire intensity by stratum
    group_names = list(layer_groups.keys())
    group_burning = []
    group_fuel = []
    
    for group_name, layer_indices in layer_groups.items():
        total_burning = sum(layer_stats[i]['burning'] for i in layer_indices)
        avg_fuel = np.mean([layer_stats[i]['fuel_mean'] for i in layer_indices if layer_stats[i]['fuel_mean'] > 0])
        
        group_burning.append(total_burning)
        group_fuel.append(avg_fuel if not np.isnan(avg_fuel) else 0)
    
    x = np.arange(len(group_names))
    width = 0.35
    
    bars1 = ax1.bar(x - width/2, group_burning, width, label='Burning Cells', color='red', alpha=0.7)
    ax1_twin = ax1.twinx()
    bars2 = ax1_twin.bar(x + width/2, group_fuel, width, label='Avg Fuel Load', color='green', alpha=0.7)
    
    ax1.set_xlabel('Canopy Stratum')
    ax1.set_ylabel('Burning Cells', color='red')
    ax1_twin.set_ylabel('Average Fuel Load', color='green')
    ax1.set_title('Fire Activity by Canopy Stratum', fontweight='bold')
    ax1.set_xticks(x)
    ax1.set_xticklabels(group_names, rotation=45)
    ax1.grid(True, alpha=0.3)
    
    # Add value labels
    for bar, value in zip(bars1, group_burning):
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                f'{int(value)}', ha='center', va='bottom')
    
    # 2. Vertical fire profile (all layers)
    layers = list(range(total_layers))
    heights = [layer_stats[i]['height_center'] for i in layers]
    burning_counts = [layer_stats[i]['burning'] for i in layers]
    
    ax2.plot(heights, burning_counts, 'r-', linewidth=2, marker='o', markersize=4)
    ax2.fill_between(heights, burning_counts, alpha=0.3, color='red')
    
    # Add stratum boundaries
    stratum_boundaries = [10, 25, 35]
    colors = ['blue', 'orange', 'purple']
    labels = ['Understory/Mid-Canopy', 'Mid/Upper Canopy', 'Upper/Emergent']
    
    for boundary, color, label in zip(stratum_boundaries, colors, labels):
        ax2.axvline(boundary, color=color, linestyle='--', alpha=0.7, label=label)
    
    ax2.set_xlabel('Height (m)')
    ax2.set_ylabel('Burning Cells')
    ax2.set_title('Complete Vertical Fire Profile', fontweight='bold')
    ax2.grid(True, alpha=0.3)
    ax2.legend()
    
    # 3. Layer efficiency analysis
    layer_efficiency = []
    for i in range(total_layers):
        burning = layer_stats[i]['burning']
        fuel = layer_stats[i]['fuel_mean']
        efficiency = burning / fuel if fuel > 0 else 0
        layer_efficiency.append(efficiency)
    
    ax3.bar(heights, layer_efficiency, width=1.5, alpha=0.7, color='orange')
    ax3.set_xlabel('Height (m)')
    ax3.set_ylabel('Fire Efficiency (Burning/Fuel)')
    ax3.set_title('Fire Efficiency by Layer', fontweight='bold')
    ax3.grid(True, alpha=0.3)
    
    # 4. Cumulative analysis
    cumulative_burning = np.cumsum(burning_counts)
    cumulative_fuel = np.cumsum([layer_stats[i]['fuel_mean'] for i in layers])
    
    ax4.plot(heights, cumulative_burning, 'r-', linewidth=2, label='Cumulative Burning')
    ax4_twin = ax4.twinx()
    ax4_twin.plot(heights, cumulative_fuel, 'g-', linewidth=2, label='Cumulative Fuel')
    
    ax4.set_xlabel('Height (m)')
    ax4.set_ylabel('Cumulative Burning Cells', color='red')
    ax4_twin.set_ylabel('Cumulative Fuel Load', color='green')
    ax4.set_title('Cumulative Fire and Fuel Distribution', fontweight='bold')
    ax4.grid(True, alpha=0.3)
    
    # Add legends
    ax4.legend(loc='upper left')
    ax4_twin.legend(loc='upper right')
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"✅ Layer aggregation analysis saved to {output_file}")
    
    return fig, layer_groups

def create_3d_ember_network(fuel_data, fire_data, layer_stats, history, output_file="test1_ember_network.png"):
    """Create 3D ember transport network visualization."""
    
    print("🕸️ Creating 3D ember transport network...")
    
    # Generate ember network with consistent parameters
    ember_network = []
    
    # Ember generation parameters (consistent with animation)
    base_embers_per_cell = 3  # Analysis mode - more comprehensive
    max_embers_per_layer = 200
    
    # Create ember sources from all burning cells
    for layer_idx in range(fuel_data.shape[2]):
        fire_layer = fire_data[:, :, layer_idx]
        burning_cells = np.where(fire_layer == 1)
        
        if len(burning_cells[0]) > 0:
            height = layer_stats[layer_idx]['height_center']
            
            # Limit embers for performance if needed
            num_sources = min(len(burning_cells[0]), max_embers_per_layer // base_embers_per_cell)
            
            for i in range(num_sources):
                source_x = burning_cells[0][i]
                source_y = burning_cells[1][i]
                
                # Generate multiple ember trajectories from each source
                num_embers = np.random.poisson(base_embers_per_cell)  # Poisson distribution for realism
                
                for _ in range(num_embers):
                    # Wind-driven transport (consistent parameters)
                    wind_speed = 5.0
                    wind_direction = 90.0  # East
                    
                    # Transport distance based on height and wind (consistent formula)
                    base_distance = wind_speed * np.sqrt(height / 10)
                    transport_distance = base_distance * np.random.lognormal(0, 0.5)
                    
                    # Direction with wind variation (consistent)
                    angle = math.radians(wind_direction + np.random.normal(0, 30))
                    
                    # Landing position
                    landing_x = source_x + transport_distance * math.cos(angle)
                    landing_y = source_y + transport_distance * math.sin(angle)
                    
                    # Landing height (embers fall) - consistent formula
                    landing_height = max(2, height - np.random.exponential(height/4))
                    
                    ember_network.append({
                        'source': (source_x, source_y, height),
                        'landing': (landing_x, landing_y, landing_height),
                        'distance': transport_distance,
                        'source_layer': layer_idx
                    })
    
    print(f"   Generated {len(ember_network)} ember connections (consistent with animation parameters)")
    
    # Create network visualization
    fig = plt.figure(figsize=(20, 12))
    
    # 1. 3D ember network
    ax1 = fig.add_subplot(221, projection='3d')
    
    # Plot ember trajectories as network edges
    for ember in ember_network[:500]:  # Limit for performance
        source = ember['source']
        landing = ember['landing']
        
        # Color by source layer
        layer_color = plt.cm.viridis(ember['source_layer'] / fuel_data.shape[2])
        
        ax1.plot([source[0], landing[0]], 
                [source[1], landing[1]], 
                [source[2], landing[2]], 
                color=layer_color, alpha=0.3, linewidth=0.5)
    
    # Plot nodes (sources and landings)
    sources = [e['source'] for e in ember_network[:500]]
    landings = [e['landing'] for e in ember_network[:500]]
    
    if sources:
        sx, sy, sz = zip(*sources)
        ax1.scatter(sx, sy, sz, c='red', s=20, alpha=0.8, label='Sources')
    
    if landings:
        lx, ly, lz = zip(*landings)
        ax1.scatter(lx, ly, lz, c='orange', s=10, alpha=0.6, label='Landings')
    
    ax1.set_xlabel('X (cells)')
    ax1.set_ylabel('Y (cells)')
    ax1.set_zlabel('Height (m)')
    ax1.set_title('3D Ember Transport Network', fontweight='bold')
    ax1.legend()
    
    # 2. Network connectivity analysis
    ax2 = fig.add_subplot(222)
    
    # Analyze connectivity by layer
    layer_connections = {}
    for ember in ember_network:
        layer = ember['source_layer']
        if layer not in layer_connections:
            layer_connections[layer] = 0
        layer_connections[layer] += 1
    
    layers = list(layer_connections.keys())
    connections = list(layer_connections.values())
    heights = [layer_stats[l]['height_center'] for l in layers]
    
    bars = ax2.bar(heights, connections, width=1.5, alpha=0.7, color='purple')
    ax2.set_xlabel('Source Height (m)')
    ax2.set_ylabel('Number of Ember Connections')
    ax2.set_title('Ember Generation by Layer', fontweight='bold')
    ax2.grid(True, alpha=0.3)
    
    # Add value labels
    for bar, value in zip(bars, connections):
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                f'{int(value)}', ha='center', va='bottom', fontsize=8)
    
    # 3. Transport distance distribution
    ax3 = fig.add_subplot(223)
    
    distances = [e['distance'] for e in ember_network]
    ax3.hist(distances, bins=30, alpha=0.7, color='orange', edgecolor='black')
    ax3.axvline(np.mean(distances), color='red', linestyle='--',
               label=f'Mean: {np.mean(distances):.1f} cells')
    ax3.axvline(np.percentile(distances, 95), color='purple', linestyle='--',
               label=f'95th percentile: {np.percentile(distances, 95):.1f} cells')
    
    ax3.set_xlabel('Transport Distance (cells)')
    ax3.set_ylabel('Frequency')
    ax3.set_title('Ember Transport Distance Distribution', fontweight='bold')
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    
    # 4. Risk assessment heatmap
    ax4 = fig.add_subplot(224)
    
    # Create landing density heatmap
    if landings:
        lx, ly, lz = zip(*landings)
        
        # Create 2D histogram
        hist, xedges, yedges = np.histogram2d(lx, ly, bins=20)
        extent = [xedges[0], xedges[-1], yedges[0], yedges[-1]]
        
        im = ax4.imshow(hist.T, extent=extent, origin='lower', cmap='Reds', alpha=0.8)
        ax4.set_xlabel('X (cells)')
        ax4.set_ylabel('Y (cells)')
        ax4.set_title('Ember Landing Risk Heatmap', fontweight='bold')
        
        # Add colorbar
        cbar = plt.colorbar(im, ax=ax4)
        cbar.set_label('Landing Density')
        
        # Add contour lines for risk zones
        ax4.contour(hist.T, extent=extent, levels=5, colors='black', alpha=0.5, linewidths=1)
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"✅ 3D ember network saved to {output_file}")
    
    return fig, ember_network

def create_fire_dynamics_summary(fuel_data, fire_data, layer_stats, history, output_file="test1_fire_dynamics.png"):
    """Create comprehensive fire dynamics summary."""
    
    print("🔥 Creating fire dynamics summary...")
    
    total_layers = fuel_data.shape[2]
    
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
    
    # 1. Fire intensity vs height with trend analysis
    heights = [layer_stats[i]['height_center'] for i in range(total_layers)]
    burning_counts = [layer_stats[i]['burning'] for i in range(total_layers)]
    fuel_loads = [layer_stats[i]['fuel_mean'] for i in range(total_layers)]
    
    # Primary plot
    ax1.scatter(heights, burning_counts, s=100, c=fuel_loads, cmap='Greens', alpha=0.7, edgecolors='black')
    
    # Trend line
    if len(heights) > 1:
        z = np.polyfit(heights, burning_counts, 2)  # Quadratic fit
        p = np.poly1d(z)
        ax1.plot(heights, p(heights), "r--", alpha=0.8, linewidth=2, label='Trend')
    
    ax1.set_xlabel('Height (m)')
    ax1.set_ylabel('Burning Cells')
    ax1.set_title('Fire Intensity vs Height\n(Color = Fuel Load)', fontweight='bold')
    ax1.grid(True, alpha=0.3)
    ax1.legend()
    
    # Add colorbar
    cbar1 = plt.colorbar(ax1.collections[0], ax=ax1)
    cbar1.set_label('Fuel Load')
    
    # 2. Fire progression analysis
    # Simulate progression based on history
    progression_data = []
    for step in range(0, len(history), 5):
        step_data = history[step]
        active_cells = step_data.get('active_cells', 0)
        progression_data.append(active_cells)
    
    steps = list(range(0, len(history), 5))
    ax2.plot(steps, progression_data, 'r-', linewidth=2, marker='o', markersize=4)
    ax2.fill_between(steps, progression_data, alpha=0.3, color='red')
    
    # Add phases
    if len(progression_data) > 0:
        max_activity = max(progression_data)
        max_step = steps[progression_data.index(max_activity)]
        
        ax2.axvline(max_step, color='orange', linestyle='--', alpha=0.7, 
                   label=f'Peak Activity: Step {max_step}')
    
    ax2.set_xlabel('Simulation Step')
    ax2.set_ylabel('Active Fire Cells')
    ax2.set_title('Fire Progression Over Time', fontweight='bold')
    ax2.grid(True, alpha=0.3)
    ax2.legend()
    
    # 3. Layer interaction matrix
    # Calculate layer-to-layer fire spread potential
    interaction_matrix = np.zeros((total_layers, total_layers))
    
    for i in range(total_layers):
        for j in range(total_layers):
            if i != j:
                height_diff = abs(layer_stats[i]['height_center'] - layer_stats[j]['height_center'])
                fire_i = layer_stats[i]['burning']
                fire_j = layer_stats[j]['burning']
                
                # Interaction strength based on proximity and fire activity
                if height_diff <= 4:  # Adjacent layers
                    interaction_matrix[i, j] = min(fire_i, fire_j) / max(fire_i + fire_j, 1)
    
    im3 = ax3.imshow(interaction_matrix, cmap='Reds', aspect='auto')
    ax3.set_xlabel('Target Layer')
    ax3.set_ylabel('Source Layer')
    ax3.set_title('Layer Interaction Matrix', fontweight='bold')
    
    # Add layer height labels
    layer_labels = [f'L{i}\n{layer_stats[i]["height_center"]:.0f}m' for i in range(0, total_layers, 2)]
    ax3.set_xticks(range(0, total_layers, 2))
    ax3.set_xticklabels(layer_labels, fontsize=8)
    ax3.set_yticks(range(0, total_layers, 2))
    ax3.set_yticklabels(layer_labels, fontsize=8)
    
    plt.colorbar(im3, ax=ax3, label='Interaction Strength')
    
    # 4. Fire behavior classification
    # Classify fire behavior by layer characteristics
    behavior_classes = {
        'Surface Fire': [],
        'Ladder Fire': [],
        'Crown Fire': [],
        'Spotting Fire': []
    }
    
    for i in range(total_layers):
        height = layer_stats[i]['height_center']
        burning = layer_stats[i]['burning']
        fuel = layer_stats[i]['fuel_mean']
        
        if height <= 6:
            behavior_classes['Surface Fire'].append(burning)
        elif 6 < height <= 15 and burning > 0:
            behavior_classes['Ladder Fire'].append(burning)
        elif height > 15 and burning > 15:
            behavior_classes['Crown Fire'].append(burning)
        elif burning > 0:
            behavior_classes['Spotting Fire'].append(burning)
    
    # Calculate totals
    class_totals = {k: sum(v) for k, v in behavior_classes.items() if v}
    
    if class_totals:
        classes = list(class_totals.keys())
        totals = list(class_totals.values())
        colors = ['brown', 'orange', 'red', 'purple']
        
        wedges, texts, autotexts = ax4.pie(totals, labels=classes, colors=colors[:len(classes)], 
                                          autopct='%1.1f%%', startangle=90)
        ax4.set_title('Fire Behavior Classification', fontweight='bold')
        
        # Enhance text
        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_fontweight('bold')
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"✅ Fire dynamics summary saved to {output_file}")
    
    return fig

def main():
    """Main function for interactive fire exploration."""
    print("🎮 Interactive Fire Explorer System")
    print("=" * 80)
    
    try:
        # Load simulation data
        history, model, metadata = load_test1_data()
        
        if history is None:
            print("❌ Failed to load simulation data")
            return
        
        # Extract data efficiently
        fuel_data, fire_data, layer_stats, width, height = extract_efficient_data(model)
        
        if fuel_data is None:
            print("❌ Failed to extract data")
            return
        
        print(f"\n🎮 Creating interactive visualizations...")
        print(f"   Interactive grid: {width}×{height}×{fuel_data.shape[2]}")
        
        # Create all visualizations
        print("\n1. Layer Aggregation Analysis...")
        agg_fig, layer_groups = create_layer_aggregation_analysis(fuel_data, fire_data, layer_stats)
        
        print("\n2. 3D Ember Network...")
        network_fig, ember_network = create_3d_ember_network(fuel_data, fire_data, layer_stats, history)
        
        print("\n3. Fire Dynamics Summary...")
        dynamics_fig = create_fire_dynamics_summary(fuel_data, fire_data, layer_stats, history)
        
        print("\n🎉 Interactive fire exploration complete!")
        print("📁 Generated files:")
        print("   • test1_layer_aggregation.png - Efficient layer analysis")
        print("   • test1_ember_network.png - 3D ember transport network")
        print("   • test1_fire_dynamics.png - Comprehensive fire dynamics")
        
        print(f"\n✅ Interactive Analysis Summary:")
        print(f"   • Total layers: {len(layer_stats)}")
        print(f"   • Layer groups: {len(layer_groups)}")
        print(f"   • Ember network connections: {len(ember_network) if 'ember_network' in locals() else 0}")
        print(f"   • Interactive resolution: {width}×{height}")
        
        # Print layer group summary
        print(f"\n📊 Layer Group Analysis:")
        for group_name, layer_indices in layer_groups.items():
            total_burning = sum(layer_stats[i]['burning'] for i in layer_indices)
            print(f"   • {group_name}: {len(layer_indices)} layers, {total_burning} burning cells")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()