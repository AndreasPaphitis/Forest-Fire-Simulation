"""
Create Figure 19: Validation Simulation vs EMSR Delineations Comparison
Shows the burned area from validation simulation overlaid with EMSR Day 4 delineations.
"""
import numpy as np
import matplotlib.pyplot as plt
import geopandas as gpd
import pickle
import gzip
from pathlib import Path
from rasterio.transform import from_bounds
import matplotlib.patches as patches

# Configure matplotlib for academic figures
plt.style.use('default')
plt.rcParams.update({
    'font.family': 'Times New Roman',
    'font.size': 12,
    'axes.labelsize': 12,
    'axes.titlesize': 14,
    'xtick.labelsize': 10,
    'ytick.labelsize': 10,
    'legend.fontsize': 10,
    'figure.titlesize': 16,
    'lines.linewidth': 1.5,
    'axes.linewidth': 1.2
})

def load_simulation_state(state_file_path):
    """Load simulation state from pkl.gz file"""
    print(f"📂 Loading simulation state: {state_file_path}")
    try:
        with gzip.open(state_file_path, 'rb') as f:
            state_data = pickle.load(f)
        print(f"✅ Loaded simulation state successfully")
        return state_data
    except Exception as e:
        print(f"❌ Error loading simulation state: {e}")
        return None

def extract_burned_area_from_state(state_data):
    """Extract burned area from simulation state"""
    try:
        # Check if fire_perimeter_2d is directly available
        if 'fire_perimeter_2d' in state_data:
            burned_area_2d = state_data['fire_perimeter_2d']
            print(f"✅ Found fire_perimeter_2d directly: {burned_area_2d.shape}")
            print(f"   Total burned cells: {np.sum(burned_area_2d > 0):,}")
            return burned_area_2d
        
        # Try other possible keys
        possible_keys = ['fire_perimeter_2d', 'burned_area_2d', 'fire_mask', 'perimeter']
        for key in possible_keys:
            if key in state_data:
                burned_area_2d = state_data[key]
                print(f"✅ Found burned area data in '{key}': {burned_area_2d.shape}")
                print(f"   Total burned cells: {np.sum(burned_area_2d > 0):,}")
                return burned_area_2d
        
        # Try to find forest model
        forest_model = None
        if 'forest_model' in state_data:
            forest_model = state_data['forest_model']
        elif 'model' in state_data:
            forest_model = state_data['model']
        
        if forest_model is not None and hasattr(forest_model, 'get_2d_fire_perimeter'):
            burned_area_2d = forest_model.get_2d_fire_perimeter()
            print(f"✅ Extracted 2D fire perimeter from model: {burned_area_2d.shape}")
            print(f"   Total burned cells: {np.sum(burned_area_2d > 0):,}")
            return burned_area_2d
        
        print("❌ Could not find burned area data")
        print(f"   Available keys: {list(state_data.keys()) if isinstance(state_data, dict) else 'Not a dict'}")
        return None
            
    except Exception as e:
        print(f"❌ Error extracting burned area: {e}")
        return None

def load_emsr_data():
    """Load EMSR Day 4 delineations"""
    emsr_path = Path("EMSR Delineations/Day 4 (26_08_23)/EMSR685_AOI01_GRA_PRODUCT_observedEventA_v1.shp")
    
    if not emsr_path.exists():
        print(f"❌ EMSR file not found: {emsr_path}")
        return None
    
    try:
        print(f"📂 Loading EMSR data: {emsr_path}")
        emsr_gdf = gpd.read_file(str(emsr_path))
        print(f"✅ Loaded EMSR data: {len(emsr_gdf)} features")
        
        # Transform to UTM Zone 28N for Tenerife
        emsr_gdf_utm = emsr_gdf.to_crs(epsg=32628)
        print(f"✅ Transformed to UTM Zone 28N")
        
        return emsr_gdf_utm
        
    except Exception as e:
        print(f"❌ Error loading EMSR data: {e}")
        return None

def create_figure19_comparison(burned_area_2d, emsr_gdf_utm, step_number, output_dir=None):
    """Create Figure 19 comparison plot"""
    
    print(f"\n🎨 Creating Figure 19 comparison for Step {step_number}")
    
    # Create figure
    fig, ax = plt.subplots(figsize=(14, 10))
    
    # Calculate simulation grid coordinates (609x609 grid, 20m resolution)
    grid_width, grid_height = burned_area_2d.shape
    resolution = 20.0  # 20m per cell
    
    # Get EMSR bounds for reference
    emsr_bounds = emsr_gdf_utm.total_bounds  # [minx, miny, maxx, maxy]
    emsr_center_x = (emsr_bounds[0] + emsr_bounds[2]) / 2
    emsr_center_y = (emsr_bounds[1] + emsr_bounds[3]) / 2
    
    print(f"📍 EMSR center: ({emsr_center_x:.1f}, {emsr_center_y:.1f}) UTM")
    
    # Calculate simulation grid bounds (centered on EMSR fire)
    sim_width_m = grid_width * resolution
    sim_height_m = grid_height * resolution
    
    sim_bounds = [
        emsr_center_x - sim_width_m/2,  # minx
        emsr_center_y - sim_height_m/2, # miny  
        emsr_center_x + sim_width_m/2,  # maxx
        emsr_center_y + sim_height_m/2  # maxy
    ]
    
    print(f"🗺️  Simulation bounds: {sim_bounds}")
    
    # Create coordinate arrays for simulation data
    x_coords = np.linspace(sim_bounds[0], sim_bounds[2], grid_width)
    y_coords = np.linspace(sim_bounds[1], sim_bounds[3], grid_height)
    X, Y = np.meshgrid(x_coords, y_coords)
    
    # Plot EMSR data (observed fire)
    emsr_gdf_utm.plot(ax=ax, color='red', edgecolor='darkred', linewidth=2, alpha=0.8, label='EMSR Day 4 Observed Fire')
    
    # Plot simulation burned area
    burned_mask = burned_area_2d > 0
    if np.any(burned_mask):
        # Create filled contour for simulation
        ax.contourf(X, Y, burned_area_2d, levels=[0.5, 1.5], colors=['blue'], alpha=0.6)
        ax.contour(X, Y, burned_area_2d, levels=[0.5], colors=['darkblue'], linewidths=2)
        
        # Add simulation to legend (use handle for legend only, don't add to axes)
        simulation_patch = patches.Patch(color='blue', alpha=0.6, label=f'Simulated Fire (Step {step_number})')
    else:
        print("⚠️  No burned cells found in simulation")
    
    # Calculate overlap statistics
    if np.any(burned_mask):
        # Rasterize EMSR to same grid for comparison
        from rasterio.features import rasterize
        from rasterio.transform import from_bounds
        
        transform = from_bounds(sim_bounds[0], sim_bounds[1], sim_bounds[2], sim_bounds[3], grid_width, grid_height)
        emsr_raster = rasterize(emsr_gdf_utm.geometry, out_shape=(grid_height, grid_width), transform=transform)
        emsr_mask = emsr_raster > 0
        
        # Calculate overlap metrics
        intersection = np.sum(burned_mask & emsr_mask)
        union = np.sum(burned_mask | emsr_mask)
        sim_area = np.sum(burned_mask)
        emsr_area = np.sum(emsr_mask)
        
        # Calculate spatial metrics
        jaccard = intersection / union if union > 0 else 0
        dice = (2 * intersection) / (sim_area + emsr_area) if (sim_area + emsr_area) > 0 else 0
        spatial_error = 1 - dice  # Same as calibration objective
        
        print(f"\n📊 SPATIAL COMPARISON METRICS:")
        print(f"   Simulated cells: {sim_area:,}")
        print(f"   EMSR cells: {emsr_area:,}")
        print(f"   Intersection: {intersection:,}")
        print(f"   Jaccard Index: {jaccard:.4f}")
        print(f"   Dice Coefficient: {dice:.4f}")
        print(f"   Spatial Error: {spatial_error:.4f}")
        
        # Add metrics to plot
        metrics_text = f"Step {step_number} Metrics:\n"
        metrics_text += f"Dice Coefficient: {dice:.3f}\n"
        metrics_text += f"Spatial Error: {spatial_error:.3f}\n"
        metrics_text += f"Simulated Area: {sim_area:,} cells\n"
        metrics_text += f"EMSR Area: {emsr_area:,} cells"
        
        ax.text(0.02, 0.98, metrics_text, transform=ax.transAxes, 
                verticalalignment='top', bbox=dict(boxstyle='round', facecolor='white', alpha=0.8),
                fontsize=10, fontfamily='monospace')
    
    # Set labels and title
    ax.set_xlabel('Easting (UTM Zone 28N, meters)', fontweight='bold')
    ax.set_ylabel('Northing (UTM Zone 28N, meters)', fontweight='bold')
    ax.set_title(f'Figure 19: Validation Simulation vs EMSR Delineations (Step {step_number})', fontweight='bold', pad=20)
    
    # Add legend
    handles, labels = ax.get_legend_handles_labels()
    if 'simulation_patch' in locals():
        handles.append(simulation_patch)
    ax.legend(handles=handles, loc='upper right', framealpha=0.9)
    
    # Set equal aspect ratio and grid
    ax.set_aspect('equal')
    ax.grid(True, alpha=0.3)
    
    # Tight layout
    plt.tight_layout()
    
    # Save figure
    output_path = Path(output_dir) / f"Figure19_Validation_Step{step_number}_vs_EMSR.png"
    plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
    print(f"💾 Saved: {output_path}")
    
    # Show plot
    plt.show()
    
    return fig, ax

def main():
    """Main function to create Figure 19 comparison"""
    print("🔥 CREATING FIGURE 19: VALIDATION SIMULATION vs EMSR COMPARISON")
    print("=" * 70)
    
    # Load EMSR data
    emsr_gdf_utm = load_emsr_data()
    if emsr_gdf_utm is None:
        return
    
    # Find available simulation state files
    possible_dirs = [
        "validation_rank2_conservative_100steps",
        "validation_rank1_extreme_100steps",
        "validation_rank1_extreme_200steps", 
        "validation_results_optimized"
    ]
    
    validation_dir = None
    for dir_name in possible_dirs:
        dir_path = Path(dir_name)
        if dir_path.exists():
            validation_dir = dir_path
            break
    
    if validation_dir is None:
        print(f"❌ No validation directory found. Tried: {possible_dirs}")
        return
    
    print(f"📂 Using validation directory: {validation_dir}")
    
    # Look for simulation state files
    state_files = list(validation_dir.glob("sim_state_step_*.pkl.gz"))
    state_files.sort()
    
    if not state_files:
        print(f"❌ No simulation state files found in {validation_dir}")
        return
    
    print(f"📂 Found {len(state_files)} simulation state files:")
    for i, state_file in enumerate(state_files):
        print(f"   {i+1}. {state_file.name}")
    
    # Use the latest available step (highest step number)
    latest_step_file = state_files[-1]
    # Extract step number from filename like "sim_state_step_000060_20250910_081015"
    filename_parts = latest_step_file.stem.split('_')
    step_number = int(filename_parts[3])  # The step number is after "step"
    
    print(f"\n🎯 Using latest step: {step_number} ({latest_step_file.name})")
    
    # Load simulation state
    state_data = load_simulation_state(latest_step_file)
    if state_data is None:
        return
    
    # Extract burned area
    burned_area_2d = extract_burned_area_from_state(state_data)
    if burned_area_2d is None:
        return
    
    # Create comparison plot
    fig, ax = create_figure19_comparison(burned_area_2d, emsr_gdf_utm, step_number, str(validation_dir))
    
    print(f"\n✅ Figure 19 comparison completed!")
    
    # Determine parameter set from directory name
    if "rank2" in str(validation_dir).lower() or "conservative" in str(validation_dir).lower():
        print(f"   This shows RANK 2 CONSERVATIVE parameters (spread_prob=0.775) results")
        print(f"   More realistic fire shapes, less overfitting risk")
    elif "rank1" in str(validation_dir).lower() or "extreme" in str(validation_dir).lower():
        print(f"   This shows RANK 1 EXTREME parameters (spread_prob=0.95) results")
        print(f"   Potentially overfitted, check for square fire shapes")
    else:
        print(f"   Compare fire shapes for overfitting analysis")

if __name__ == "__main__":
    main()
