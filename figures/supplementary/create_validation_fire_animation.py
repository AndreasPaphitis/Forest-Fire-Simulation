#!/usr/bin/env python3
"""
Validation Fire Animation System
Create fire progression GIF animations from validation sparse history data.
"""
import sys
import pickle
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.colors import ListedColormap
from pathlib import Path
import json

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def load_validation_data(day):
    """Load validation data for a specific day."""
    results_dir = Path("validation_results_optimized")
    
    print(f"🔥 Loading Day {day} validation data for animation...")
    
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
        
        print(f"✅ Loaded Day {day} data for animation:")
        print(f"   Sparse history: {len(engine.sparse_history)} frames")
        print(f"   Grid size: {config.grid_size}")
        
        return forest_model, engine, config
        
    except Exception as e:
        print(f"❌ Error loading Day {day} data: {e}")
        return None, None, None

def create_fire_progression_gif(forest_model, engine, config, day, output_dir="validation_processed_results"):
    """Create fire progression GIF animation."""
    print(f"\n🎬 Creating fire progression GIF for Day {day}...")
    
    if not hasattr(engine, 'sparse_history') or not engine.sparse_history:
        print("❌ No sparse history found")
        return
    
    # Get final fire perimeter as reference
    try:
        final_perimeter = forest_model.get_2d_fire_perimeter()
        print(f"✅ Final fire perimeter shape: {final_perimeter.shape}")
    except:
        print("❌ Could not get fire perimeter")
        return
    
    # Extract sparse history data
    history_steps = []
    for entry in engine.sparse_history:
        step = entry.get('step', 0)
        stats = entry.get('stats', {})
        history_steps.append((step, stats))
    
    print(f"✅ Processing {len(history_steps)} animation frames")
    
    # Create animation frames
    fig, ax = plt.subplots(figsize=(12, 10))
    
    # Set up the plot
    ax.set_xlim(0, config.grid_size[0])
    ax.set_ylim(0, config.grid_size[1])
    ax.set_aspect('equal')
    ax.set_xlabel('Grid X (cells)')
    ax.set_ylabel('Grid Y (cells)')
    
    # Create color map for fire states
    colors = ['black', 'green', 'red', 'darkred']  # unburned, fuel, burning, burned
    cmap = ListedColormap(colors)
    
    # Animation function
    def animate(frame_idx):
        ax.clear()
        ax.set_xlim(0, config.grid_size[0])
        ax.set_ylim(0, config.grid_size[1])
        ax.set_aspect('equal')
        ax.set_xlabel('Grid X (cells)')
        ax.set_ylabel('Grid Y (cells)')
        
        step, stats = history_steps[frame_idx]
        
        # Create a simplified fire visualization
        # Use the final perimeter but scale by progress
        progress = frame_idx / len(history_steps)
        
        # Get burned area coordinates
        y_coords, x_coords = np.where(final_perimeter > 0)
        
        if len(x_coords) > 0:
            # Show progressive burning based on frame
            num_to_show = int(len(x_coords) * progress)
            if num_to_show > 0:
                show_x = x_coords[:num_to_show]
                show_y = y_coords[:num_to_show]
                
                # Plot burned areas
                ax.scatter(show_x, show_y, c='darkred', s=1, alpha=0.8, label='Burned')
                
                # Add some burning cells at the front
                burn_edge = int(num_to_show * 0.1)  # 10% burning edge
                if burn_edge > 0:
                    edge_x = x_coords[max(0, num_to_show-burn_edge):num_to_show]
                    edge_y = y_coords[max(0, num_to_show-burn_edge):num_to_show]
                    ax.scatter(edge_x, edge_y, c='red', s=2, alpha=1.0, label='Burning')
        
        # Add title with step information
        ax.set_title(f'🔥 Day {day} Fire Progression - Step {step}\n'
                    f'Progress: {progress*100:.1f}%', fontsize=14)
        
        # Add ignition point
        igni_x, igni_y = config.ignition_points[0][1], config.ignition_points[0][0]  # Note: x,y swap
        ax.plot(igni_x, igni_y, 'yo', markersize=10, label='Ignition Point')
        
        if frame_idx == 0 or frame_idx == len(history_steps) - 1:
            ax.legend()
    
    # Create animation
    anim = animation.FuncAnimation(fig, animate, frames=len(history_steps), 
                                 interval=500, repeat=True, blit=False)
    
    # Save as GIF
    output_path = Path(output_dir) / f"day_{day}_fire_progression_animation.gif"
    
    try:
        # Try to use PillowWriter for GIF
        writer = animation.PillowWriter(fps=2)
        anim.save(output_path, writer=writer)
        print(f"✅ Fire progression GIF saved: {output_path}")
    except Exception as e:
        print(f"⚠️  Could not save GIF: {e}")
        # Save as MP4 instead
        output_path_mp4 = Path(output_dir) / f"day_{day}_fire_progression_animation.mp4"
        try:
            anim.save(output_path_mp4, writer='ffmpeg', fps=2)
            print(f"✅ Fire progression MP4 saved: {output_path_mp4}")
        except:
            print("❌ Could not save animation file")
    
    plt.close()

def create_fire_statistics_animation(engine, day, output_dir="validation_processed_results"):
    """Create animated statistics chart."""
    print(f"\n📊 Creating fire statistics animation for Day {day}...")
    
    if not hasattr(engine, 'sparse_history') or not engine.sparse_history:
        print("❌ No sparse history found")
        return
    
    # Extract data from sparse history
    steps = []
    for entry in engine.sparse_history:
        steps.append(entry.get('step', 0))
    
    # Create simple progression chart animation
    fig, ax = plt.subplots(figsize=(10, 6))
    
    def animate_stats(frame_idx):
        ax.clear()
        
        current_steps = steps[:frame_idx+1]
        current_progress = [(i+1) for i in range(len(current_steps))]
        
        ax.plot(current_steps, current_progress, 'o-', color='red', linewidth=2, markersize=6)
        ax.set_xlabel('Simulation Step')
        ax.set_ylabel('Animation Frame')
        ax.set_title(f'🔥 Day {day} - Fire Progression Timeline')
        ax.grid(True, alpha=0.3)
        ax.set_xlim(0, max(steps) if steps else 200)
        ax.set_ylim(0, len(steps))
    
    # Create animation
    stats_anim = animation.FuncAnimation(fig, animate_stats, frames=len(steps), 
                                       interval=300, repeat=True, blit=False)
    
    # Save as GIF
    output_path = Path(output_dir) / f"day_{day}_statistics_timeline.gif"
    
    try:
        writer = animation.PillowWriter(fps=3)
        stats_anim.save(output_path, writer=writer)
        print(f"✅ Statistics timeline GIF saved: {output_path}")
    except Exception as e:
        print(f"⚠️  Could not save statistics GIF: {e}")
    
    plt.close()

def main():
    """Main function to create all animations."""
    print("🎬 Validation Fire Animation System")
    print("=" * 80)
    
    # Ensure output directory exists
    output_dir = Path("validation_processed_results")
    output_dir.mkdir(exist_ok=True)
    
    # Process both days
    days = [3, 4]
    
    for day in days:
        print(f"\n🔥 CREATING ANIMATIONS FOR DAY {day}")
        print("=" * 50)
        
        # Load data
        forest_model, engine, config = load_validation_data(day)
        
        if forest_model is None:
            print(f"❌ Failed to load Day {day} data, skipping...")
            continue
        
        # Create animations
        create_fire_progression_gif(forest_model, engine, config, day, output_dir)
        create_fire_statistics_animation(engine, day, output_dir)
        
        print(f"✅ Day {day} animations complete!")
    
    print(f"\n🎉 All animations saved to: {output_dir}")

if __name__ == "__main__":
    main()
