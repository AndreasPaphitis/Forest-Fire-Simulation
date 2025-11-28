#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Figure 19: CORRECTED Spatial Fire Spread Validation Maps
Creates spatial comparison maps using the CORRECT EMSR data for each day.
Day 3 validation uses Day 3 EMSR, Day 4 validation uses Day 4 EMSR.
"""

import json
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from pathlib import Path
import geopandas as gpd
import pickle
import gzip
import sys

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Set professional style
plt.style.use('default')
plt.rcParams.update({
    'font.size': 11,
    'font.family': 'serif',
    'font.serif': ['Times New Roman'],
    'axes.linewidth': 1.2,
    'axes.spines.top': False,
    'axes.spines.right': False,
    'figure.dpi': 300,
    'savefig.dpi': 300,
    'savefig.bbox': 'tight',
    'savefig.facecolor': 'white',
    'savefig.edgecolor': 'none',
})

def load_validation_results():
    """Load validation results from FINAL VALIDATION RESULTS directory."""
    try:
        day3_file = Path("FINAL VALIDATION RESULTS/day_3_validation_result.json")
        day4_file = Path("FINAL VALIDATION RESULTS/day_4_validation_result.json")
        
        with open(day3_file, 'r') as f:
            day3_data = json.load(f)
        with open(day4_file, 'r') as f:
            day4_data = json.load(f)
            
        print("✅ Loaded validation results from FINAL VALIDATION RESULTS")
        return {3: day3_data, 4: day4_data}
    except Exception as e:
        print(f"❌ Error loading validation results: {e}")
        return None

def load_simulation_state_for_day(day):
    """Load simulation state data for a specific validation day from FINAL VALIDATION RESULTS."""
    try:
        # Load the step 100 simulation state for the specific day from FINAL VALIDATION RESULTS
        validation_dir = Path("FINAL VALIDATION RESULTS")
        
        # Look for step 100 simulation files in subdirectories (they're in nested folders)
        step100_files = list(validation_dir.glob("**/sim_state_step_000100_*.pkl"))
        
        # Filter out directories and only keep actual files
        step100_files = [f for f in step100_files if f.is_file()]
        
        if not step100_files:
            print(f"❌ No step 100 simulation files found in {validation_dir}")
            return None
        
        # Map days to specific simulation files
        # Since we have two step 100 files, we'll assign them based on timestamps
        sorted_files = sorted(step100_files)
        
        print(f"   🗂️  Found {len(sorted_files)} step 100 files:")
        for i, f in enumerate(sorted_files):
            print(f"      [{i}] {f}")
        
        if day == 3 and len(sorted_files) >= 1:
            final_sim_file = sorted_files[0]  # First step 100 file for Day 3  
        elif day == 4 and len(sorted_files) >= 2:
            final_sim_file = sorted_files[1]  # Second step 100 file for Day 4
        elif len(sorted_files) >= 1:
            final_sim_file = sorted_files[-1]  # Fallback to latest file
        else:
            print(f"❌ No appropriate step 100 file found for Day {day}")
            return None
        
        print(f"   📂 Loading from: {final_sim_file}")
        
        # Load the simulation state
        if final_sim_file.suffix == '.gz':
            with gzip.open(final_sim_file, 'rb') as f:
                state = pickle.load(f)
        else:
            with open(final_sim_file, 'rb') as f:
                state = pickle.load(f)
        
        print(f"✅ Loaded step 100 simulation state for Day {day}: {final_sim_file.name}")
        
        # Extract burned area from fire_perimeter_2d
        if 'fire_perimeter_2d' in state:
            burned_2d = (state['fire_perimeter_2d'] > 0).astype(int)
            print(f"   📊 Extracted burned area: {np.sum(burned_2d)} cells, shape: {burned_2d.shape}")
            return burned_2d
        else:
            print(f"   ❌ No fire_perimeter_2d found in state")
            return None
            
    except Exception as e:
        print(f"❌ Error loading simulation data for Day {day}: {e}")
        return None

def load_emsr_data(day):
    """Load the CORRECT EMSR data for a specific validation day."""
    try:
        emsr_dir = Path("EMSR Delineations")
        
        # CORRECTED: Use the right EMSR data for each day
        day_mapping = {
            3: "Day 3 (24_08_23)",  # Day 3 validation uses Day 3 EMSR background
            4: "Day 4 (26_08_23)"   # Day 4 validation uses Day 4 EMSR background
        }
        
        day_dir = emsr_dir / day_mapping[day]
        print(f"📂 Loading EMSR data for Day {day} from: {day_dir}")
        
        if day_dir.exists():
            shp_files = list(day_dir.glob("*.shp"))
            if shp_files:
                gdf = gpd.read_file(shp_files[0])
                # Ensure we have UTM projection
                if gdf.crs.to_string() != 'EPSG:32628':
                    print(f"   Converting {day_mapping[day]} from {gdf.crs} to UTM 28N...")
                    gdf = gdf.to_crs('EPSG:32628')
                print(f"✅ Loaded CORRECT EMSR data for Day {day}: {len(gdf)} features")
                return gdf
        
        print(f"❌ No EMSR data found for Day {day} at {day_dir}")
        return None
    except Exception as e:
        print(f"❌ Error loading EMSR data for Day {day}: {e}")
        return None

def create_figure19_corrected():
    """Create Figure 19 using CORRECT validation data for each day."""
    
    print("🎨 Creating Figure 19: CORRECTED Spatial Fire Spread Validation Maps")
    print("📍 Using Day 3 EMSR for Day 3 validation, Day 4 EMSR for Day 4 validation")
    
    # Load validation results
    validation_results = load_validation_results()
    if not validation_results:
        print("❌ Cannot proceed without validation results")
        return
    
    # Create figure with two subplots
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(20, 9))
    
    # Color scheme
    emsr_color = '#d62728'       # Strong red for observed EMSR
    sim_color = '#2ca02c'        # Strong green for simulation
    background_color = '#f8f8f8'
    
    days = [3, 4]
    axes = [ax1, ax2]
    day_labels = ['(a) Day 3 Validation Against Day 3 EMSR', '(b) Day 4 Validation Against Day 4 EMSR']
    
    for day, ax, label in zip(days, axes, day_labels):
        print(f"\n📊 Processing Day {day} Validation...")
        
        # Load CORRECT EMSR data for this specific day
        emsr_gdf = load_emsr_data(day)
        
        # Load simulation data for this day
        sim_burned = load_simulation_state_for_day(day)
        
        if emsr_gdf is not None and sim_burned is not None:
            # Get bounds from EMSR data
            emsr_bounds = emsr_gdf.total_bounds  # [minx, miny, maxx, maxy]
            print(f"   📍 EMSR bounds: {emsr_bounds}")
            
            # Calculate simulation grid coordinates
            grid_height, grid_width = sim_burned.shape
            resolution = 20.0  # 20m per cell
            
            # Center simulation grid on EMSR fire
            emsr_center_x = (emsr_bounds[0] + emsr_bounds[2]) / 2
            emsr_center_y = (emsr_bounds[1] + emsr_bounds[3]) / 2
            
            sim_width_m = grid_width * resolution
            sim_height_m = grid_height * resolution
            
            sim_bounds = [
                emsr_center_x - sim_width_m/2,  # minx
                emsr_center_y - sim_height_m/2, # miny  
                emsr_center_x + sim_width_m/2,  # maxx
                emsr_center_y + sim_height_m/2  # maxy
            ]
            
            print(f"   🗺️  Simulation bounds: {sim_bounds}")
            
            # Create coordinate arrays for simulation
            x_coords = np.linspace(sim_bounds[0], sim_bounds[2], grid_width)
            y_coords = np.linspace(sim_bounds[1], sim_bounds[3], grid_height)
            X, Y = np.meshgrid(x_coords, y_coords)
            
            # Set background
            ax.set_facecolor(background_color)
            
            # Plot simulation burned area first (so EMSR overlays on top)
            burned_mask = sim_burned > 0
            if np.any(burned_mask):
                # Create filled contour for simulation
                cs = ax.contourf(X, Y, sim_burned, levels=[0.5, 1.5], colors=[sim_color], alpha=0.7)
                ax.contour(X, Y, sim_burned, levels=[0.5], colors=['darkgreen'], linewidths=2.5)
                
                print(f"   🔥 Simulated burned cells: {np.sum(burned_mask):,}")
            
            # Plot EMSR data (observed fire) on top
            emsr_gdf.plot(ax=ax, color=emsr_color, alpha=0.8, edgecolor='darkred', 
                         linewidth=2, label=f'EMSR Day {day} Observed Fire')
            
            # Calculate overlap metrics
            if np.any(burned_mask):
                from rasterio.features import rasterize
                from rasterio.transform import from_bounds
                
                transform = from_bounds(sim_bounds[0], sim_bounds[1], sim_bounds[2], sim_bounds[3], 
                                      grid_width, grid_height)
                emsr_raster = rasterize(emsr_gdf.geometry, out_shape=(grid_height, grid_width), 
                                      transform=transform)
                emsr_mask = emsr_raster > 0
                
                # Calculate spatial metrics
                intersection = np.sum(burned_mask & emsr_mask)
                sim_area = np.sum(burned_mask)
                emsr_area = np.sum(emsr_mask)
                
                dice = (2 * intersection) / (sim_area + emsr_area) if (sim_area + emsr_area) > 0 else 0
                jaccard = intersection / np.sum(burned_mask | emsr_mask) if np.sum(burned_mask | emsr_mask) > 0 else 0
                spatial_error = 1 - dice
                
                # Calculate area ratio and over-prediction penalty
                area_ratio = sim_area / emsr_area if emsr_area > 0 else float('inf')
                overpred_penalty = 2.0 * (area_ratio - 2.0)**2 if area_ratio > 2.0 else 0
                total_objective = spatial_error + overpred_penalty
                
                print(f"   📊 EMSR cells: {emsr_area:,}")
                print(f"   📊 Intersection: {intersection:,}")
                print(f"   📊 Dice: {dice:.3f}, Spatial Error: {spatial_error:.3f}")
                print(f"   📊 Area Ratio: {area_ratio:.2f}, Total Objective: {total_objective:.3f}")
                
                # Get actual validation objective from results
                actual_objective = validation_results[day]['objective_value']
                
                # Create metrics text box
                metrics_text = f"Day {day} Validation Results\n"
                metrics_text += f"{'='*28}\n"
                metrics_text += f"Actual Validation Obj: {actual_objective:.3f}\n"
                metrics_text += f"Calculated Objective: {total_objective:.3f}\n"
                metrics_text += f"Spatial Error: {spatial_error:.3f}\n"
                metrics_text += f"Dice Coefficient: {dice:.3f}\n"
                metrics_text += f"Jaccard Index: {jaccard:.3f}\n"
                metrics_text += f"Area Ratio: {area_ratio:.2f}\n"
                if overpred_penalty > 0:
                    metrics_text += f"Over-pred Penalty: {overpred_penalty:.3f}\n"
                metrics_text += f"\nArea Comparison:\n"
                metrics_text += f"Simulated: {sim_area * 0.04:.1f} ha\n"
                metrics_text += f"EMSR Day {day}: {emsr_area * 0.04:.1f} ha\n"
                metrics_text += f"Overlap: {intersection * 0.04:.1f} ha\n"
                metrics_text += f"\nExecution Time: {validation_results[day]['execution_time']/3600:.1f}h"
                
                ax.text(0.02, 0.98, metrics_text, transform=ax.transAxes, 
                       verticalalignment='top', horizontalalignment='left',
                       bbox=dict(boxstyle="round,pad=0.5", facecolor="white", alpha=0.95, 
                               edgecolor='black', linewidth=1),
                       fontsize=9, fontfamily='monospace')
            
            # Set equal aspect ratio and adjust bounds
            ax.set_aspect('equal')
            
            # Zoom to focus on fire area with margin
            margin = 1500  # 1.5km margin
            ax.set_xlim(emsr_bounds[0] - margin, emsr_bounds[2] + margin)
            ax.set_ylim(emsr_bounds[1] - margin, emsr_bounds[3] + margin)
            
        else:
            # Fallback if data loading failed
            ax.text(0.5, 0.5, f'Day {day}\nValidation Data Not Available', ha='center', va='center',
                   transform=ax.transAxes, fontsize=16, 
                   bbox=dict(boxstyle="round,pad=0.5", facecolor="lightgray", alpha=0.7))
        
        # NO SUBPLOT TITLES - Academic standard: titles only in thesis captions
        # Subplot labels removed for cleaner academic presentation
        
        ax.set_xlabel('UTM Easting (m)', fontweight='bold', fontsize=13)
        ax.set_ylabel('UTM Northing (m)', fontweight='bold', fontsize=13)
        ax.grid(True, alpha=0.4, linestyle='--', linewidth=0.8)
        ax.tick_params(axis='both', which='major', labelsize=11)
        
        # Format tick labels with proper thousands separators
        ax.ticklabel_format(style='plain', axis='both')
    
    # Add legend
    legend_elements = [
        patches.Patch(color=emsr_color, alpha=0.8, label='EMSR Observed Fire (Correct Day)'),
        patches.Patch(color=sim_color, alpha=0.7, label='Simulated Fire Spread (Step 100)'),
    ]
    
    fig.legend(handles=legend_elements, loc='upper center', bbox_to_anchor=(0.5, 0.96),
              ncol=2, fontsize=13, frameon=True, fancybox=True, shadow=True)
    
    # NO MAIN TITLE - Academic standard: titles only in captions
    # fig.suptitle removed - titles should be in thesis figure captions only
    
    plt.tight_layout()
    plt.subplots_adjust(top=0.88, bottom=0.12)
    
    # Save figure
    output_dir = Path("Academic_Thesis_Charts")
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / "Figure_19_CORRECTED_Spatial_Validation_Maps.png"
    
    plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white', edgecolor='none')
    plt.savefig(output_path.with_suffix('.pdf'), bbox_inches='tight', facecolor='white', edgecolor='none')
    
    print(f"\n✅ CORRECTED Figure 19 saved successfully:")
    print(f"   📁 {output_path}")
    print(f"   📁 {output_path.with_suffix('.pdf')}")
    
    plt.show()

if __name__ == "__main__":
    create_figure19_corrected()
