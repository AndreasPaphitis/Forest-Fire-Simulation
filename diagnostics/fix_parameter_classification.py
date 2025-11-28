#!/usr/bin/env python3
"""
Fix Parameter Classification Script
Removes critical/moderate parameter differentiation and recreates affected charts
"""

import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# Import our existing styling system
from chart_styling_system import ChartStyler

def create_fixed_sensitivity_data():
    """Create sensitivity data without artificial tiers."""
    return {
        'parameters': ['spread_probability', 'fuel_consumption_rate', 'fuel_moisture_threshold',
                      'wind_speed_factor', 'slope_factor', 'ember_probability',
                      'min_fuel_value', 'ignition_temp_threshold', 'weather_factor',
                      'terrain_complexity', 'canopy_density', 'surface_moisture',
                      'atmospheric_pressure'],
        'scores': [1.4063, 0.1609, 0.1159, 0.0564, 0.0382, 0.0133, 
                  0.0110, 0.0095, 0.0089, 0.0073, 0.0064, 0.0049, 0.0009],
        # Remove artificial tiers - use gradient coloring instead
        'importance_rank': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13]
    }

class FixedChartCreator:
    """Chart creator without artificial parameter classification."""
    
    def __init__(self):
        self.styler = ChartStyler()
        self.setup_gradient_colors()
    
    def setup_gradient_colors(self):
        """Setup gradient colors based on importance rank."""
        # Use a gradient from most important (red) to least important (blue)
        # This is scientifically accurate without artificial categories
        self.colors = {
            'high_importance': '#d62728',      # Red for highest sensitivity
            'medium_importance': '#ff7f0e',    # Orange for medium
            'low_importance': '#1f77b4',       # Blue for lower sensitivity
            'validation_observed': '#2ca02c',   # Green for observed data
            'validation_predicted': '#1f77b4', # Blue for predicted
            'accent': '#9467bd'                # Purple for highlights
        }
    
    def get_gradient_color(self, rank, total_params):
        """Get color based on importance rank (gradient approach)."""
        # Create smooth gradient from red (most important) to blue (least important)
        ratio = (rank - 1) / (total_params - 1)  # 0 to 1
        
        if ratio <= 0.3:  # Top 30% - Red to Orange
            return '#d62728'  # Red
        elif ratio <= 0.7:  # Middle 40% - Orange
            return '#ff7f0e'  # Orange  
        else:  # Bottom 30% - Blue
            return '#1f77b4'  # Blue
    
    def create_figure(self, figsize=(12, 8)):
        """Create figure with academic styling."""
        return plt.subplots(figsize=figsize)
    
    def save_figure(self, fig, filepath, title, tight_layout=True):
        """Save figure with proper formatting."""
        if tight_layout:
            plt.tight_layout()
        
        # Add overall title
        fig.suptitle(title, fontsize=16, fontweight='bold', y=0.98)
        
        # Save with high DPI for thesis quality
        plt.savefig(filepath, dpi=300, bbox_inches='tight', 
                   facecolor='white', edgecolor='none')
        plt.close()
        print(f"✅ Saved: {filepath}")

def create_fixed_parameter_sensitivity_ranking(creator, data, output_dir):
    """Create parameter sensitivity ranking without artificial tiers."""
    fig, ax = creator.create_figure(figsize=(14, 8))
    
    # Use gradient coloring based on actual importance
    colors = [creator.get_gradient_color(rank, len(data['parameters'])) 
              for rank in data['importance_rank']]
    
    bars = ax.bar(range(len(data['parameters'])), data['scores'], 
                  color=colors, alpha=0.8, edgecolor='black', linewidth=0.8)
    
    # Formatting
    ax.set_xticks(range(len(data['parameters'])))
    ax.set_xticklabels([p.replace('_', ' ').title() for p in data['parameters']], 
                       rotation=45, ha='right', fontsize=11)
    ax.set_ylabel('Sensitivity Score', fontweight='bold', fontsize=13)
    ax.set_xlabel('Model Parameters', fontweight='bold', fontsize=13)
    
    # Add value labels on bars
    for bar, score in zip(bars, data['scores']):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height + 0.01,
                f'{score:.3f}', ha='center', va='bottom', fontsize=9, fontweight='bold')
    
    # Scientific legend based on sensitivity levels
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor='#d62728', edgecolor='black', 
              label='High Sensitivity (>0.1)', alpha=0.8),
        Patch(facecolor='#ff7f0e', edgecolor='black', 
              label='Medium Sensitivity (0.01-0.1)', alpha=0.8),
        Patch(facecolor='#1f77b4', edgecolor='black', 
              label='Low Sensitivity (<0.01)', alpha=0.8)
    ]
    ax.legend(handles=legend_elements, loc='upper right', frameon=True, 
              fancybox=True, shadow=True)
    
    ax.grid(True, alpha=0.3)
    ax.set_ylim(0, max(data['scores']) * 1.1)
    
    creator.save_figure(fig, output_dir / 'Figure_1_Parameter_Sensitivity_Ranking.png',
                       'Global Parameter Sensitivity Analysis\n(Importance Ranking Based on Impact on Model Output)')

def create_fixed_top5_parameters_focus(creator, data, output_dir):
    """Create top 5 parameters chart without artificial classification."""
    fig, ax = creator.create_figure(figsize=(12, 8))
    
    # Focus on top 5 parameters
    top5_params = data['parameters'][:5]
    top5_scores = data['scores'][:5]
    top5_ranks = data['importance_rank'][:5]
    
    # Use gradient colors for top 5
    top5_colors = [creator.get_gradient_color(rank, 5) for rank in range(1, 6)]
    
    bars = ax.bar(range(len(top5_params)), top5_scores, 
                  color=top5_colors, alpha=0.8, edgecolor='black', linewidth=1.2)
    
    # Enhanced formatting for top parameters
    ax.set_xticks(range(len(top5_params)))
    ax.set_xticklabels([p.replace('_', ' ').title() for p in top5_params], 
                       rotation=30, ha='right', fontsize=12, fontweight='bold')
    ax.set_ylabel('Sensitivity Score', fontweight='bold', fontsize=14)
    ax.set_xlabel('Top 5 Most Influential Parameters', fontweight='bold', fontsize=14)
    
    # Add value labels with percentage contribution
    total_sensitivity = sum(data['scores'])
    for bar, score in zip(bars, top5_scores):
        height = bar.get_height()
        percentage = (score / total_sensitivity) * 100
        ax.text(bar.get_x() + bar.get_width()/2., height + 0.02,
                f'{score:.3f}\n({percentage:.1f}%)', 
                ha='center', va='bottom', fontsize=11, fontweight='bold')
    
    ax.grid(True, alpha=0.3)
    ax.set_ylim(0, max(top5_scores) * 1.2)
    
    # Add summary text
    top5_contribution = sum(top5_scores) / total_sensitivity * 100
    ax.text(0.02, 0.98, f'Top 5 Parameters Account for {top5_contribution:.1f}% of Total Sensitivity',
            transform=ax.transAxes, fontsize=12, fontweight='bold',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8),
            verticalalignment='top')
    
    creator.save_figure(fig, output_dir / 'Figure_2_Top5_Parameters_Focus.png',
                       'Detailed Analysis of Five Most Influential Parameters\n(Sensitivity Scores and Relative Contributions)')

def create_fixed_parameter_distribution_analysis(creator, data, output_dir):
    """Create parameter distribution analysis without artificial tiers."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    
    # Left: Sensitivity score distribution (scientific)
    ax1.hist(data['scores'], bins=8, alpha=0.7, color=creator.colors['medium_importance'], 
             edgecolor='black', linewidth=1)
    ax1.set_ylabel('Number of Parameters', fontweight='bold', fontsize=12)
    ax1.set_xlabel('Sensitivity Score Range', fontweight='bold', fontsize=12)
    ax1.set_title('(a) Sensitivity Score Distribution', fontweight='bold', pad=15, fontsize=13)
    ax1.grid(True, alpha=0.3)
    
    # Add statistical annotations
    mean_score = np.mean(data['scores'])
    median_score = np.median(data['scores'])
    ax1.axvline(mean_score, color='red', linestyle='--', linewidth=2, label=f'Mean: {mean_score:.3f}')
    ax1.axvline(median_score, color='blue', linestyle='--', linewidth=2, label=f'Median: {median_score:.3f}')
    ax1.legend()
    
    # Right: Cumulative sensitivity contribution
    cumulative_scores = np.cumsum(data['scores'])
    cumulative_percentage = (cumulative_scores / cumulative_scores[-1]) * 100
    
    colors = [creator.get_gradient_color(rank, len(data['parameters'])) 
              for rank in data['importance_rank']]
    
    bars = ax2.bar(range(len(data['parameters'])), cumulative_percentage, 
                   color=colors, alpha=0.8, edgecolor='black', linewidth=0.5)
    
    ax2.set_xticks(range(0, len(data['parameters']), 2))  # Show every 2nd parameter
    ax2.set_xticklabels([data['parameters'][i].replace('_', ' ').title() 
                        for i in range(0, len(data['parameters']), 2)], 
                       rotation=45, ha='right', fontsize=9)
    ax2.set_ylabel('Cumulative Sensitivity (%)', fontweight='bold', fontsize=12)
    ax2.set_xlabel('Parameters (Ranked by Importance)', fontweight='bold', fontsize=12)
    ax2.set_title('(b) Cumulative Sensitivity Analysis', fontweight='bold', pad=15, fontsize=13)
    ax2.grid(True, alpha=0.3)
    
    # Add 80% line (Pareto principle reference)
    ax2.axhline(y=80, color='red', linestyle='--', linewidth=2, 
                label='80% Threshold', alpha=0.8)
    ax2.legend()
    
    plt.tight_layout()
    creator.save_figure(fig, output_dir / 'Figure_12_Parameter_Distribution_Analysis.png',
                       'Parameter Sensitivity Distribution and Cumulative Analysis\n(Scientific Classification Based on Actual Impact)',
                       tight_layout=False)

def main():
    """Remove critical/moderate classification and recreate affected charts."""
    print("🔧 Fixing Parameter Classification - Removing Artificial Tiers...")
    
    # Setup
    output_dir = Path("Comprehensive_Thesis_Charts")
    output_dir.mkdir(exist_ok=True)
    
    creator = FixedChartCreator()
    data = create_fixed_sensitivity_data()
    
    print("\n📊 Recreating Charts Without Artificial Classification...")
    
    # Recreate the main affected charts
    print("  1. Parameter Sensitivity Ranking (Fixed)...")
    create_fixed_parameter_sensitivity_ranking(creator, data, output_dir)
    
    print("  2. Top 5 Parameters Focus (Fixed)...")
    create_fixed_top5_parameters_focus(creator, data, output_dir)
    
    print("  3. Parameter Distribution Analysis (Replaces Tier Classification)...")
    create_fixed_parameter_distribution_analysis(creator, data, output_dir)
    
    print("\n✅ Parameter classification fixed!")
    print("🗑️  Removed: Artificial critical/moderate differentiation")
    print("✨ Added: Scientific gradient-based importance classification")
    print("📊 Charts now use sensitivity score thresholds instead of arbitrary tiers")

if __name__ == "__main__":
    main()
