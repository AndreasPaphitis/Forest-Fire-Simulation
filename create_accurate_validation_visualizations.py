#!/usr/bin/env python3
"""
Accurate Validation Visualizations
Creates only scientifically accurate visualizations based on real validation data.
NO fake animations or interpolated progressions.
"""
import sys
import pickle
import numpy as np
import matplotlib.pyplot as plt
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, '.')

def load_validation_data(day):
    """Load real validation data for a specific day."""
    results_dir = Path("validation_results_optimized")
    
    print(f"📊 Loading Day {day} validation data...")
    
    try:
        # Load JSON results
        results_file = results_dir / f"day_{day}_validation_result.json"
        with open(results_file, 'r') as f:
            validation_results = json.load(f)
        
        # Load forest model for final fire perimeter
        forest_model_file = results_dir / f"day_{day}_forest_model.pkl"
        with open(forest_model_file, 'rb') as f:
            forest_model = pickle.load(f)
        
        # Load config for grid info
        config_file = results_dir / f"day_{day}_config.pkl"
        with open(config_file, 'rb') as f:
            config = pickle.load(f)
        
        print(f"✅ Loaded Day {day} data - Grid: {config.grid_size}, Resolution: {config.model_resolution}m")
        
        return validation_results, forest_model, config
        
    except Exception as e:
        print(f"❌ Error loading Day {day} data: {e}")
        return None, None, None

def create_final_fire_perimeter_map(forest_model, config, day, output_dir="validation_processed_results"):
    """Create accurate map of final burned area."""
    print(f"🗺️  Creating final fire perimeter map for Day {day}...")
    
    try:
        # Get real fire perimeter from forest model
        fire_perimeter = forest_model.get_2d_fire_perimeter()
        
        # Create figure
        fig, ax = plt.subplots(figsize=(12, 10))
        
        # Convert to real-world coordinates
        x_coords = np.arange(fire_perimeter.shape[1]) * config.model_resolution  # meters
        y_coords = np.arange(fire_perimeter.shape[0]) * config.model_resolution  # meters
        X, Y = np.meshgrid(x_coords, y_coords)
        
        # Plot burned areas
        burned_mask = fire_perimeter > 0
        burned_area_ha = burned_mask.sum() * (config.model_resolution ** 2) / 10000  # hectares
        
        # Create the map
        im = ax.imshow(fire_perimeter, extent=[0, fire_perimeter.shape[1] * config.model_resolution,
                                             0, fire_perimeter.shape[0] * config.model_resolution],
                      cmap='Reds', origin='lower', alpha=0.8)
        
        # Add ignition point
        igni_x = config.ignition_points[0][1] * config.model_resolution
        igni_y = config.ignition_points[0][0] * config.model_resolution
        ax.plot(igni_x, igni_y, 'go', markersize=12, markeredgecolor='black', 
                markeredgewidth=2, label='Ignition Point')
        
        # Add colorbar
        cbar = plt.colorbar(im, ax=ax)
        cbar.set_label('Fire Intensity', rotation=270, labelpad=20)
        
        # Formatting
        ax.set_xlabel('Distance (meters)')
        ax.set_ylabel('Distance (meters)')
        ax.set_title(f'🔥 Day {day} Final Fire Perimeter\nBurned Area: {burned_area_ha:.1f} hectares')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        # Save map
        output_file = Path(output_dir) / f"day_{day}_final_fire_perimeter.png"
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"✅ Fire perimeter map saved: {output_file}")
        plt.close()
        
        return burned_area_ha
        
    except Exception as e:
        print(f"❌ Error creating fire perimeter map: {e}")
        return 0

def create_spread_statistics_dashboard(validation_results, day, output_dir="validation_processed_results"):
    """Create accurate statistics dashboard from real data."""
    print(f"📊 Creating statistics dashboard for Day {day}...")
    
    try:
        stats = validation_results['vertical_spread_stats']
        
        # Create 2x2 dashboard
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
        
        # Plot 1: Spread Events Bar Chart
        spread_types = ['Horizontal', 'Vertical', 'Ember']
        spread_values = [stats['horizontal_spread'], stats['vertical_spread'], stats['ember_spread']]
        colors = ['#ff7f0e', '#d62728', '#ff9999']
        
        bars = ax1.bar(spread_types, spread_values, color=colors, alpha=0.8)
        ax1.set_ylabel('Number of Spread Events')
        ax1.set_title(f'🔥 Day {day} Fire Spread Events\nTotal: {stats["total_spread"]:,} events')
        
        # Add value labels
        for bar, value in zip(bars, spread_values):
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height,
                    f'{value/1000:.0f}K', ha='center', va='bottom', fontweight='bold')
        
        # Plot 2: Percentage Distribution Pie Chart
        percentages = [stats['horizontal_percentage'], stats['vertical_percentage'], stats['ember_percentage']]
        ax2.pie(percentages, labels=spread_types, colors=colors, autopct='%1.1f%%', startangle=90)
        ax2.set_title(f'📊 Day {day} Spread Distribution')
        
        # Plot 3: Efficiency Comparison
        efficiency_types = ['Horizontal', 'Vertical', 'Ember']
        efficiency_values = [stats['horizontal_efficiency'], stats['vertical_efficiency'], stats['ember_efficiency']]
        
        bars3 = ax3.bar(efficiency_types, efficiency_values, color=colors, alpha=0.8)
        ax3.set_ylabel('Efficiency (%)')
        ax3.set_title(f'⚡ Day {day} Spread Efficiency')
        
        # Add value labels
        for bar, value in zip(bars3, efficiency_values):
            height = bar.get_height()
            ax3.text(bar.get_x() + bar.get_width()/2., height,
                    f'{value:.1f}%', ha='center', va='bottom', fontweight='bold')
        
        # Plot 4: Key Ratios
        ratios = ['Vertical/Horizontal', 'Ember/Horizontal', 'Ember/Vertical']
        ratio_values = [stats['vertical_horizontal_ratio'], stats['ember_horizontal_ratio'], stats['ember_vertical_ratio']]
        
        bars4 = ax4.bar(ratios, ratio_values, color=['green', 'orange', 'red'], alpha=0.8)
        ax4.set_ylabel('Ratio')
        ax4.set_title(f'📈 Day {day} Spread Ratios')
        ax4.tick_params(axis='x', rotation=45)
        
        # Add value labels
        for bar, value in zip(bars4, ratio_values):
            height = bar.get_height()
            ax4.text(bar.get_x() + bar.get_width()/2., height,
                    f'{value:.2f}', ha='center', va='bottom', fontweight='bold')
        
        plt.tight_layout()
        
        # Save dashboard
        output_file = Path(output_dir) / f"day_{day}_accurate_statistics_dashboard.png"
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"✅ Statistics dashboard saved: {output_file}")
        plt.close()
        
    except Exception as e:
        print(f"❌ Error creating statistics dashboard: {e}")

def create_performance_analysis(validation_results, day, output_dir="validation_processed_results"):
    """Create performance analysis from real metrics."""
    print(f"⚡ Creating performance analysis for Day {day}...")
    
    try:
        # Extract performance data
        exec_time_hours = validation_results['execution_time'] / 3600
        objective_value = validation_results['objective_value']
        
        # Create performance plot
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
        
        # Plot 1: Execution Time
        ax1.bar(['Execution Time'], [exec_time_hours], color='steelblue', alpha=0.8)
        ax1.set_ylabel('Time (hours)')
        ax1.set_title(f'⏱️ Day {day} Simulation Execution Time')
        ax1.text(0, exec_time_hours, f'{exec_time_hours:.1f}h', ha='center', va='bottom', fontweight='bold')
        
        # Plot 2: Objective Value
        ax2.bar(['Objective Value'], [objective_value], color='green', alpha=0.8)
        ax2.set_ylabel('Objective Value')
        ax2.set_title(f'🎯 Day {day} Validation Objective')
        ax2.text(0, objective_value, f'{objective_value:.3f}', ha='center', va='bottom', fontweight='bold')
        
        # Plot 3: Spread Classification
        classification = validation_results['vertical_spread_stats']['spread_classification']
        ax3.text(0.5, 0.5, classification, ha='center', va='center', fontsize=14, 
                bbox=dict(boxstyle="round,pad=0.3", facecolor="lightblue", alpha=0.8))
        ax3.set_xlim(0, 1)
        ax3.set_ylim(0, 1)
        ax3.set_title(f'🔍 Day {day} Fire Behavior Classification')
        ax3.axis('off')
        
        # Plot 4: Total Ignitions
        total_ignitions = validation_results['vertical_spread_stats']['total_ignitions']
        ax4.bar(['Total Ignitions'], [total_ignitions], color='orange', alpha=0.8)
        ax4.set_ylabel('Number of Ignitions')
        ax4.set_title(f'🔥 Day {day} Total Ignition Events')
        ax4.text(0, total_ignitions, f'{total_ignitions:,}', ha='center', va='bottom', fontweight='bold')
        
        plt.tight_layout()
        
        # Save performance analysis
        output_file = Path(output_dir) / f"day_{day}_accurate_performance_analysis.png"
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"✅ Performance analysis saved: {output_file}")
        plt.close()
        
    except Exception as e:
        print(f"❌ Error creating performance analysis: {e}")

def create_comparison_dashboard(day3_results, day4_results, output_dir="validation_processed_results"):
    """Create accurate Day 3 vs Day 4 comparison."""
    print(f"🔍 Creating Day 3 vs Day 4 comparison...")
    
    try:
        # Extract data
        day3_stats = day3_results['vertical_spread_stats']
        day4_stats = day4_results['vertical_spread_stats']
        
        # Create comparison
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
        
        # Plot 1: Spread Events Comparison
        categories = ['Horizontal', 'Vertical', 'Ember']
        day3_values = [day3_stats['horizontal_spread'], day3_stats['vertical_spread'], day3_stats['ember_spread']]
        day4_values = [day4_stats['horizontal_spread'], day4_stats['vertical_spread'], day4_stats['ember_spread']]
        
        x = np.arange(len(categories))
        width = 0.35
        
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
                        f'{int(height/1000)}K', ha='center', va='bottom', fontsize=8)
        
        # Plot 2: Objective Values
        objectives = [day3_results['objective_value'], day4_results['objective_value']]
        ax2.bar(['Day 3', 'Day 4'], objectives, color=['#ff7f0e', '#1f77b4'], alpha=0.8)
        ax2.set_ylabel('Objective Value')
        ax2.set_title('🎯 Validation Objective Comparison')
        
        for i, v in enumerate(objectives):
            ax2.text(i, v, f'{v:.3f}', ha='center', va='bottom', fontweight='bold')
        
        # Plot 3: Execution Times
        exec_times = [day3_results['execution_time']/3600, day4_results['execution_time']/3600]
        ax3.bar(['Day 3', 'Day 4'], exec_times, color=['#ff7f0e', '#1f77b4'], alpha=0.8)
        ax3.set_ylabel('Execution Time (hours)')
        ax3.set_title('⏱️ Simulation Time Comparison')
        
        for i, v in enumerate(exec_times):
            ax3.text(i, v, f'{v:.1f}h', ha='center', va='bottom', fontweight='bold')
        
        # Plot 4: Efficiency Comparison
        day3_eff = [day3_stats['horizontal_efficiency'], day3_stats['vertical_efficiency'], day3_stats['ember_efficiency']]
        day4_eff = [day4_stats['horizontal_efficiency'], day4_stats['vertical_efficiency'], day4_stats['ember_efficiency']]
        
        bars3 = ax4.bar(x - width/2, day3_eff, width, label='Day 3', color='#ff7f0e', alpha=0.8)
        bars4 = ax4.bar(x + width/2, day4_eff, width, label='Day 4', color='#1f77b4', alpha=0.8)
        
        ax4.set_xlabel('Spread Type')
        ax4.set_ylabel('Efficiency (%)')
        ax4.set_title('⚡ Spread Efficiency Comparison')
        ax4.set_xticks(x)
        ax4.set_xticklabels(categories)
        ax4.legend()
        
        plt.tight_layout()
        
        # Save comparison
        output_file = Path(output_dir) / "day_3_vs_day_4_accurate_comparison.png"
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"✅ Comparison dashboard saved: {output_file}")
        plt.close()
        
    except Exception as e:
        print(f"❌ Error creating comparison dashboard: {e}")

def main():
    """Create all accurate visualizations from real validation data."""
    print("🎯 ACCURATE VALIDATION VISUALIZATIONS")
    print("=" * 80)
    print("Creating only scientifically accurate visualizations based on real data")
    print("NO fake animations or interpolated progressions")
    
    # Ensure output directory exists
    output_dir = Path("validation_processed_results")
    output_dir.mkdir(exist_ok=True)
    
    # Load data for both days
    print(f"\n📊 LOADING VALIDATION DATA")
    print("=" * 50)
    
    day3_results, day3_forest, day3_config = load_validation_data(3)
    day4_results, day4_forest, day4_config = load_validation_data(4)
    
    if not all([day3_results, day3_forest, day3_config, day4_results, day4_forest, day4_config]):
        print("❌ Failed to load validation data")
        return
    
    # Create accurate visualizations for Day 3
    print(f"\n🔥 CREATING ACCURATE VISUALIZATIONS FOR DAY 3")
    print("=" * 60)
    
    burned_area_3 = create_final_fire_perimeter_map(day3_forest, day3_config, 3, output_dir)
    create_spread_statistics_dashboard(day3_results, 3, output_dir)
    create_performance_analysis(day3_results, 3, output_dir)
    
    # Create accurate visualizations for Day 4
    print(f"\n🔥 CREATING ACCURATE VISUALIZATIONS FOR DAY 4")
    print("=" * 60)
    
    burned_area_4 = create_final_fire_perimeter_map(day4_forest, day4_config, 4, output_dir)
    create_spread_statistics_dashboard(day4_results, 4, output_dir)
    create_performance_analysis(day4_results, 4, output_dir)
    
    # Create comparison
    print(f"\n📊 CREATING DAY 3 vs DAY 4 COMPARISON")
    print("=" * 60)
    
    create_comparison_dashboard(day3_results, day4_results, output_dir)
    
    # Summary
    print(f"\n✅ ALL ACCURATE VISUALIZATIONS COMPLETE!")
    print("=" * 80)
    print(f"📁 All files saved to: {output_dir}")
    print(f"🔥 Day 3 burned area: {burned_area_3:.1f} hectares")
    print(f"🔥 Day 4 burned area: {burned_area_4:.1f} hectares")
    
    # List generated files
    print("\n📁 Generated accurate visualization files:")
    for file in sorted(output_dir.glob("*accurate*")):
        print(f"   • {file.name}")
    
    print("\n🎯 These visualizations are based on REAL validation data only!")
    print("🚫 NO fake animations or interpolated progressions included!")

if __name__ == "__main__":
    main()
