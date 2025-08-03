#!/usr/bin/env python3
"""
Updated Animation System
Generate comprehensive animations using advanced 3D visualization techniques.
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
    
    print("🎬 Loading Test 1 simulation data for updated animations...")
    
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

def extract_animation_data(model, sample_step=15):
    """Extract data optimized for animation."""
    print("🎞️ Extracting data for animation...")
    
    if not hasattr(model, 'fuel_load') or not hasattr(model.fuel_load, 'shape'):
        print("❌ Model does not have expected fuel_load structure")
        return None
    
    width, height, total_layers = model.fuel_load.shape
    print(f"   Original dimensions: {width}×{height}×{total_layers}")
    
    # Animation-optimized sampling
    sample_width = width // sample_step
    sample_height = height // sample_step
    
    print(f"   Animation grid: {sample_width}×{sample_height}×{total_layers}")
    
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

def create_stratified_layer_animation(fuel_data, fire_data, layer_stats, output_file="test1_stratified_animation.gif"):
    """Create animation showing fire by canopy strata."""
    
    print("🌲 Creating stratified layer animation...")
    
    total_layers = fuel_data.shape[2]
    
    # Define strata
    strata = {
        'Understory (2-10m)': [i for i in range(total_layers) if layer_stats[i]['height_center'] <= 10],
        'Mid-Canopy (10-25m)': [i for i in range(total_layers) if 10 < layer_stats[i]['height_center'] <= 25],
        'Upper Canopy (25-35m)': [i for i in range(total_layers) if 25 < layer_stats[i]['height_center'] <= 35],
        'Emergent (35m+)': [i for i in range(total_layers) if layer_stats[i]['height_center'] > 35]
    }
    
    # Create aggregated data for each stratum
    stratum_data = {}
    for stratum_name, layer_indices in strata.items():
        if layer_indices:
            # Aggregate fire data across layers in stratum
            aggregated_fire = np.zeros((fuel_data.shape[0], fuel_data.shape[1]))
            aggregated_fuel = np.zeros((fuel_data.shape[0], fuel_data.shape[1]))
            
            for layer_idx in layer_indices:
                aggregated_fire += fire_data[:, :, layer_idx]
                aggregated_fuel += fuel_data[:, :, layer_idx]
            
            # Normalize
            aggregated_fire = np.clip(aggregated_fire, 0, 2)
            aggregated_fuel = aggregated_fuel / len(layer_indices)
            
            stratum_data[stratum_name] = {
                'fire': aggregated_fire,
                'fuel': aggregated_fuel,
                'layers': layer_indices,
                'burning_total': sum(layer_stats[i]['burning'] for i in layer_indices)
            }
    
    # Create animation
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    axes = axes.flatten()
    
    # Initialize plots
    ims = []
    titles = []
    
    for i, (stratum_name, data) in enumerate(stratum_data.items()):
        if i < len(axes):
            ax = axes[i]
            
            # Initial image
            im = ax.imshow(data['fire'], cmap='Reds', vmin=0, vmax=2, origin='lower', animated=True)
            ims.append(im)
            
            ax.set_title(f'{stratum_name}\n{data["burning_total"]} burning cells')
            ax.set_xticks([])
            ax.set_yticks([])
            titles.append(ax.title)
    
    # Remove unused subplots
    for i in range(len(stratum_data), len(axes)):
        fig.delaxes(axes[i])
    
    def animate(frame):
        # Simulate temporal evolution (simplified)
        phase = frame / 50.0  # 50 frame animation
        
        updated_artists = []
        
        for i, (stratum_name, data) in enumerate(stratum_data.items()):
            if i < len(ims):
                # Add temporal variation
                fire_evolution = data['fire'] * (0.5 + 0.5 * np.sin(phase * 2 * np.pi + i))
                fire_evolution = np.clip(fire_evolution, 0, 2)
                
                ims[i].set_array(fire_evolution)
                updated_artists.append(ims[i])
        
        return updated_artists
    
    # Create animation
    anim = animation.FuncAnimation(fig, animate, frames=50, interval=200, blit=True, repeat=True)
    
    plt.tight_layout()
    
    # Save animation
    try:
        anim.save(output_file, writer='pillow', fps=5, dpi=100)
        print(f"✅ Stratified animation saved to {output_file}")
    except Exception as e:
        print(f"❌ Error saving animation: {e}")
    
    return anim

def generate_consistent_embers(fuel_data, fire_data, layer_stats, ember_mode='animation'):
    """Generate embers with consistent parameters across all visualizations."""
    
    ember_network = []
    
    # Ember generation parameters
    if ember_mode == 'animation':
        # Reduced for performance
        base_embers_per_cell = 1
        max_embers_per_layer = 50
    else:  # 'analysis' mode
        # Full analysis
        base_embers_per_cell = 3
        max_embers_per_layer = 200
    
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
                
                # Generate embers from this source
                if ember_mode == 'animation':
                    num_embers = base_embers_per_cell
                else:
                    num_embers = np.random.poisson(base_embers_per_cell)
                
                for _ in range(num_embers):
                    # Wind-driven transport (consistent parameters)
                    wind_speed = 5.0
                    wind_direction = 90.0  # East
                    
                    # Transport distance based on height and wind
                    base_distance = wind_speed * np.sqrt(height / 10)
                    transport_distance = base_distance * np.random.lognormal(0, 0.5)
                    
                    # Direction with wind variation
                    angle = math.radians(wind_direction + np.random.normal(0, 30))
                    
                    # Landing position
                    landing_x = source_x + transport_distance * math.cos(angle)
                    landing_y = source_y + transport_distance * math.sin(angle)
                    
                    # Landing height (embers fall)
                    landing_height = max(2, height - np.random.exponential(height/4))
                    
                    # Create trajectory points for animation
                    trajectory_points = []
                    num_points = 20
                    
                    for t in range(num_points):
                        progress = t / (num_points - 1)
                        
                        # Position along trajectory
                        x = source_x + transport_distance * progress * math.cos(angle)
                        y = source_y + transport_distance * progress * math.sin(angle)
                        
                        # Height (parabolic fall)
                        z = height * (1 - progress) + 2 * progress - 0.5 * progress**2 * (height - 2)
                        z = max(2, z)
                        
                        trajectory_points.append((x, y, z))
                    
                    ember_network.append({
                        'source': (source_x, source_y, height),
                        'landing': (landing_x, landing_y, landing_height),
                        'distance': transport_distance,
                        'source_layer': layer_idx,
                        'points': trajectory_points,
                        'color': plt.cm.viridis(layer_idx / fuel_data.shape[2])
                    })
    
    return ember_network

def create_3d_ember_animation(fuel_data, fire_data, layer_stats, history, output_file="test1_3d_ember_animation.gif"):
    """Create 3D ember transport animation with consistent parameters."""
    
    print("🔥 Creating 3D ember transport animation...")
    
    # Generate embers using consistent method
    ember_trajectories = generate_consistent_embers(fuel_data, fire_data, layer_stats, ember_mode='animation')
    
    print(f"   Generated {len(ember_trajectories)} ember trajectories (consistent with network analysis)")
    
    # Create 3D animation
    fig = plt.figure(figsize=(16, 12))
    ax = fig.add_subplot(111, projection='3d')
    
    # Initialize empty plots
    lines = []
    points = []
    
    for ember in ember_trajectories:
        line, = ax.plot([], [], [], color=ember['color'], alpha=0.6, linewidth=1)
        point, = ax.plot([], [], [], 'o', color=ember['color'], markersize=4, alpha=0.8)
        lines.append(line)
        points.append(point)
    
    ax.set_xlabel('X (cells)')
    ax.set_ylabel('Y (cells)')
    ax.set_zlabel('Height (m)')
    ax.set_title(f'3D Ember Transport Animation\n{len(ember_trajectories)} trajectories')
    
    # Set consistent view
    ax.set_xlim(0, fuel_data.shape[0])
    ax.set_ylim(0, fuel_data.shape[1])
    ax.set_zlim(2, 42)
    
    def animate_embers(frame):
        # Animation progress
        progress = (frame % 40) / 40.0
        
        for i, ember in enumerate(ember_trajectories):
            trajectory = ember['points']
            
            if progress < 1.0:
                # Show trajectory up to current progress
                end_idx = max(1, int(progress * len(trajectory)))
                
                if end_idx > 1:
                    traj_segment = trajectory[:end_idx]
                    x_vals, y_vals, z_vals = zip(*traj_segment)
                    
                    lines[i].set_data_3d(x_vals, y_vals, z_vals)
                    
                    # Current ember position
                    current_point = trajectory[end_idx - 1]
                    points[i].set_data_3d([current_point[0]], [current_point[1]], [current_point[2]])
                else:
                    lines[i].set_data_3d([], [], [])
                    points[i].set_data_3d([], [], [])
            else:
                # Reset for next cycle
                lines[i].set_data_3d([], [], [])
                points[i].set_data_3d([], [], [])
        
        return lines + points
    
    # Create animation
    anim = animation.FuncAnimation(fig, animate_embers, frames=80, interval=150, blit=False, repeat=True)
    
    # Save animation
    try:
        anim.save(output_file, writer='pillow', fps=6, dpi=100)
        print(f"✅ 3D ember animation saved to {output_file}")
        
        # Print statistics for comparison
        distances = [e['distance'] for e in ember_trajectories]
        print(f"   Ember statistics:")
        print(f"   - Mean transport distance: {np.mean(distances):.1f} cells")
        print(f"   - Max transport distance: {np.max(distances):.1f} cells")
        print(f"   - 95th percentile: {np.percentile(distances, 95):.1f} cells")
        
    except Exception as e:
        print(f"❌ Error saving animation: {e}")
    
    return anim

def create_vertical_profile_animation(fuel_data, fire_data, layer_stats, history, output_file="test1_vertical_profile_animation.gif"):
    """Create animated vertical fire profile."""
    
    print("📊 Creating vertical profile animation...")
    
    total_layers = fuel_data.shape[2]
    
    # Create figure
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))
    
    # Prepare data
    heights = [layer_stats[i]['height_center'] for i in range(total_layers)]
    burning_counts = [layer_stats[i]['burning'] for i in range(total_layers)]
    fuel_loads = [layer_stats[i]['fuel_mean'] for i in range(total_layers)]
    
    # Initialize plots
    line1, = ax1.plot(heights, burning_counts, 'r-', linewidth=3, marker='o', markersize=6)
    fill1 = ax1.fill_between(heights, burning_counts, alpha=0.3, color='red')
    
    ax1.set_xlabel('Height (m)')
    ax1.set_ylabel('Burning Cells')
    ax1.set_title('Fire Activity Profile')
    ax1.grid(True, alpha=0.3)
    ax1.set_ylim(0, max(burning_counts) * 1.2)
    
    # Fuel distribution
    line2, = ax2.plot(heights, fuel_loads, 'g-', linewidth=3, marker='s', markersize=6)
    fill2 = ax2.fill_between(heights, fuel_loads, alpha=0.3, color='green')
    
    ax2.set_xlabel('Height (m)')
    ax2.set_ylabel('Fuel Load')
    ax2.set_title('Fuel Distribution Profile')
    ax2.grid(True, alpha=0.3)
    ax2.set_ylim(0, max(fuel_loads) * 1.2)
    
    # Add stratum boundaries
    stratum_boundaries = [10, 25, 35]
    colors = ['blue', 'orange', 'purple']
    
    for boundary, color in zip(stratum_boundaries, colors):
        ax1.axvline(boundary, color=color, linestyle='--', alpha=0.7)
        ax2.axvline(boundary, color=color, linestyle='--', alpha=0.7)
    
    def animate_profile(frame):
        try:
            # Simulate temporal variation
            phase = frame / 30.0
            
            # Ensure we have valid data
            if not burning_counts or not heights or len(burning_counts) != len(heights):
                return [line1]
            
            # Vary fire intensity with time
            varied_burning = [count * (0.7 + 0.3 * np.sin(phase * 2 * np.pi + i * 0.1)) 
                             for i, count in enumerate(burning_counts)]
            
            # Ensure varied_burning has same length as heights
            if len(varied_burning) != len(heights):
                return [line1]
            
            # Update fire profile
            line1.set_ydata(varied_burning)
            
            # Remove old fill and create new one
            for collection in ax1.collections:
                collection.remove()
            ax1.fill_between(heights, varied_burning, alpha=0.3, color='red')
            
            # Highlight current peak (with bounds checking)
            peak_idx = -1
            if len(varied_burning) > 0:
                peak_idx = np.argmax(varied_burning)
                if 0 <= peak_idx < len(heights) and 0 <= peak_idx < len(varied_burning):
                    peak_height = heights[peak_idx]
                    peak_value = varied_burning[peak_idx]
                    ax1.plot(peak_height, peak_value, 'yo', markersize=12, alpha=0.8)
            
            # Update title with current stats
            total_burning = sum(varied_burning)
            if len(varied_burning) > 0 and 0 <= peak_idx < len(heights):
                ax1.set_title(f'Fire Activity Profile\nTotal: {total_burning:.0f} cells, Peak: {heights[peak_idx]:.0f}m')
            else:
                ax1.set_title(f'Fire Activity Profile\nTotal: {total_burning:.0f} cells')
            
            return [line1]
            
        except Exception as e:
            print(f"Animation frame {frame} error: {e}")
            return [line1]
    
    # Create animation
    anim = animation.FuncAnimation(fig, animate_profile, frames=60, interval=200, blit=False, repeat=True)
    
    plt.tight_layout()
    
    # Save animation
    try:
        anim.save(output_file, writer='pillow', fps=5, dpi=100)
        print(f"✅ Vertical profile animation saved to {output_file}")
    except Exception as e:
        print(f"❌ Error saving animation: {e}")
    
    return anim

def create_fire_progression_animation(history, fuel_data, fire_data, layer_stats, output_file="test1_fire_progression_animation.gif"):
    """Create fire progression animation over time."""
    
    print("⏱️ Creating fire progression animation...")
    
    # Extract progression data
    progression_data = []
    for step in range(len(history)):
        step_data = history[step]
        active_cells = step_data.get('active_cells', 0)
        progression_data.append(active_cells)
    
    # Create figure
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
    
    # 1. Fire progression over time
    steps = list(range(len(progression_data)))
    line1, = ax1.plot([], [], 'r-', linewidth=2, marker='o', markersize=4)
    ax1.set_xlim(0, len(steps))
    ax1.set_ylim(0, max(progression_data) * 1.1)
    ax1.set_xlabel('Simulation Step')
    ax1.set_ylabel('Active Fire Cells')
    ax1.set_title('Fire Progression Over Time')
    ax1.grid(True, alpha=0.3)
    
    # 2. Current fire distribution by height
    heights = [layer_stats[i]['height_center'] for i in range(fuel_data.shape[2])]
    burning_counts = [layer_stats[i]['burning'] for i in range(fuel_data.shape[2])]
    
    bars2 = ax2.bar(heights, burning_counts, width=1.5, alpha=0.7, color='red')
    ax2.set_xlabel('Height (m)')
    ax2.set_ylabel('Burning Cells')
    ax2.set_title('Current Fire Distribution')
    ax2.grid(True, alpha=0.3)
    
    # 3. Cumulative fire activity
    line3, = ax3.plot([], [], 'orange', linewidth=2)
    ax3.set_xlim(0, len(steps))
    ax3.set_ylim(0, sum(progression_data) * 1.1)
    ax3.set_xlabel('Simulation Step')
    ax3.set_ylabel('Cumulative Fire Activity')
    ax3.set_title('Cumulative Fire Activity')
    ax3.grid(True, alpha=0.3)
    
    # 4. Statistics panel
    ax4.axis('off')
    stats_text = ax4.text(0.1, 0.5, '', transform=ax4.transAxes, fontsize=12,
                         verticalalignment='center', fontfamily='monospace')
    
    def animate_progression(frame):
        current_step = frame % len(progression_data)
        
        # Update progression line
        x_data = steps[:current_step + 1]
        y_data = progression_data[:current_step + 1]
        line1.set_data(x_data, y_data)
        
        # Update cumulative
        cumulative = np.cumsum(progression_data[:current_step + 1])
        line3.set_data(x_data, cumulative)
        
        # Update fire distribution (simulate evolution)
        evolution_factor = 0.5 + 0.5 * (current_step / len(progression_data))
        evolved_burning = [count * evolution_factor for count in burning_counts]
        
        for bar, new_height in zip(bars2, evolved_burning):
            bar.set_height(new_height)
        
        # Update statistics
        current_active = progression_data[current_step]
        total_cumulative = sum(progression_data[:current_step + 1])
        
        stats_text.set_text(f"""
FIRE PROGRESSION STATISTICS

Current Step: {current_step + 1}/{len(progression_data)}
Progress: {(current_step + 1)/len(progression_data)*100:.1f}%

Current Active Cells: {current_active}
Peak Activity: {max(progression_data)}
Total Cumulative: {total_cumulative}

Average Activity: {np.mean(progression_data[:current_step + 1]):.1f}
        """)
        
        return [line1, line3] + list(bars2) + [stats_text]
    
    # Create animation
    anim = animation.FuncAnimation(fig, animate_progression, frames=len(progression_data), 
                                 interval=100, blit=False, repeat=True)
    
    plt.tight_layout()
    
    # Save animation
    try:
        anim.save(output_file, writer='pillow', fps=10, dpi=100)
        print(f"✅ Fire progression animation saved to {output_file}")
    except Exception as e:
        print(f"❌ Error saving animation: {e}")
    
    return anim

def main():
    """Main function for creating updated animations."""
    print("🎬 Updated Animation System")
    print("=" * 80)
    
    try:
        # Load simulation data
        history, model, metadata = load_test1_data()
        
        if history is None:
            print("❌ Failed to load simulation data")
            return
        
        # Extract animation data
        fuel_data, fire_data, layer_stats, width, height = extract_animation_data(model)
        
        if fuel_data is None:
            print("❌ Failed to extract animation data")
            return
        
        print(f"\n🎬 Creating updated animations...")
        print(f"   Animation grid: {width}×{height}×{fuel_data.shape[2]}")
        
        # Create all animations
        print("\n1. Stratified Layer Animation...")
        stratified_anim = create_stratified_layer_animation(fuel_data, fire_data, layer_stats)
        
        print("\n2. 3D Ember Transport Animation...")
        ember_anim = create_3d_ember_animation(fuel_data, fire_data, layer_stats, history)
        
        print("\n3. Vertical Profile Animation...")
        profile_anim = create_vertical_profile_animation(fuel_data, fire_data, layer_stats, history)
        
        print("\n4. Fire Progression Animation...")
        progression_anim = create_fire_progression_animation(history, fuel_data, fire_data, layer_stats)
        
        print("\n🎉 Updated animations complete!")
        print("📁 Generated animation files:")
        print("   • test1_stratified_animation.gif - Fire by canopy strata")
        print("   • test1_3d_ember_animation.gif - 3D ember transport")
        print("   • test1_vertical_profile_animation.gif - Animated vertical profile")
        print("   • test1_fire_progression_animation.gif - Fire progression over time")
        
        print(f"\n✅ Animation Summary:")
        print(f"   • Total layers: {len(layer_stats)}")
        print(f"   • Animation resolution: {width}×{height}")
        print(f"   • Simulation steps: {len(history)}")
        print(f"   • Total burning cells: {sum(s['burning'] for s in layer_stats.values())}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()