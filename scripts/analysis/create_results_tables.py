#!/usr/bin/env python3
"""
Create Results Tables as PNG Images
Matches existing thesis figure formatting and style
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import Rectangle
import numpy as np
import json
from pathlib import Path

def setup_academic_style():
    """Setup Times New Roman styling matching other thesis figures"""
    plt.style.use('default')
    plt.rcParams['font.family'] = 'serif'
    plt.rcParams['font.serif'] = ['Times New Roman', 'Times', 'Liberation Serif', 'serif']
    plt.rcParams['axes.linewidth'] = 1.5
    plt.rcParams['axes.edgecolor'] = '#333333'
    plt.rcParams['font.size'] = 12
    plt.rcParams['axes.labelsize'] = 14
    plt.rcParams['axes.titlesize'] = 16
    plt.rcParams['axes.titleweight'] = 'bold'

def get_colors():
    """Return established color palette"""
    return {
        'fire_red': '#d32f2f',
        'ember_orange': '#ff8f00',
        'forest_green': '#388e3c',
        'sky_blue': '#1976d2',
        'earth_brown': '#5d4037',
        'ash_gray': '#616161',
        'gold': '#f57c00',
        'white': '#ffffff',
        'black': '#000000',
        'light_red': '#ffebee',
        'light_green': '#e8f5e8',
        'light_gray': '#f5f5f5'
    }

def load_validation_data():
    """Load validation results"""
    results_dir = Path("results/validation/final")
    with open(results_dir / "validation_results_summary.json", 'r') as f:
        return json.load(f)

def create_table_1_comprehensive_validation():
    """Table 1: Comprehensive Validation Results"""
    setup_academic_style()
    colors = get_colors()
    data = load_validation_data()
    
    day3 = data["3"]
    day4 = data["4"]
    
    # Create figure
    fig, ax = plt.subplots(figsize=(16, 10))
    ax.axis('off')
    fig.patch.set_facecolor('white')
    
    # Table data
    table_data = [
        ["Validation Metric", "Day 3", "Day 4"],
        ["", "", ""],
        ["Spatial Performance", "", ""],
        ["Objective Value", f"{day3['objective_value']:.3f}", f"{day4['objective_value']:.3f}"],
        ["Execution Time (min)", f"{day3['execution_time']/60:.1f}", f"{day4['execution_time']/60:.1f}"],
        ["Improvement", "--", f"{((day3['objective_value'] - day4['objective_value']) / day3['objective_value'] * 100):.1f}%"],
        ["", "", ""],
        ["Fire Behavior Metrics", "", ""],
        ["P_vertical (%)", f"{day3['vertical_spread_stats']['vertical_percentage']:.2f}", f"{day4['vertical_spread_stats']['vertical_percentage']:.2f}"],
        ["P_ember (%)", f"{day3['vertical_spread_stats']['ember_percentage']:.1f}", f"{day4['vertical_spread_stats']['ember_percentage']:.1f}"],
        ["η_spread (ember, %)", f"{day3['vertical_spread_stats']['ember_efficiency']:.1f}", f"{day4['vertical_spread_stats']['ember_efficiency']:.1f}"],
        ["", "", ""],
        ["Expected Ranges", "", ""],
        ["P_vertical target", "30-50%", "30-50%"],
        ["P_ember target", "10-20%", "10-20%"]
    ]
    
    # Create table
    table = ax.table(cellText=table_data, cellLoc='center', loc='center',
                    colWidths=[0.45, 0.275, 0.275])
    
    table.auto_set_font_size(False)
    table.set_fontsize(12)
    table.scale(1, 2.5)
    
    # Style cells
    for i, row in enumerate(table_data):
        for j in range(3):
            cell = table[(i, j)]
            
            # Header row
            if i == 0:
                cell.set_facecolor(colors['fire_red'])
                cell.set_text_props(weight='bold', color='white', size=14)
                cell.set_height(0.06)
            # Section headers
            elif i in [2, 7, 12]:
                cell.set_facecolor(colors['ash_gray'])
                cell.set_text_props(weight='bold', color='white', size=13)
            # Empty rows
            elif row[0] == "":
                cell.set_facecolor(colors['light_gray'])
                cell.set_height(0.03)
            # Problematic values (P_vertical and P_ember actual values)
            elif i in [8, 9] and j > 0:
                cell.set_facecolor(colors['light_red'])
                cell.set_text_props(weight='bold')
            # Good performance (execution times)
            elif i == 4 and j > 0:
                cell.set_facecolor(colors['light_green'])
                cell.set_text_props(weight='bold')
            # Regular cells
            else:
                cell.set_facecolor('white')
                
            cell.set_edgecolor(colors['ash_gray'])
            cell.set_linewidth(1.5)
    
    # No title - academic standard: titles only in thesis captions
    
    output_dir = Path("results/figures/thesis")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "Table_1_Comprehensive_Validation.png"
    
    plt.savefig(output_file, dpi=300, bbox_inches='tight', facecolor='white', edgecolor='none')
    plt.close()
    
    return output_file

def create_table_2_sensitivity_ranking():
    """Table 2: Parameter Sensitivity Ranking"""
    setup_academic_style()
    colors = get_colors()
    
    # Create figure
    fig, ax = plt.subplots(figsize=(18, 9))
    ax.axis('off')
    fig.patch.set_facecolor('white')
    
    # Table data
    table_data = [
        ["Rank", "Parameter", "Sensitivity Index", "Physical Meaning"],
        ["1", "spread_probability", "1.4063", "Fundamental probability governing fire spread between adjacent cells"],
        ["2", "fuel_consumption_rate", "0.1609", "Rate parameter controlling fuel depletion during combustion"],
        ["3", "ember_probability", "0.1159", "Probability of ember generation during active fire spread"],
        ["4", "ember_ignition", "0.0564", "Success probability for ember-initiated ignition events"],
        ["5", "fuel_moisture_baseline", "0.0382", "Base fuel moisture content affecting ignition susceptibility"]
    ]
    
    # Create table
    table = ax.table(cellText=table_data, cellLoc='left', loc='center',
                    colWidths=[0.08, 0.25, 0.17, 0.5])
    
    table.auto_set_font_size(False)
    table.set_fontsize(11)
    table.scale(1, 3.0)
    
    # Sensitivity values for gradient coloring
    sensitivity_values = [1.4063, 0.1609, 0.1159, 0.0564, 0.0382]
    max_sens = max(sensitivity_values)
    
    # Style cells
    for i, row in enumerate(table_data):
        for j in range(4):
            cell = table[(i, j)]
            
            # Header row
            if i == 0:
                cell.set_facecolor(colors['sky_blue'])
                cell.set_text_props(weight='bold', color='white', size=13)
                cell.set_height(0.08)
            # Data rows - gradient coloring based on sensitivity
            else:
                intensity = sensitivity_values[i-1] / max_sens
                
                if j in [0, 2]:  # Rank and Sensitivity columns
                    if intensity > 0.8:
                        cell.set_facecolor(colors['fire_red'])
                        cell.set_text_props(weight='bold', color='white')
                    elif intensity > 0.4:
                        cell.set_facecolor(colors['ember_orange'])
                        cell.set_text_props(weight='bold', color='white')
                    elif intensity > 0.1:
                        cell.set_facecolor(colors['gold'])
                        cell.set_text_props(weight='bold', color='white')
                    else:
                        cell.set_facecolor('#fff3e0')
                        cell.set_text_props(weight='bold')
                elif j == 1:  # Parameter name
                    cell.set_facecolor(colors['light_gray'])
                    cell.set_text_props(family='monospace', size=10)
                else:  # Physical meaning
                    cell.set_facecolor('white')
                    
            cell.set_edgecolor(colors['ash_gray'])
            cell.set_linewidth(1.5)
    
    # No title - academic standard: titles only in thesis captions
    
    output_dir = Path("results/figures/thesis")
    output_file = output_dir / "Table_2_Sensitivity_Ranking.png"
    
    plt.savefig(output_file, dpi=300, bbox_inches='tight', facecolor='white', edgecolor='none')
    plt.close()
    
    return output_file

def create_table_3_calibration_comparison():
    """Table 3: Calibration Parameter Comparison"""
    setup_academic_style()
    colors = get_colors()
    
    # Create figure
    fig, ax = plt.subplots(figsize=(18, 10))
    ax.axis('off')
    fig.patch.set_facecolor('white')
    
    # Table data
    table_data = [
        ["Parameter", "Rank 1 (Error: 0.5127)", "Rank 2 (Error: 0.5360)", "Selection Rationale"],
        ["min_fuel_value", "0.02", "0.02", "Identical aggressive ignition threshold"],
        ["spread_probability", "0.95", "0.775", "Rank 2 selected for realistic spread rates"],
        ["fuel_consumption_rate", "0.30", "0.30", "Identical slow consumption approach"],
        ["ember_probability", "0.60", "0.60", "Identical high ember generation"]
    ]
    
    # Create table
    table = ax.table(cellText=table_data, cellLoc='center', loc='center',
                    colWidths=[0.25, 0.25, 0.25, 0.25])
    
    table.auto_set_font_size(False)
    table.set_fontsize(11)
    table.scale(1, 2.8)
    
    # Style cells
    for i, row in enumerate(table_data):
        for j in range(4):
            cell = table[(i, j)]
            
            # Header row
            if i == 0:
                cell.set_facecolor(colors['forest_green'])
                cell.set_text_props(weight='bold', color='white', size=13)
                cell.set_height(0.08)
            # Key difference row (spread_probability)
            elif i == 2:
                if j == 1:  # Rank 1 value (bad)
                    cell.set_facecolor('#ffcdd2')  # Light red
                    cell.set_text_props(weight='bold')
                elif j == 2:  # Rank 2 value (selected)
                    cell.set_facecolor('#c8e6c9')  # Light green
                    cell.set_text_props(weight='bold')
                elif j == 3:  # Rationale
                    cell.set_facecolor(colors['gold'])
                    cell.set_text_props(weight='bold', size=10)
                else:
                    cell.set_facecolor(colors['light_gray'])
                    cell.set_text_props(family='monospace', size=10)
            # Parameter names
            elif j == 0:
                cell.set_facecolor(colors['light_gray'])
                cell.set_text_props(family='monospace', size=10)
            # Regular cells
            else:
                cell.set_facecolor('white')
                
            cell.set_edgecolor(colors['ash_gray'])
            cell.set_linewidth(1.5)
    
    # No title - academic standard: titles only in thesis captions
    
    output_dir = Path("results/figures/thesis")
    output_file = output_dir / "Table_3_Calibration_Comparison.png"
    
    plt.savefig(output_file, dpi=300, bbox_inches='tight', facecolor='white', edgecolor='none')
    plt.close()
    
    return output_file

def create_table_4_computational_performance():
    """Table 4: Computational Performance Summary"""
    setup_academic_style()
    colors = get_colors()
    data = load_validation_data()
    
    day3 = data["3"]
    day4 = data["4"]
    
    # Create figure
    fig, ax = plt.subplots(figsize=(18, 10))
    ax.axis('off')
    fig.patch.set_facecolor('white')
    
    # Table data
    table_data = [
        ["Scenario", "Execution Time (min)", "Grid Size", "Timesteps", "Performance Notes"],
        ["Day 3 Validation", f"{day3['execution_time']/60:.1f}", "609×609×20", "100", "High vertical spread classification"],
        ["Day 4 Validation", f"{day4['execution_time']/60:.1f}", "609×609×20", "100", "Consistent behavior patterns"],
        ["", "", "", "", ""],
        ["Average", f"{(day3['execution_time'] + day4['execution_time'])/120:.1f}", "148 km²", "--", "Efficient simulation performance"],
        ["Total Fire Events (Day 3)", f"{day3['vertical_spread_stats']['total_spread']:,}", "--", "--", "High activity"],
        ["Total Fire Events (Day 4)", f"{day4['vertical_spread_stats']['total_spread']:,}", "--", "--", "Sustained activity"]
    ]
    
    # Create table
    table = ax.table(cellText=table_data, cellLoc='center', loc='center',
                    colWidths=[0.25, 0.18, 0.18, 0.14, 0.25])
    
    table.auto_set_font_size(False)
    table.set_fontsize(11)
    table.scale(1, 2.8)
    
    # Style cells
    for i, row in enumerate(table_data):
        for j in range(5):
            cell = table[(i, j)]
            
            # Header row
            if i == 0:
                cell.set_facecolor(colors['earth_brown'])
                cell.set_text_props(weight='bold', color='white', size=13)
                cell.set_height(0.08)
            # Empty row
            elif i == 3:
                cell.set_facecolor(colors['light_gray'])
                cell.set_height(0.03)
            # Summary row
            elif i == 4:
                cell.set_facecolor(colors['ash_gray'])
                cell.set_text_props(weight='bold', color='white')
            # Good execution times
            elif i in [1, 2] and j == 1:
                cell.set_facecolor(colors['light_green'])
                cell.set_text_props(weight='bold')
            # High fire events (problematic)
            elif i in [5, 6] and j == 1:
                cell.set_facecolor('#fff3e0')  # Light orange
                cell.set_text_props(weight='bold')
            # Regular cells
            else:
                cell.set_facecolor('white')
                
            cell.set_edgecolor(colors['ash_gray'])
            cell.set_linewidth(1.5)
    
    # No title - academic standard: titles only in thesis captions
    
    output_dir = Path("results/figures/thesis")
    output_file = output_dir / "Table_4_Computational_Performance.png"
    
    plt.savefig(output_file, dpi=300, bbox_inches='tight', facecolor='white', edgecolor='none')
    plt.close()
    
    return output_file

def main():
    """Generate all tables as PNG images"""
    
    print("=" * 70)
    print("GENERATING RESULTS TABLES AS PNG IMAGES")
    print("=" * 70)
    print()
    
    output_files = []
    
    print("📊 Creating Table 1: Comprehensive Validation Results...")
    output_files.append(create_table_1_comprehensive_validation())
    print(f"   ✅ SAVED")
    
    print("📊 Creating Table 2: Parameter Sensitivity Ranking...")
    output_files.append(create_table_2_sensitivity_ranking())
    print(f"   ✅ SAVED")
    
    print("📊 Creating Table 3: Calibration Parameter Comparison...")
    output_files.append(create_table_3_calibration_comparison())
    print(f"   ✅ SAVED")
    
    print("📊 Creating Table 4: Computational Performance Summary...")
    output_files.append(create_table_4_computational_performance())
    print(f"   ✅ SAVED")
    
    print()
    print("=" * 70)
    print("✅ ALL TABLES GENERATED SUCCESSFULLY!")
    print("=" * 70)
    print()
    print("📁 FILE LOCATIONS:")
    print()
    for i, filepath in enumerate(output_files, 1):
        abs_path = filepath.resolve()
        print(f"   Table {i}: {abs_path}")
    print()
    print("=" * 70)
    print("🎨 FORMATTING:")
    print("   • Times New Roman font (APA 7 compliant)")
    print("   • 300 DPI resolution (publication quality)")
    print("   • Established color scheme matching other thesis figures")
    print("   • Fire Red headers / Light red for problematic values")
    print("   • Light green for good performance")
    print("=" * 70)

if __name__ == "__main__":
    main()

