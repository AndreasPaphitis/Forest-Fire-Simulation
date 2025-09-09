#!/usr/bin/env python3
"""
Final Academic Quality Chart Creation
Creates publication-ready charts with consistent styling, clear titles, and proper axis labels
Following academic best practices for thesis inclusion
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# Import our styling system and enhance it for academic standards
from chart_styling_system import styler

class AcademicChartCreator:
    """Enhanced chart creator for academic publication standards."""
    
    def __init__(self):
        """Initialize with strict academic styling."""
        self.setup_academic_style()
        self.setup_consistent_colors()
    
    def setup_academic_style(self):
        """Configure matplotlib for academic publication standards."""
        
        # Academic publication settings
        plt.rcParams.update({
            # Fonts - Times New Roman is preferred for academic work
            'font.family': 'serif',
            'font.serif': ['Times New Roman', 'Times', 'DejaVu Serif', 'serif'],
            'font.size': 12,
            'axes.titlesize': 14,
            'axes.labelsize': 12,
            'xtick.labelsize': 11,
            'ytick.labelsize': 11,
            'legend.fontsize': 11,
            'figure.titlesize': 16,
            'axes.titleweight': 'bold',
            'figure.titleweight': 'bold',
            
            # Academic spacing and layout
            'axes.titlepad': 20,
            'axes.labelpad': 10,
            'xtick.major.pad': 8,
            'ytick.major.pad': 8,
            'legend.frameon': True,
            'legend.fancybox': True,
            'legend.shadow': False,  # No shadows for academic work
            'legend.edgecolor': 'black',
            'legend.facecolor': 'white',
            
            # High quality output
            'figure.dpi': 100,
            'savefig.dpi': 300,
            'savefig.bbox': 'tight',
            'savefig.pad_inches': 0.15,
            'savefig.facecolor': 'white',
            'savefig.edgecolor': 'none',
            
            # Clean, academic appearance
            'axes.linewidth': 1.0,
            'grid.linewidth': 0.5,
            'lines.linewidth': 2.0,
            'patch.linewidth': 0.5,
            'axes.edgecolor': 'black',
            'axes.axisbelow': True,
        })
        
        # Clean academic style
        sns.set_style("whitegrid", {
            "axes.spines.left": True,
            "axes.spines.bottom": True,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "grid.color": "#d0d0d0",
            "grid.linewidth": 0.5,
            "axes.edgecolor": "black",
            "axes.linewidth": 1.0,
        })
    
    def setup_consistent_colors(self):
        """Define strictly consistent academic color scheme."""
        
        # Academic color palette - colorblind safe and print-friendly
        self.academic_colors = {
            # Primary sensitivity colors (MUST be consistent)
            'critical': '#d62728',      # Academic red for critical parameters
            'moderate': '#1f77b4',      # Academic blue for moderate parameters
            
            # Validation colors (consistent across all charts)
            'day3': '#ff7f0e',          # Academic orange for Day 3
            'day4': '#2ca02c',          # Academic green for Day 4
            
            # Fire spread mechanism colors (consistent)
            'ember': '#d62728',         # Red for ember (most important)
            'horizontal': '#1f77b4',    # Blue for horizontal
            'vertical': '#2ca02c',      # Green for vertical
            
            # Supporting colors
            'neutral': '#7f7f7f',       # Gray for neutral/other
            'accent': '#ff7f0e',        # Orange for highlights
        }
        
        # Create parameter-specific color mapping to ensure consistency
        self.parameter_colors = {
            'spread_probability': self.academic_colors['critical'],
            'fuel_consumption_rate': self.academic_colors['critical'],
            'ember_probability': self.academic_colors['critical'],
            'ember_ignition': self.academic_colors['critical'],
            'fuel_moisture_baseline': self.academic_colors['moderate'],  # FIX: Was inconsistent
            'min_fuel_value': self.academic_colors['critical'],
            'slope_influence': self.academic_colors['critical'],
            'ember_wind_factor': self.academic_colors['moderate'],
            'ignition_threshold': self.academic_colors['critical'],
            'ember_height_factor': self.academic_colors['critical'],
            'wind_influence_on_spread': self.academic_colors['critical'],
            'ember_distance': self.academic_colors['critical'],
            'ember_rise': self.academic_colors['moderate']
        }
    
    def get_parameter_color(self, parameter, tier):
        """Get consistent color for a parameter based on tier."""
        if tier == 'CRITICAL':
            return self.academic_colors['critical']
        else:
            return self.academic_colors['moderate']
    
    def create_figure(self, figsize=(10, 6)):
        """Create academic-quality figure."""
        fig, ax = plt.subplots(figsize=figsize)
        ax.grid(True, alpha=0.3)
        ax.set_axisbelow(True)
        return fig, ax
    
    def save_figure(self, fig, filepath, title=None, tight_layout=True):
        """Save figure with academic standards."""
        if title:
            fig.suptitle(title, fontsize=16, fontweight='bold', y=0.98)
        
        if tight_layout:
            plt.tight_layout()
        
        fig.savefig(filepath, dpi=300, bbox_inches='tight', 
                   facecolor='white', edgecolor='none', pad_inches=0.15)
        plt.close(fig)

def create_final_academic_charts():
    """Create final academic-quality charts for thesis."""
    
    print("🎓 Creating FINAL ACADEMIC QUALITY charts for thesis...")
    
    # Create output directory
    output_dir = Path("Final_Thesis_Charts")
    output_dir.mkdir(exist_ok=True)
    
    # Initialize academic chart creator
    creator = AcademicChartCreator()
    
    # Get data
    sensitivity_data = get_sensitivity_data()
    validation_data = get_validation_data()
    
    print("📊 Creating Sensitivity Analysis Charts...")
    create_sensitivity_academic_charts(creator, sensitivity_data, output_dir)
    
    print("📈 Creating Validation Charts...")
    create_validation_academic_charts(creator, validation_data, output_dir)
    
    print("🎯 Creating Combined Analysis Charts...")
    create_combined_academic_charts(creator, sensitivity_data, validation_data, output_dir)
    
    print("✅ Final academic charts created successfully!")
    print(f"📁 Charts saved to: {output_dir.absolute()}")

def get_sensitivity_data():
    """Get sensitivity analysis data."""
    return {
        'parameters': [
            'spread_probability', 'fuel_consumption_rate', 'ember_probability',
            'ember_ignition', 'fuel_moisture_baseline', 'min_fuel_value',
            'slope_influence', 'ember_wind_factor', 'ignition_threshold',
            'ember_height_factor', 'wind_influence_on_spread', 'ember_distance', 'ember_rise'
        ],
        'scores': [1.4063, 0.1609, 0.1159, 0.0564, 0.0382, 0.0133, 
                  0.0110, 0.0095, 0.0089, 0.0073, 0.0064, 0.0049, 0.0009],
        'tiers': ['CRITICAL', 'CRITICAL', 'CRITICAL', 'CRITICAL', 'MODERATE', 
                 'CRITICAL', 'CRITICAL', 'MODERATE', 'CRITICAL', 'CRITICAL',
                 'CRITICAL', 'CRITICAL', 'MODERATE']
    }

def get_validation_data():
    """Get validation data."""
    return {
        'Day 3': {
            'objective_value': 0.36478319063434,
            'execution_time': 92767.42757368088,
            'vertical_percentage': 3.5425738519179046,
            'horizontal_percentage': 24.660087492950645,
            'ember_percentage': 41.97787294187608,
            'vertical_efficiency': 12.211482536531653,
            'horizontal_efficiency': 85.00492589772773,
            'ember_efficiency': 144.70045898208804,
        },
        'Day 4': {
            'objective_value': 0.4009607768174204,
            'execution_time': 93156.15769529343,
            'vertical_percentage': 3.567978287731257,
            'horizontal_percentage': 24.646308987141115,
            'ember_percentage': 41.94988990928136,
            'vertical_efficiency': 12.293112729411474,
            'horizontal_efficiency': 84.91639531121874,
            'ember_efficiency': 144.53415465403728,
        }
    }

def create_sensitivity_academic_charts(creator, data, output_dir):
    """Create academic-quality sensitivity analysis charts."""
    
    # 1. Parameter Sensitivity Ranking (Main Chart)
    fig, ax = creator.create_figure(figsize=(12, 8))
    
    # CONSISTENT COLORS: Use tier-based coloring
    colors = [creator.get_parameter_color(param, tier) 
             for param, tier in zip(data['parameters'], data['tiers'])]
    
    bars = ax.bar(range(len(data['parameters'])), data['scores'], 
                  color=colors, alpha=0.8, edgecolor='black', linewidth=0.5)
    
    # Professional axis labels and title
    ax.set_xticks(range(len(data['parameters'])))
    ax.set_xticklabels([p.replace('_', ' ').title() for p in data['parameters']], 
                       rotation=45, ha='right')
    ax.set_ylabel('Sensitivity Score', fontweight='bold')
    ax.set_xlabel('Model Parameters', fontweight='bold')
    
    # Add value labels on bars
    for bar, score in zip(bars, data['scores']):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height + max(data['scores']) * 0.01,
                f'{score:.4f}', ha='center', va='bottom', fontweight='bold', fontsize=9)
    
    # Professional legend
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor=creator.academic_colors['critical'], 
              edgecolor='black', label='Critical Parameters (Sensitivity > 0.01)'),
        Patch(facecolor=creator.academic_colors['moderate'], 
              edgecolor='black', label='Moderate Parameters (Sensitivity ≤ 0.01)')
    ]
    ax.legend(handles=legend_elements, loc='upper right', frameon=True, 
              edgecolor='black', facecolor='white')
    
    creator.save_figure(fig, output_dir / 'Figure_1_Parameter_Sensitivity_Ranking.png',
                       'Parameter Sensitivity Analysis Results\n(Method 2 Range-Based Analysis, August 2025)')
    
    # 2. Top 5 Parameters Focus
    fig, ax = creator.create_figure(figsize=(10, 6))
    
    top5_params = data['parameters'][:5]
    top5_scores = data['scores'][:5]
    top5_tiers = data['tiers'][:5]
    
    top5_colors = [creator.get_parameter_color(param, tier) 
                   for param, tier in zip(top5_params, top5_tiers)]
    
    bars = ax.bar(range(len(top5_params)), top5_scores, 
                  color=top5_colors, alpha=0.8, edgecolor='black', linewidth=0.5)
    
    ax.set_xticks(range(len(top5_params)))
    ax.set_xticklabels([p.replace('_', ' ').title() for p in top5_params], rotation=45, ha='right')
    ax.set_ylabel('Sensitivity Score', fontweight='bold')
    ax.set_xlabel('Top 5 Most Sensitive Parameters', fontweight='bold')
    
    # Add value labels
    for bar, score in zip(bars, top5_scores):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height + max(top5_scores) * 0.02,
                f'{score:.4f}', ha='center', va='bottom', fontweight='bold', fontsize=10)
    
    creator.save_figure(fig, output_dir / 'Figure_2_Top5_Parameters_Focus.png',
                       'Top 5 Most Sensitive Parameters\n(Selected for Grid Search Calibration)')
    
    # 3. Sensitivity to Calibration Workflow
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    
    # Top 4 calibrated parameters
    top4_params = data['parameters'][:4]
    top4_scores = data['scores'][:4]
    top4_tiers = data['tiers'][:4]
    calibrated_values = [0.95, 0.55, 0.6, 0.55]
    
    # Sensitivity scores
    colors1 = [creator.get_parameter_color(param, tier) 
              for param, tier in zip(top4_params, top4_tiers)]
    
    bars1 = ax1.bar(range(len(top4_params)), top4_scores, 
                    color=colors1, alpha=0.8, edgecolor='black', linewidth=0.5)
    
    ax1.set_xticks(range(len(top4_params)))
    ax1.set_xticklabels([p.replace('_', ' ').title() for p in top4_params], rotation=45, ha='right')
    ax1.set_ylabel('Sensitivity Score', fontweight='bold')
    ax1.set_xlabel('Parameters', fontweight='bold')
    ax1.set_title('(a) Sensitivity Analysis Results', fontweight='bold', pad=15)
    
    # Add value labels
    for bar, score in zip(bars1, top4_scores):
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height + max(top4_scores) * 0.02,
                f'{score:.4f}', ha='center', va='bottom', fontweight='bold', fontsize=9)
    
    # Calibrated values
    bars2 = ax2.bar(range(len(top4_params)), calibrated_values,
                    color=creator.academic_colors['accent'], alpha=0.8,
                    edgecolor='black', linewidth=0.5)
    
    ax2.set_xticks(range(len(top4_params)))
    ax2.set_xticklabels([p.replace('_', ' ').title() for p in top4_params], rotation=45, ha='right')
    ax2.set_ylabel('Calibrated Parameter Value', fontweight='bold')
    ax2.set_xlabel('Parameters', fontweight='bold')
    ax2.set_title('(b) Final Calibrated Values', fontweight='bold', pad=15)
    
    # Add value labels
    for bar, value in zip(bars2, calibrated_values):
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height + max(calibrated_values) * 0.02,
                f'{value:.2f}', ha='center', va='bottom', fontweight='bold', fontsize=9)
    
    plt.tight_layout()
    creator.save_figure(fig, output_dir / 'Figure_3_Sensitivity_to_Calibration_Workflow.png',
                       'From Sensitivity Analysis to Parameter Calibration\n(Complete Workflow Implementation)',
                       tight_layout=False)

def create_validation_academic_charts(creator, data, output_dir):
    """Create academic-quality validation charts."""
    
    # 4. Validation Performance Comparison
    fig, ax = creator.create_figure(figsize=(8, 6))
    
    days = list(data.keys())
    objectives = [data[day]['objective_value'] for day in days]
    colors = [creator.academic_colors['day3'], creator.academic_colors['day4']]
    
    bars = ax.bar(days, objectives, color=colors, alpha=0.8, 
                  edgecolor='black', linewidth=0.5)
    
    ax.set_ylabel('Objective Function Value\n(Combined Spatial Similarity)', fontweight='bold')
    ax.set_xlabel('Validation Days', fontweight='bold')
    ax.set_ylim(0, max(objectives) * 1.15)
    
    # Add value labels
    for bar, obj in zip(bars, objectives):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height + height*0.02,
                f'{obj:.4f}', ha='center', va='bottom', fontweight='bold', fontsize=11)
    
    # Add improvement annotation
    improvement = (objectives[1] - objectives[0]) / objectives[0] * 100
    ax.annotate(f'+{improvement:.1f}% improvement', 
                xy=(1, objectives[1]), xytext=(0.5, objectives[1] + 0.02),
                arrowprops=dict(arrowstyle='->', color='black', lw=1),
                ha='center', fontweight='bold')
    
    creator.save_figure(fig, output_dir / 'Figure_4_Validation_Performance_Comparison.png',
                       'Validation Performance Comparison\n(2023 Tenerife Fire Event - Days 3 and 4)')
    
    # 5. Fire Spread Mechanisms Analysis
    fig, ax = creator.create_figure(figsize=(10, 6))
    
    spread_types = ['Vertical', 'Horizontal', 'Ember']
    day3_spreads = [data['Day 3']['vertical_percentage'], 
                   data['Day 3']['horizontal_percentage'],
                   data['Day 3']['ember_percentage']]
    day4_spreads = [data['Day 4']['vertical_percentage'],
                   data['Day 4']['horizontal_percentage'], 
                   data['Day 4']['ember_percentage']]
    
    # Consistent colors for spread mechanisms
    spread_colors = [creator.academic_colors['vertical'], 
                    creator.academic_colors['horizontal'],
                    creator.academic_colors['ember']]
    
    x = np.arange(len(spread_types))
    width = 0.35
    
    bars1 = ax.bar(x - width/2, day3_spreads, width, label='Day 3', 
                   color=creator.academic_colors['day3'], alpha=0.8, 
                   edgecolor='black', linewidth=0.5)
    bars2 = ax.bar(x + width/2, day4_spreads, width, label='Day 4',
                   color=creator.academic_colors['day4'], alpha=0.8, 
                   edgecolor='black', linewidth=0.5)
    
    ax.set_ylabel('Percentage of Total Spread Events (%)', fontweight='bold')
    ax.set_xlabel('Fire Spread Mechanism', fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(spread_types)
    
    # Professional legend
    ax.legend(frameon=True, edgecolor='black', facecolor='white')
    
    # Add value labels
    for bars in [bars1, bars2]:
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                    f'{height:.1f}%', ha='center', va='bottom', fontweight='bold', fontsize=9)
    
    creator.save_figure(fig, output_dir / 'Figure_5_Fire_Spread_Mechanisms.png',
                       'Fire Spread Mechanism Analysis\n(Ember Transport Dominance in Tenerife Fire)')
    
    # 6. Advanced Performance Dashboard
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(14, 10))
    
    # Objective values
    bars1 = ax1.bar(days, objectives, color=colors, alpha=0.8, 
                    edgecolor='black', linewidth=0.5)
    ax1.set_ylabel('Objective Value', fontweight='bold')
    ax1.set_xlabel('Validation Days', fontweight='bold')
    ax1.set_title('(a) Spatial Similarity Performance', fontweight='bold', pad=15)
    ax1.set_ylim(0, max(objectives) * 1.15)
    
    for bar, obj in zip(bars1, objectives):
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height + height*0.02,
                f'{obj:.4f}', ha='center', va='bottom', fontweight='bold', fontsize=10)
    
    # Execution times
    exec_times = [data[day]['execution_time'] / 3600 for day in days]
    bars2 = ax2.bar(days, exec_times, color=colors, alpha=0.8,
                    edgecolor='black', linewidth=0.5)
    ax2.set_ylabel('Execution Time (hours)', fontweight='bold')
    ax2.set_xlabel('Validation Days', fontweight='bold')
    ax2.set_title('(b) Computational Performance', fontweight='bold', pad=15)
    
    for bar, time in zip(bars2, exec_times):
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height + height*0.02,
                f'{time:.1f}h', ha='center', va='bottom', fontweight='bold', fontsize=10)
    
    # Fire spread mechanisms
    bars3a = ax3.bar(x - width/2, day3_spreads, width, label='Day 3', 
                     color=creator.academic_colors['day3'], alpha=0.8, 
                     edgecolor='black', linewidth=0.5)
    bars3b = ax3.bar(x + width/2, day4_spreads, width, label='Day 4',
                     color=creator.academic_colors['day4'], alpha=0.8, 
                     edgecolor='black', linewidth=0.5)
    
    ax3.set_ylabel('Spread Events (%)', fontweight='bold')
    ax3.set_xlabel('Mechanism Type', fontweight='bold')
    ax3.set_title('(c) Fire Spread Mechanisms', fontweight='bold', pad=15)
    ax3.set_xticks(x)
    ax3.set_xticklabels(spread_types)
    ax3.legend(frameon=True, edgecolor='black', facecolor='white')
    
    # Efficiency comparison
    efficiency_types = ['Vertical', 'Horizontal', 'Ember']
    day3_eff = [data['Day 3']['vertical_efficiency'],
               data['Day 3']['horizontal_efficiency'],
               data['Day 3']['ember_efficiency']]
    day4_eff = [data['Day 4']['vertical_efficiency'],
               data['Day 4']['horizontal_efficiency'],
               data['Day 4']['ember_efficiency']]
    
    bars4a = ax4.bar(x - width/2, day3_eff, width, label='Day 3',
                     color=creator.academic_colors['day3'], alpha=0.8, 
                     edgecolor='black', linewidth=0.5)
    bars4b = ax4.bar(x + width/2, day4_eff, width, label='Day 4',
                     color=creator.academic_colors['day4'], alpha=0.8, 
                     edgecolor='black', linewidth=0.5)
    
    ax4.set_ylabel('Efficiency (%)', fontweight='bold')
    ax4.set_xlabel('Mechanism Type', fontweight='bold')
    ax4.set_title('(d) Fire Spread Efficiency', fontweight='bold', pad=15)
    ax4.set_xticks(x)
    ax4.set_xticklabels(efficiency_types)
    ax4.legend(frameon=True, edgecolor='black', facecolor='white')
    
    plt.tight_layout()
    creator.save_figure(fig, output_dir / 'Figure_6_Advanced_Performance_Dashboard.png',
                       'Comprehensive Validation Analysis Dashboard\n(2023 Tenerife Fire Event Performance Assessment)',
                       tight_layout=False)

def create_combined_academic_charts(creator, sens_data, val_data, output_dir):
    """Create combined analysis charts."""
    
    # 7. Efficiency Radar Chart
    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(projection='polar'))
    
    categories = ['Vertical\nEfficiency', 'Horizontal\nEfficiency', 'Ember\nEfficiency',
                 'Objective\nValue (×50)', 'Time\nEfficiency']
    
    # Normalize values for radar chart
    day3_values = [
        val_data['Day 3']['vertical_efficiency'] / 150,
        val_data['Day 3']['horizontal_efficiency'] / 100,
        val_data['Day 3']['ember_efficiency'] / 150,
        val_data['Day 3']['objective_value'] * 2,
        1 - (val_data['Day 3']['execution_time'] / 100000)
    ]
    
    day4_values = [
        val_data['Day 4']['vertical_efficiency'] / 150,
        val_data['Day 4']['horizontal_efficiency'] / 100, 
        val_data['Day 4']['ember_efficiency'] / 150,
        val_data['Day 4']['objective_value'] * 2,
        1 - (val_data['Day 4']['execution_time'] / 100000)
    ]
    
    # Complete the circle
    day3_values += day3_values[:1]
    day4_values += day4_values[:1]
    categories += categories[:1]
    
    angles = np.linspace(0, 2 * np.pi, len(categories), endpoint=True)
    
    # Plot with academic styling
    ax.plot(angles, day3_values, 'o-', linewidth=2.5, label='Day 3', 
            color=creator.academic_colors['day3'], markersize=6)
    ax.fill(angles, day3_values, alpha=0.15, color=creator.academic_colors['day3'])
    
    ax.plot(angles, day4_values, 's-', linewidth=2.5, label='Day 4', 
            color=creator.academic_colors['day4'], markersize=6)
    ax.fill(angles, day4_values, alpha=0.15, color=creator.academic_colors['day4'])
    
    # Customize
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(categories[:-1], fontsize=11, fontweight='bold')
    ax.set_ylim(0, 1)
    ax.set_yticks([0.2, 0.4, 0.6, 0.8, 1.0])
    ax.set_yticklabels(['0.2', '0.4', '0.6', '0.8', '1.0'], fontsize=10)
    ax.grid(True, alpha=0.3)
    
    plt.legend(loc='upper right', bbox_to_anchor=(1.2, 1.0), fontsize=12, 
               frameon=True, edgecolor='black', facecolor='white')
    
    creator.save_figure(fig, output_dir / 'Figure_7_Efficiency_Radar_Chart.png',
                       'Multi-Dimensional Performance Comparison\n(Normalized Efficiency Analysis)')
    
    # 8. Executive Summary Chart
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    
    # Key sensitivity findings
    top3_params = sens_data['parameters'][:3]
    top3_scores = sens_data['scores'][:3]
    
    bars1 = ax1.bar(range(len(top3_params)), top3_scores, 
                    color=creator.academic_colors['critical'], alpha=0.8,
                    edgecolor='black', linewidth=0.5)
    
    ax1.set_xticks(range(len(top3_params)))
    ax1.set_xticklabels([p.replace('_', ' ').title() for p in top3_params], rotation=45, ha='right')
    ax1.set_ylabel('Sensitivity Score', fontweight='bold')
    ax1.set_xlabel('Top 3 Critical Parameters', fontweight='bold')
    ax1.set_title('(a) Key Sensitivity Findings', fontweight='bold', pad=15)
    
    for bar, score in zip(bars1, top3_scores):
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height + max(top3_scores) * 0.02,
                f'{score:.4f}', ha='center', va='bottom', fontweight='bold', fontsize=10)
    
    # Key validation findings
    performance_metrics = ['Objective\nValue', 'Ember\nDominance (%)', 'Model\nImprovement (%)']
    day3_metrics = [val_data['Day 3']['objective_value'], 
                   val_data['Day 3']['ember_percentage'],
                   0]  # Baseline
    day4_metrics = [val_data['Day 4']['objective_value'],
                   val_data['Day 4']['ember_percentage'],
                   9.9]  # Improvement
    
    x = np.arange(len(performance_metrics))
    width = 0.35
    bars2a = ax2.bar(x - width/2, day3_metrics, width, label='Day 3',
                     color=creator.academic_colors['day3'], alpha=0.8, 
                     edgecolor='black', linewidth=0.5)
    bars2b = ax2.bar(x + width/2, day4_metrics, width, label='Day 4',
                     color=creator.academic_colors['day4'], alpha=0.8, 
                     edgecolor='black', linewidth=0.5)
    
    ax2.set_xticks(x)
    ax2.set_xticklabels(performance_metrics)
    ax2.set_ylabel('Performance Metric Value', fontweight='bold')
    ax2.set_xlabel('Validation Metrics', fontweight='bold')
    ax2.set_title('(b) Key Validation Findings', fontweight='bold', pad=15)
    ax2.legend(frameon=True, edgecolor='black', facecolor='white')
    
    plt.tight_layout()
    creator.save_figure(fig, output_dir / 'Figure_8_Executive_Summary.png',
                       'Key Research Findings Summary\n(Sensitivity Analysis and Validation Results)',
                       tight_layout=False)

if __name__ == "__main__":
    create_final_academic_charts()
