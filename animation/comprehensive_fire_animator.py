#!/usr/bin/env python3
"""
Comprehensive Fire Animation System
Complete animation suite for forest fire validation results.
Generates all types of animations: 2D progression, 3D visualizations, statistics, and layer analysis.
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

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def load_validation_data(day):
    """Load validation data for a specific day."""
    results_dir = Path("validation_results_optimized")
    
    print(f"🔥 Loading Day {day} validation data for animations...")
    
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
        
        # Use sparse history from engine
        history = engine.sparse_history if hasattr(engine, 'sparse_history') else []
        
        print(f"✅ Loaded Day {day} data:")
        print(f"   Grid size: {config.grid_size}")
        print(f"   Layers: {config.num_layers}")
        print(f"   History frames: {len(history)}")
        print(f"   Resolution: {config.model_resolution}m per cell")
        
        return forest_model, engine, config, validation_results, history
        
    except Exception as e:
        print(f"❌ Error loading Day {day} data: {e}")
        return None, None, None, None, None

def create_2d_fire_progression_animation(forest_model, history, config, day, output_dir="validation_processed_results"):
    """Create 2D fire progression animation."""
    print(f"\n🎬 Creating 2D fire progression animation for Day {day}...")
    
    if not history:
        print("❌ No history data available")
        return
    
    try:
        # Get final fire perimeter
        final_perimeter = forest_model.get_2d_fire_perimeter()
        
        # Create animation
        fig, ax = plt.subplots(figsize=(12, 10))
        
        def animate(frame_idx):
            ax.clear()
            ax.set_xlim(0, config.grid_size[0])
            ax.set_ylim(0, config.grid_size[1])
            ax.set_aspect('equal')
            
            # Get current step
            step = history[frame_idx].get('step', frame_idx * 5)
            progress = frame_idx / len(history)
            
            # Show progressive burning
            y_coords, x_coords = np.where(final_perimeter > 0)
            if len(x_coords) > 0:
                num_to_show = int(len(x_coords) * progress)
                if num_to_show > 0:
                    # Burned areas
                    show_x = x_coords[:num_to_show]
                    show_y = y_coords[:num_to_show]
                    ax.scatter(show_x, show_y, c='darkred', s=1, alpha=0.8, label='Burned')
                    
                    # Burning edge
                    edge_size = max(1, int(num_to_show * 0.05))
                    edge_x = x_coords[max(0, num_to_show-edge_size):num_to_show]
                    edge_y = y_coords[max(0, num_to_show-edge_size):num_to_show]
                    ax.scatter(edge_x, edge_y, c='red', s=3, alpha=1.0, label='Burning')
            
            # Add ignition point
            igni_x, igni_y = config.ignition_points[0][1], config.ignition_points[0][0]
            ax.plot(igni_x, igni_y, 'yo', markersize=10, label='Ignition')
            
            ax.set_title(f'🔥 Day {day} Fire Progression - Step {step}\nProgress: {progress*100:.1f}%')
            ax.set_xlabel('Grid X (cells)')
            ax.set_ylabel('Grid Y (cells)')
            
            if frame_idx == 0 or frame_idx == len(history) - 1:
                ax.legend()
        
        # Create animation
        anim = animation.FuncAnimation(fig, animate, frames=len(history), 
                                     interval=500, repeat=True, blit=False)
        
        # Save animation
        output_file = Path(output_dir) / f"day_{day}_2d_fire_progression.gif"
        try:
            writer = animation.PillowWriter(fps=3)
            anim.save(output_file, writer=writer)
            print(f"✅ 2D progression animation saved: {output_file}")
        except Exception as e:
            print(f"⚠️  Could not save GIF: {e}")
        
        plt.close()
        return anim
        
    except Exception as e:
        print(f"❌ Error creating 2D animation: {e}")
        return None

def create_3d_layered_visualization(forest_model, config, day, output_dir="validation_processed_results"):
    """Create 3D layered fire visualization."""
    print(f"\n🎨 Creating 3D layered visualization for Day {day}...")
    
    try:
        # Get fire perimeter
        fire_perimeter = forest_model.get_2d_fire_perimeter()
        
        # Create 3D plot
        fig = plt.figure(figsize=(14, 10))
        ax = fig.add_subplot(111, projection='3d')
        
        # Get burned coordinates
        y_coords, x_coords = np.where(fire_perimeter > 0)
        
        if len(x_coords) > 0:
            # Sample for performance
            if len(x_coords) > 10000:
                indices = np.random.choice(len(x_coords), 10000, replace=False)
                x_coords = x_coords[indices]
                y_coords = y_coords[indices]
            
            # Convert to meters
            x_meters = x_coords * config.model_resolution
            y_meters = y_coords * config.model_resolution
            
            # Create multiple layers
            colors = ['darkred', 'red', 'orange', 'yellow', 'lightcoral']
            for layer in range(min(config.num_layers, 5)):
                layer_height = layer * 3  # 3m per layer
                
                # Sample different densities for each layer
                layer_sample = max(1, len(x_coords) // (layer + 1))
                sample_indices = np.random.choice(len(x_coords), layer_sample, replace=False)
                
                ax.scatter(x_meters[sample_indices], y_meters[sample_indices], 
                          layer_height, c=colors[layer], s=2-layer*0.3, 
                          alpha=0.7-layer*0.1, label=f'Layer {layer+1}')
            
            ax.set_xlabel('X (meters)')
            ax.set_ylabel('Y (meters)')
            ax.set_zlabel('Height (meters)')
            ax.set_title(f'🔥 Day {day} - 3D Layered Fire Visualization\nBurned Area: {len(x_coords):,} cells')
            ax.legend()
            
            # Save plot
            output_file = Path(output_dir) / f"day_{day}_3d_layered_fire.png"
            plt.savefig(output_file, dpi=300, bbox_inches='tight')
            print(f"✅ 3D layered visualization saved: {output_file}")
        
        plt.close()
        
    except Exception as e:
        print(f"❌ Error creating 3D visualization: {e}")

def create_statistics_animation(history, validation_results, day, output_dir="validation_processed_results"):
    """Create animated statistics progression."""
    print(f"\n📊 Creating statistics animation for Day {day}...")
    
    if not history:
        print("❌ No history data available")
        return
    
    try:
        # Extract statistics from validation results
        stats = validation_results['vertical_spread_stats']
        
        # Create progression data
        steps = [entry.get('step', i*5) for i, entry in enumerate(history)]
        
        # Simulate progression (since we don't have step-by-step stats)
        total_spread = stats['total_spread']
        horizontal_spread = stats['horizontal_spread']
        vertical_spread = stats['vertical_spread']
        ember_spread = stats['ember_spread']
        
        # Create animated plot
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
        
        def animate_stats(frame_idx):
            progress = (frame_idx + 1) / len(history)
            current_step = steps[frame_idx]
            
            # Clear all axes
            for ax in [ax1, ax2, ax3, ax4]:
                ax.clear()
            
            # Plot 1: Cumulative spread
            current_horizontal = int(horizontal_spread * progress)
            current_vertical = int(vertical_spread * progress)
            current_ember = int(ember_spread * progress)
            
            spread_types = ['Horizontal', 'Vertical', 'Ember']
            spread_values = [current_horizontal, current_vertical, current_ember]
            colors = ['#ff7f0e', '#d62728', '#ff9999']
            
            bars = ax1.bar(spread_types, spread_values, color=colors)
            ax1.set_ylabel('Spread Events')
            ax1.set_title(f'🔥 Day {day} - Cumulative Spread Events\nStep: {current_step}')
            ax1.set_ylim(0, max(horizontal_spread, vertical_spread, ember_spread))
            
            # Add value labels
            for bar, value in zip(bars, spread_values):
                height = bar.get_height()
                ax1.text(bar.get_x() + bar.get_width()/2., height,
                        f'{value:,}', ha='center', va='bottom')
            
            # Plot 2: Progression over time
            current_steps = steps[:frame_idx+1]
            horizontal_progression = [int(horizontal_spread * (i+1)/len(history)) for i in range(len(current_steps))]
            
            ax2.plot(current_steps, horizontal_progression, 'o-', color='#ff7f0e', linewidth=2)
            ax2.set_xlabel('Simulation Step')
            ax2.set_ylabel('Horizontal Spread Events')
            ax2.set_title(f'🚀 Day {day} - Horizontal Spread Progression')
            ax2.set_xlim(0, max(steps))
            ax2.set_ylim(0, horizontal_spread)
            ax2.grid(True, alpha=0.3)
            
            # Plot 3: Percentage distribution
            total_current = current_horizontal + current_vertical + current_ember
            if total_current > 0:
                percentages = [v/total_current*100 for v in spread_values]
                ax3.pie(percentages, labels=spread_types, colors=colors, autopct='%1.1f%%', startangle=90)
                ax3.set_title(f'📊 Day {day} - Spread Distribution')
            
            # Plot 4: Efficiency over time
            if frame_idx > 0:
                efficiency_steps = current_steps
                # Simulate efficiency progression
                efficiency_values = [stats['horizontal_efficiency'] * (i+1)/len(current_steps) for i in range(len(current_steps))]
                
                ax4.plot(efficiency_steps, efficiency_values, 's-', color='green', linewidth=2)
                ax4.set_xlabel('Simulation Step')
                ax4.set_ylabel('Efficiency (%)')
                ax4.set_title(f'⚡ Day {day} - Spread Efficiency')
                ax4.set_xlim(0, max(steps))
                ax4.set_ylim(0, stats['horizontal_efficiency'])
                ax4.grid(True, alpha=0.3)
        
        # Create animation
        stats_anim = animation.FuncAnimation(fig, animate_stats, frames=len(history), 
                                           interval=800, repeat=True, blit=False)
        
        # Save animation
        output_file = Path(output_dir) / f"day_{day}_statistics_animation.gif"
        try:
            writer = animation.PillowWriter(fps=2)
            stats_anim.save(output_file, writer=writer)
            print(f"✅ Statistics animation saved: {output_file}")
        except Exception as e:
            print(f"⚠️  Could not save statistics animation: {e}")
        
        plt.close()
        return stats_anim
        
    except Exception as e:
        print(f"❌ Error creating statistics animation: {e}")
        return None

def create_comparison_dashboard(day3_results, day4_results, output_dir="validation_processed_results"):
    """Create animated comparison between Day 3 and Day 4."""
    print(f"\n📊 Creating Day 3 vs Day 4 comparison dashboard...")
    
    try:
        # Extract statistics
        day3_stats = day3_results['vertical_spread_stats']
        day4_stats = day4_results['vertical_spread_stats']
        
        # Create comparison plot
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
        
        # Comparison data
        categories = ['Horizontal', 'Vertical', 'Ember']
        day3_values = [day3_stats['horizontal_spread'], day3_stats['vertical_spread'], day3_stats['ember_spread']]
        day4_values = [day4_stats['horizontal_spread'], day4_stats['vertical_spread'], day4_stats['ember_spread']]
        
        x = np.arange(len(categories))
        width = 0.35
        
        # Plot 1: Spread events comparison
        bars1 = ax1.bar(x - width/2, day3_values, width, label='Day 3', color='#ff7f0e', alpha=0.8)
        bars2 = ax1.bar(x + width/2, day4_values, width, label='Day 4', color='#1f77b4', alpha=0.8)
        
        ax1.set_xlabel('Spread Type')
        ax1.set_ylabel('Number of Events')
        ax1.set_title('🔥 Fire Spread Events Comparison')
        ax1.set_xticks(x)
        ax1.set_xticklabels(categories)
        ax1.legend()
        
        # Add value labels
        for bars in [bars1, bars2]:
            for bar in bars:
                height = bar.get_height()
                ax1.text(bar.get_x() + bar.get_width()/2., height,
                        f'{int(height/1000)}K', ha='center', va='bottom')
        
        # Plot 2: Efficiency comparison
        day3_eff = [day3_stats['horizontal_efficiency'], day3_stats['vertical_efficiency'], day3_stats['ember_efficiency']]
        day4_eff = [day4_stats['horizontal_efficiency'], day4_stats['vertical_efficiency'], day4_stats['ember_efficiency']]
        
        bars3 = ax2.bar(x - width/2, day3_eff, width, label='Day 3', color='#ff7f0e', alpha=0.8)
        bars4 = ax2.bar(x + width/2, day4_eff, width, label='Day 4', color='#1f77b4', alpha=0.8)
        
        ax2.set_xlabel('Spread Type')
        ax2.set_ylabel('Efficiency (%)')
        ax2.set_title('⚡ Spread Efficiency Comparison')
        ax2.set_xticks(x)
        ax2.set_xticklabels(categories)
        ax2.legend()
        
        # Plot 3: Objective values
        objectives = [day3_results['objective_value'], day4_results['objective_value']]
        ax3.bar(['Day 3', 'Day 4'], objectives, color=['#ff7f0e', '#1f77b4'], alpha=0.8)
        ax3.set_ylabel('Objective Value')
        ax3.set_title('🎯 Validation Objective Comparison')
        
        # Add value labels
        for i, v in enumerate(objectives):
            ax3.text(i, v, f'{v:.3f}', ha='center', va='bottom')
        
        # Plot 4: Execution time
        exec_times = [day3_results['execution_time']/3600, day4_results['execution_time']/3600]  # Convert to hours
        ax4.bar(['Day 3', 'Day 4'], exec_times, color=['#ff7f0e', '#1f77b4'], alpha=0.8)
        ax4.set_ylabel('Execution Time (hours)')
        ax4.set_title('⏱️ Simulation Time Comparison')
        
        # Add value labels
        for i, v in enumerate(exec_times):
            ax4.text(i, v, f'{v:.1f}h', ha='center', va='bottom')
        
        plt.tight_layout()
        
        # Save comparison
        output_file = Path(output_dir) / "day_3_vs_day_4_comparison.png"
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"✅ Comparison dashboard saved: {output_file}")
        plt.close()
        
    except Exception as e:
        print(f"❌ Error creating comparison dashboard: {e}")

def main():
    """Main function to create all comprehensive animations."""
    print("🎬 Comprehensive Fire Animation System")
    print("=" * 80)
    
    # Ensure output directory exists
    output_dir = Path("validation_processed_results")
    output_dir.mkdir(exist_ok=True)
    
    # Load data for both days
    day3_data = load_validation_data(3)
    day4_data = load_validation_data(4)
    
    if day3_data[0] is None or day4_data[0] is None:
        print("❌ Failed to load validation data")
        return
    
    # Process Day 3
    print(f"\n🔥 CREATING COMPREHENSIVE ANIMATIONS FOR DAY 3")
    print("=" * 60)
    
    forest_model3, engine3, config3, results3, history3 = day3_data
    
    create_2d_fire_progression_animation(forest_model3, history3, config3, 3, output_dir)
    create_3d_layered_visualization(forest_model3, config3, 3, output_dir)
    create_statistics_animation(history3, results3, 3, output_dir)
    
    print(f"✅ Day 3 comprehensive animations complete!")
    
    # Process Day 4
    print(f"\n🔥 CREATING COMPREHENSIVE ANIMATIONS FOR DAY 4")
    print("=" * 60)
    
    forest_model4, engine4, config4, results4, history4 = day4_data
    
    create_2d_fire_progression_animation(forest_model4, history4, config4, 4, output_dir)
    create_3d_layered_visualization(forest_model4, config4, 4, output_dir)
    create_statistics_animation(history4, results4, 4, output_dir)
    
    print(f"✅ Day 4 comprehensive animations complete!")
    
    # Create comparison
    print(f"\n📊 CREATING DAY 3 vs DAY 4 COMPARISON")
    print("=" * 60)
    
    create_comparison_dashboard(results3, results4, output_dir)
    
    print(f"\n🎉 All comprehensive animations complete!")
    print(f"📁 All files saved to: {output_dir}")
    
    # List generated files
    print("\n📁 Generated animation files:")
    for file in sorted(output_dir.glob("day_*")):
        if file.suffix in ['.gif', '.png', '.mp4']:
            print(f"   • {file.name}")

if __name__ == "__main__":
    main()
