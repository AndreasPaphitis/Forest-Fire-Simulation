#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Sensitivity Analysis Visualization Module

This module creates high-quality publication-ready visualizations for sensitivity analysis results.
Generates interactive and static plots suitable for reports and presentations.

Author: Forest Fire Simulation Team
Date: 2025
Version: 1.0 - HPC Optimized
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import seaborn as sns
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime
import json

try:
    import plotly.graph_objects as go
    import plotly.express as px
    from plotly.subplots import make_subplots
    import plotly.offline as pyo
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

try:
    from src.utils.logging_utils import get_logger
except ImportError:
    try:
        from utils.logging_utils import get_logger
    except ImportError:
        import logging
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__)

logger = get_logger(__name__)


class SensitivityVisualizer:
    """
    Creates publication-quality visualizations for sensitivity analysis results.
    
    Supports both static (matplotlib/seaborn) and interactive (plotly) plots.
    """
    
    def __init__(self, 
                 sensitivity_results,
                 output_dir: Union[str, Path] = "sensitivity_visualizations",
                 style: str = "publication",
                 color_palette: str = "viridis",
                 interactive: bool = True):
        """
        Initialize the sensitivity visualizer.
        
        Args:
            sensitivity_results: SensitivityResults object from analysis
            output_dir: Directory to save visualization outputs
            style: Visualization style ('publication', 'presentation', 'paper')
            color_palette: Color palette to use ('viridis', 'plasma', 'tab10', 'Set2')
            interactive: Whether to create interactive plots (requires plotly)
        """
        self.results = sensitivity_results
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.style = style
        self.color_palette = color_palette
        self.interactive = interactive and PLOTLY_AVAILABLE
        
        if self.interactive and not PLOTLY_AVAILABLE:
            logger.warning("Plotly not available, falling back to static plots")
            self.interactive = False
        
        # Set up matplotlib style
        self._setup_matplotlib_style()
        
        # Prepare data for visualization
        self.df = self._prepare_dataframe()
        
        logger.info(f"Initialized sensitivity visualizer with {len(self.results.results)} parameters")
    
    def _setup_matplotlib_style(self):
        """Configure matplotlib for publication-quality plots."""
        if self.style == "publication":
            plt.style.use('seaborn-v0_8-whitegrid')
            plt.rcParams.update({
                'font.size': 12,
                'axes.titlesize': 14,
                'axes.labelsize': 12,
                'xtick.labelsize': 10,
                'ytick.labelsize': 10,
                'legend.fontsize': 10,
                'figure.titlesize': 16,
                'font.family': 'serif',
                'font.serif': ['Times New Roman', 'DejaVu Serif'],
                'axes.linewidth': 1.2,
                'grid.alpha': 0.3,
                'figure.dpi': 300,
                'savefig.dpi': 300,
                'savefig.bbox': 'tight',
                'savefig.pad_inches': 0.1
            })
        elif self.style == "presentation":
            plt.style.use('seaborn-v0_8-darkgrid')
            plt.rcParams.update({
                'font.size': 14,
                'axes.titlesize': 16,
                'axes.labelsize': 14,
                'xtick.labelsize': 12,
                'ytick.labelsize': 12,
                'legend.fontsize': 12,
                'figure.titlesize': 18,
                'font.family': 'sans-serif',
                'axes.linewidth': 1.5,
                'figure.dpi': 150,
                'savefig.dpi': 150
            })
    
    def _prepare_dataframe(self) -> pd.DataFrame:
        """Prepare pandas DataFrame for easier visualization."""
        data = []
        
        for result in self.results.results:
            if not result.is_valid:
                continue
                
            # Add main parameter data
            base_row = {
                'parameter_name': result.parameter_name,
                'sensitivity_index': result.sensitivity_index,
                'baseline_value': result.baseline_value,
                'is_baseline': True,
                'test_value': result.baseline_value,
                'objective_value': self.results.baseline_objective,
                'objective_change': 0.0,
                'relative_change': 0.0
            }
            data.append(base_row)
            
            # Add test point data
            for i, (test_val, obj_val, obj_change, rel_change) in enumerate(zip(
                result.test_values, result.objective_values, 
                result.objective_changes, result.relative_changes
            )):
                test_row = {
                    'parameter_name': result.parameter_name,
                    'sensitivity_index': result.sensitivity_index,
                    'baseline_value': result.baseline_value,
                    'is_baseline': False,
                    'test_value': test_val,
                    'objective_value': obj_val,
                    'objective_change': obj_change,
                    'relative_change': rel_change,
                    'test_point_index': i
                }
                data.append(test_row)
        
        return pd.DataFrame(data)
    
    def create_all_visualizations(self, formats: List[str] = ['png', 'pdf', 'html']) -> Dict[str, List[Path]]:
        """
        Create all 6 visualization types.
        
        Args:
            formats: List of output formats ('png', 'pdf', 'svg', 'html')
            
        Returns:
            Dictionary mapping visualization types to saved file paths
        """
        logger.info("🎨 Creating all sensitivity analysis visualizations...")
        
        saved_files = {}
        
        # 1. Parameter Sensitivity Bar Chart
        logger.info("📊 Creating parameter sensitivity bar chart...")
        files = self.plot_sensitivity_bar_chart(formats=formats)
        saved_files['sensitivity_bar_chart'] = files
        
        # 2. Parameter Correlation Heatmap
        logger.info("🔥 Creating parameter correlation heatmap...")
        files = self.plot_correlation_heatmap(formats=formats)
        saved_files['correlation_heatmap'] = files
        
        # 3. Sensitivity Distribution Plot
        logger.info("📈 Creating sensitivity distribution plot...")
        files = self.plot_sensitivity_distribution(formats=formats)
        saved_files['sensitivity_distribution'] = files
        
        # 4. Parameter Response Curves
        logger.info("📉 Creating parameter response curves...")
        files = self.plot_parameter_response_curves(formats=formats)
        saved_files['response_curves'] = files
        
        # 5. Ranking Comparison Plot
        logger.info("🏆 Creating ranking comparison plot...")
        files = self.plot_ranking_comparison(formats=formats)
        saved_files['ranking_comparison'] = files
        
        # 6. Parameter Space Visualization
        logger.info("🌌 Creating parameter space visualization...")
        files = self.plot_parameter_space(formats=formats)
        saved_files['parameter_space'] = files
        
        # Create summary dashboard (static version)
        logger.info("📋 Creating summary dashboard...")
        files = self.create_summary_dashboard(formats=formats)
        saved_files['summary_dashboard'] = files
        
        # Generate visualization report
        report_file = self.generate_visualization_report(saved_files)
        saved_files['report'] = [report_file]
        
        logger.info(f"✅ Created {len(saved_files)} visualization types with {sum(len(files) for files in saved_files.values())} total files")
        
        return saved_files
    
    def plot_sensitivity_bar_chart(self, formats: List[str] = ['png', 'html']) -> List[Path]:
        """
        1. Parameter Sensitivity Bar Chart
        Horizontal bar chart showing sensitivity indices for all parameters.
        """
        saved_files = []
        
        # Get parameter rankings
        rankings = self.results.parameter_rankings
        if not rankings:
            logger.warning("No parameter rankings available for bar chart")
            return saved_files
        
        param_names = [name for name, _ in rankings]
        sensitivity_values = [value for _, value in rankings]
        
        # Create static version with matplotlib
        fig, ax = plt.subplots(figsize=(10, max(6, len(param_names) * 0.5)))
        
        # Create horizontal bar chart
        bars = ax.barh(range(len(param_names)), sensitivity_values, 
                       color=plt.cm.get_cmap(self.color_palette)(np.linspace(0, 1, len(param_names))))
        
        # Customize the plot
        ax.set_yticks(range(len(param_names)))
        ax.set_yticklabels([name.replace('_', ' ').title() for name in param_names])
        ax.set_xlabel('Sensitivity Index', fontweight='bold')
        ax.set_title('Parameter Sensitivity Analysis\nRanked by Sensitivity Index', fontweight='bold', pad=20)
        
        # Add value labels on bars
        for i, (bar, value) in enumerate(zip(bars, sensitivity_values)):
            ax.text(value + max(sensitivity_values) * 0.01, bar.get_y() + bar.get_height()/2, 
                   f'{value:.3f}', va='center', fontweight='bold')
        
        # Add grid and styling
        ax.grid(axis='x', alpha=0.3)
        ax.set_axisbelow(True)
        
        plt.tight_layout()
        
        # Save static versions
        for fmt in formats:
            if fmt in ['png', 'pdf', 'svg']:
                filename = self.output_dir / f"sensitivity_bar_chart.{fmt}"
                plt.savefig(filename, format=fmt, bbox_inches='tight', dpi=300)
                saved_files.append(filename)
        
        plt.close()
        
        # Create interactive version if requested
        if self.interactive and 'html' in formats:
            fig_plotly = go.Figure()
            
            colors = px.colors.sample_colorscale(self.color_palette, len(param_names))
            
            fig_plotly.add_trace(go.Bar(
                x=sensitivity_values,
                y=[name.replace('_', ' ').title() for name in param_names],
                orientation='h',
                marker=dict(color=colors),
                text=[f'{val:.3f}' for val in sensitivity_values],
                textposition='outside',
                hovertemplate='<b>%{y}</b><br>Sensitivity: %{x:.4f}<extra></extra>'
            ))
            
            fig_plotly.update_layout(
                title={
                    'text': 'Parameter Sensitivity Analysis<br><sub>Ranked by Sensitivity Index</sub>',
                    'x': 0.5,
                    'xanchor': 'center',
                    'font': {'size': 18, 'family': 'Arial Black'}
                },
                xaxis_title='Sensitivity Index',
                yaxis_title='Parameters',
                height=max(400, len(param_names) * 50),
                template='plotly_white',
                font=dict(family="Arial", size=12),
                margin=dict(l=150, r=100, t=80, b=50)
            )
            
            filename = self.output_dir / "sensitivity_bar_chart.html"
            fig_plotly.write_html(filename)
            saved_files.append(filename)
        
        return saved_files
    
    def plot_correlation_heatmap(self, formats: List[str] = ['png', 'html']) -> List[Path]:
        """
        2. Parameter Correlation Heatmap
        Shows correlation between parameters and their sensitivity effects.
        """
        saved_files = []
        
        # Prepare correlation matrix data
        valid_results = [r for r in self.results.results if r.is_valid]
        if len(valid_results) < 2:
            logger.warning("Not enough valid results for correlation heatmap")
            return saved_files
        
        # Create matrix of parameter data
        param_names = [r.parameter_name for r in valid_results]
        sensitivity_indices = [r.sensitivity_index for r in valid_results]
        baseline_values = [r.baseline_value for r in valid_results]
        
        # Calculate correlation matrix
        data_matrix = np.array([
            sensitivity_indices,
            baseline_values,
            [np.mean(r.objective_changes) for r in valid_results],
            [np.std(r.objective_changes) for r in valid_results],
            [max(r.objective_changes) - min(r.objective_changes) for r in valid_results]
        ]).T
        
        corr_matrix = np.corrcoef(data_matrix.T)
        
        metric_names = ['Sensitivity Index', 'Baseline Value', 'Mean Obj Change', 
                       'Std Obj Change', 'Obj Change Range']
        
        # Create static heatmap
        fig, ax = plt.subplots(figsize=(10, 8))
        
        # Create heatmap
        im = ax.imshow(corr_matrix, cmap=self.color_palette, vmin=-1, vmax=1, aspect='auto')
        
        # Set ticks and labels
        ax.set_xticks(range(len(metric_names)))
        ax.set_yticks(range(len(metric_names)))
        ax.set_xticklabels(metric_names, rotation=45, ha='right')
        ax.set_yticklabels(metric_names)
        
        # Add correlation values to cells
        for i in range(len(metric_names)):
            for j in range(len(metric_names)):
                text = ax.text(j, i, f'{corr_matrix[i, j]:.2f}',
                             ha="center", va="center", 
                             color="white" if abs(corr_matrix[i, j]) > 0.5 else "black",
                             fontweight='bold')
        
        # Add colorbar
        cbar = plt.colorbar(im, ax=ax)
        cbar.set_label('Correlation Coefficient', rotation=270, labelpad=20, fontweight='bold')
        
        ax.set_title('Parameter Sensitivity Correlation Matrix', fontweight='bold', pad=20)
        plt.tight_layout()
        
        # Save static versions
        for fmt in formats:
            if fmt in ['png', 'pdf', 'svg']:
                filename = self.output_dir / f"correlation_heatmap.{fmt}"
                plt.savefig(filename, format=fmt, bbox_inches='tight', dpi=300)
                saved_files.append(filename)
        
        plt.close()
        
        # Create interactive version
        if self.interactive and 'html' in formats:
            fig_plotly = go.Figure(data=go.Heatmap(
                z=corr_matrix,
                x=metric_names,
                y=metric_names,
                colorscale=self.color_palette,
                zmin=-1, zmax=1,
                text=np.round(corr_matrix, 2),
                texttemplate="%{text}",
                textfont={"size": 12, "color": "white"},
                hovertemplate='<b>%{y}</b> vs <b>%{x}</b><br>Correlation: %{z:.3f}<extra></extra>'
            ))
            
            fig_plotly.update_layout(
                title={
                    'text': 'Parameter Sensitivity Correlation Matrix',
                    'x': 0.5,
                    'xanchor': 'center',
                    'font': {'size': 18, 'family': 'Arial Black'}
                },
                xaxis_title='Metrics',
                yaxis_title='Metrics',
                template='plotly_white',
                height=600,
                font=dict(family="Arial", size=12)
            )
            
            filename = self.output_dir / "correlation_heatmap.html"
            fig_plotly.write_html(filename)
            saved_files.append(filename)
        
        return saved_files
    
    def plot_sensitivity_distribution(self, formats: List[str] = ['png', 'html']) -> List[Path]:
        """
        3. Sensitivity Distribution Plot
        Box plot showing distribution of sensitivity values across parameters.
        """
        saved_files = []
        
        if self.df.empty:
            logger.warning("No data available for sensitivity distribution plot")
            return saved_files
        
        # Prepare data for plotting
        valid_df = self.df[self.df['parameter_name'].isin([r.parameter_name for r in self.results.results if r.is_valid])]
        
        # Create static version
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
        
        # Box plot of sensitivity indices
        sensitivity_data = [r.sensitivity_index for r in self.results.results if r.is_valid]
        param_names = [r.parameter_name for r in self.results.results if r.is_valid]
        
        bp1 = ax1.boxplot([sensitivity_data], labels=['All Parameters'], patch_artist=True)
        bp1['boxes'][0].set_facecolor(plt.cm.get_cmap(self.color_palette)(0.5))
        
        ax1.set_title('Sensitivity Index Distribution', fontweight='bold')
        ax1.set_ylabel('Sensitivity Index', fontweight='bold')
        ax1.grid(alpha=0.3)
        
        # Individual parameter sensitivity with error bars
        y_pos = np.arange(len(param_names))
        sensitivity_values = [r.sensitivity_index for r in self.results.results if r.is_valid]
        
        # Calculate error bars (standard deviation of objective changes)
        error_bars = [np.std(r.objective_changes) for r in self.results.results if r.is_valid]
        
        colors = plt.cm.get_cmap(self.color_palette)(np.linspace(0, 1, len(param_names)))
        bars = ax2.barh(y_pos, sensitivity_values, xerr=error_bars, 
                       color=colors, capsize=5, alpha=0.8)
        
        ax2.set_yticks(y_pos)
        ax2.set_yticklabels([name.replace('_', ' ').title() for name in param_names])
        ax2.set_xlabel('Sensitivity Index', fontweight='bold')
        ax2.set_title('Parameter Sensitivity with Uncertainty', fontweight='bold')
        ax2.grid(axis='x', alpha=0.3)
        
        plt.tight_layout()
        
        # Save static versions
        for fmt in formats:
            if fmt in ['png', 'pdf', 'svg']:
                filename = self.output_dir / f"sensitivity_distribution.{fmt}"
                plt.savefig(filename, format=fmt, bbox_inches='tight', dpi=300)
                saved_files.append(filename)
        
        plt.close()
        
        # Create interactive version
        if self.interactive and 'html' in formats:
            fig_plotly = make_subplots(
                rows=1, cols=2,
                subplot_titles=('Sensitivity Distribution', 'Parameter Sensitivity with Uncertainty'),
                horizontal_spacing=0.15
            )
            
            # Box plot
            fig_plotly.add_trace(
                go.Box(y=sensitivity_data, name='All Parameters', marker_color=px.colors.qualitative.Set3[0]),
                row=1, col=1
            )
            
            # Bar chart with error bars
            fig_plotly.add_trace(
                go.Bar(
                    x=sensitivity_values,
                    y=[name.replace('_', ' ').title() for name in param_names],
                    orientation='h',
                    error_x=dict(type='data', array=error_bars),
                    marker=dict(color=px.colors.sample_colorscale(self.color_palette, len(param_names))),
                    hovertemplate='<b>%{y}</b><br>Sensitivity: %{x:.4f}<br>Uncertainty: ±%{error_x.array:.4f}<extra></extra>'
                ),
                row=1, col=2
            )
            
            fig_plotly.update_layout(
                title={
                    'text': 'Parameter Sensitivity Distribution Analysis',
                    'x': 0.5,
                    'xanchor': 'center',
                    'font': {'size': 18, 'family': 'Arial Black'}
                },
                template='plotly_white',
                height=600,
                font=dict(family="Arial", size=12),
                showlegend=False
            )
            
            fig_plotly.update_xaxes(title_text='Sensitivity Index', row=1, col=1)
            fig_plotly.update_yaxes(title_text='Distribution', row=1, col=1)
            fig_plotly.update_xaxes(title_text='Sensitivity Index', row=1, col=2)
            fig_plotly.update_yaxes(title_text='Parameters', row=1, col=2)
            
            filename = self.output_dir / "sensitivity_distribution.html"
            fig_plotly.write_html(filename)
            saved_files.append(filename)
        
        return saved_files
    
    def plot_parameter_response_curves(self, formats: List[str] = ['png', 'html']) -> List[Path]:
        """
        4. Parameter Response Curves
        Line plots showing how objective varies with each parameter.
        """
        saved_files = []
        
        valid_results = [r for r in self.results.results if r.is_valid]
        if not valid_results:
            logger.warning("No valid results for response curves")
            return saved_files
        
        # Create static version with subplots
        n_params = len(valid_results)
        n_cols = min(3, n_params)
        n_rows = (n_params + n_cols - 1) // n_cols
        
        fig, axes = plt.subplots(n_rows, n_cols, figsize=(15, 5 * n_rows))
        if n_params == 1:
            axes = [axes]
        elif n_rows == 1:
            axes = axes.reshape(1, -1)
        axes = axes.flatten()
        
        for i, result in enumerate(valid_results):
            ax = axes[i]
            
            # Plot response curve
            all_values = [result.baseline_value] + result.test_values
            all_objectives = [self.results.baseline_objective] + result.objective_values
            
            # Sort by parameter value for smooth curve
            sorted_pairs = sorted(zip(all_values, all_objectives))
            sorted_values, sorted_objectives = zip(*sorted_pairs)
            
            # Plot line and points
            ax.plot(sorted_values, sorted_objectives, 'o-', linewidth=2, markersize=6,
                   color=plt.cm.get_cmap(self.color_palette)(i / max(n_params - 1, 1)))
            
            # Highlight baseline
            baseline_idx = all_values.index(result.baseline_value)
            ax.plot(result.baseline_value, self.results.baseline_objective, 'r*', 
                   markersize=12, label='Baseline')
            
            ax.set_xlabel(result.parameter_name.replace('_', ' ').title(), fontweight='bold')
            ax.set_ylabel('Objective Value', fontweight='bold')
            ax.set_title(f'Response: {result.parameter_name.replace("_", " ").title()}\n'
                        f'Sensitivity: {result.sensitivity_index:.3f}', fontweight='bold')
            ax.grid(alpha=0.3)
            ax.legend()
        
        # Hide empty subplots
        for i in range(n_params, len(axes)):
            axes[i].set_visible(False)
        
        plt.suptitle('Parameter Response Curves', fontsize=16, fontweight='bold', y=0.98)
        plt.tight_layout()
        
        # Save static versions
        for fmt in formats:
            if fmt in ['png', 'pdf', 'svg']:
                filename = self.output_dir / f"response_curves.{fmt}"
                plt.savefig(filename, format=fmt, bbox_inches='tight', dpi=300)
                saved_files.append(filename)
        
        plt.close()
        
        # Create interactive version
        if self.interactive and 'html' in formats:
            fig_plotly = make_subplots(
                rows=n_rows, cols=n_cols,
                subplot_titles=[r.parameter_name.replace('_', ' ').title() for r in valid_results],
                vertical_spacing=0.12,
                horizontal_spacing=0.1
            )
            
            for i, result in enumerate(valid_results):
                row = i // n_cols + 1
                col = i % n_cols + 1
                
                all_values = [result.baseline_value] + result.test_values
                all_objectives = [self.results.baseline_objective] + result.objective_values
                
                # Sort for smooth curve
                sorted_pairs = sorted(zip(all_values, all_objectives))
                sorted_values, sorted_objectives = zip(*sorted_pairs)
                
                # Add response curve
                fig_plotly.add_trace(
                    go.Scatter(
                        x=sorted_values,
                        y=sorted_objectives,
                        mode='lines+markers',
                        name=f'{result.parameter_name}',
                        line=dict(width=3),
                        marker=dict(size=8),
                        hovertemplate=f'<b>{result.parameter_name.replace("_", " ").title()}</b><br>' +
                                    'Value: %{x:.4f}<br>Objective: %{y:.4f}<extra></extra>',
                        showlegend=False
                    ),
                    row=row, col=col
                )
                
                # Add baseline point
                fig_plotly.add_trace(
                    go.Scatter(
                        x=[result.baseline_value],
                        y=[self.results.baseline_objective],
                        mode='markers',
                        marker=dict(symbol='star', size=15, color='red'),
                        name='Baseline',
                        hovertemplate='<b>Baseline</b><br>Value: %{x:.4f}<br>Objective: %{y:.4f}<extra></extra>',
                        showlegend=(i == 0)
                    ),
                    row=row, col=col
                )
            
            fig_plotly.update_layout(
                title={
                    'text': 'Parameter Response Curves<br><sub>Objective Function Response to Parameter Changes</sub>',
                    'x': 0.5,
                    'xanchor': 'center',
                    'font': {'size': 18, 'family': 'Arial Black'}
                },
                template='plotly_white',
                height=400 * n_rows,
                font=dict(family="Arial", size=12)
            )
            
            filename = self.output_dir / "response_curves.html"
            fig_plotly.write_html(filename)
            saved_files.append(filename)
        
        return saved_files
    
    def plot_ranking_comparison(self, formats: List[str] = ['png', 'html']) -> List[Path]:
        """
        5. Ranking Comparison Plot
        Comparison of parameter rankings across different sensitivity metrics.
        """
        saved_files = []
        
        valid_results = [r for r in self.results.results if r.is_valid]
        if not valid_results:
            logger.warning("No valid results for ranking comparison")
            return saved_files
        
        # Calculate different ranking metrics
        param_names = [r.parameter_name for r in valid_results]
        
        # Different ranking criteria
        sensitivity_rank = [i for i, (name, _) in enumerate(self.results.parameter_rankings) if name in param_names]
        
        # Mean absolute change ranking
        mean_changes = [np.mean(np.abs(r.objective_changes)) for r in valid_results]
        mean_change_rank = list(np.argsort(np.argsort(mean_changes))[::-1])
        
        # Maximum change ranking
        max_changes = [max(np.abs(r.objective_changes)) for r in valid_results]
        max_change_rank = list(np.argsort(np.argsort(max_changes))[::-1])
        
        # Variance ranking
        variances = [np.var(r.objective_changes) for r in valid_results]
        variance_rank = list(np.argsort(np.argsort(variances))[::-1])
        
        # Create static version
        fig, ax = plt.subplots(figsize=(12, 8))
        
        x = np.arange(len(param_names))
        width = 0.2
        
        ax.bar(x - 1.5*width, sensitivity_rank, width, label='Sensitivity Index', alpha=0.8)
        ax.bar(x - 0.5*width, mean_change_rank, width, label='Mean Change', alpha=0.8)
        ax.bar(x + 0.5*width, max_change_rank, width, label='Max Change', alpha=0.8)
        ax.bar(x + 1.5*width, variance_rank, width, label='Variance', alpha=0.8)
        
        ax.set_xlabel('Parameters', fontweight='bold')
        ax.set_ylabel('Rank (0 = Most Sensitive)', fontweight='bold')
        ax.set_title('Parameter Ranking Comparison\nAcross Different Sensitivity Metrics', fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels([name.replace('_', ' ').title() for name in param_names], rotation=45, ha='right')
        ax.legend()
        ax.grid(axis='y', alpha=0.3)
        
        plt.tight_layout()
        
        # Save static versions
        for fmt in formats:
            if fmt in ['png', 'pdf', 'svg']:
                filename = self.output_dir / f"ranking_comparison.{fmt}"
                plt.savefig(filename, format=fmt, bbox_inches='tight', dpi=300)
                saved_files.append(filename)
        
        plt.close()
        
        # Create interactive version
        if self.interactive and 'html' in formats:
            fig_plotly = go.Figure()
            
            param_names_clean = [name.replace('_', ' ').title() for name in param_names]
            
            fig_plotly.add_trace(go.Bar(
                x=param_names_clean,
                y=sensitivity_rank,
                name='Sensitivity Index',
                opacity=0.8,
                hovertemplate='<b>%{x}</b><br>Sensitivity Rank: %{y}<extra></extra>'
            ))
            
            fig_plotly.add_trace(go.Bar(
                x=param_names_clean,
                y=mean_change_rank,
                name='Mean Change',
                opacity=0.8,
                hovertemplate='<b>%{x}</b><br>Mean Change Rank: %{y}<extra></extra>'
            ))
            
            fig_plotly.add_trace(go.Bar(
                x=param_names_clean,
                y=max_change_rank,
                name='Max Change',
                opacity=0.8,
                hovertemplate='<b>%{x}</b><br>Max Change Rank: %{y}<extra></extra>'
            ))
            
            fig_plotly.add_trace(go.Bar(
                x=param_names_clean,
                y=variance_rank,
                name='Variance',
                opacity=0.8,
                hovertemplate='<b>%{x}</b><br>Variance Rank: %{y}<extra></extra>'
            ))
            
            fig_plotly.update_layout(
                title={
                    'text': 'Parameter Ranking Comparison<br><sub>Across Different Sensitivity Metrics</sub>',
                    'x': 0.5,
                    'xanchor': 'center',
                    'font': {'size': 18, 'family': 'Arial Black'}
                },
                xaxis_title='Parameters',
                yaxis_title='Rank (0 = Most Sensitive)',
                template='plotly_white',
                height=600,
                font=dict(family="Arial", size=12),
                barmode='group'
            )
            
            filename = self.output_dir / "ranking_comparison.html"
            fig_plotly.write_html(filename)
            saved_files.append(filename)
        
        return saved_files
    
    def plot_parameter_space(self, formats: List[str] = ['png', 'html']) -> List[Path]:
        """
        6. Parameter Space Visualization
        2D scatter plots showing relationships between parameters and sensitivity.
        """
        saved_files = []
        
        valid_results = [r for r in self.results.results if r.is_valid]
        if len(valid_results) < 2:
            logger.warning("Need at least 2 parameters for parameter space visualization")
            return saved_files
        
        # Prepare data
        param_names = [r.parameter_name for r in valid_results]
        baseline_values = [r.baseline_value for r in valid_results]
        sensitivity_indices = [r.sensitivity_index for r in valid_results]
        mean_changes = [np.mean(np.abs(r.objective_changes)) for r in valid_results]
        
        # Create static version with multiple scatter plots
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 12))
        
        # Plot 1: Baseline Value vs Sensitivity
        scatter1 = ax1.scatter(baseline_values, sensitivity_indices, 
                              c=range(len(param_names)), cmap=self.color_palette, 
                              s=100, alpha=0.7, edgecolors='black')
        ax1.set_xlabel('Baseline Parameter Value', fontweight='bold')
        ax1.set_ylabel('Sensitivity Index', fontweight='bold')
        ax1.set_title('Baseline Value vs Sensitivity', fontweight='bold')
        ax1.grid(alpha=0.3)
        
        # Add parameter labels
        for i, name in enumerate(param_names):
            ax1.annotate(name.replace('_', ' ').title(), 
                        (baseline_values[i], sensitivity_indices[i]),
                        xytext=(5, 5), textcoords='offset points', fontsize=8)
        
        # Plot 2: Mean Change vs Sensitivity
        ax2.scatter(mean_changes, sensitivity_indices, 
                   c=range(len(param_names)), cmap=self.color_palette, 
                   s=100, alpha=0.7, edgecolors='black')
        ax2.set_xlabel('Mean Absolute Change', fontweight='bold')
        ax2.set_ylabel('Sensitivity Index', fontweight='bold')
        ax2.set_title('Mean Change vs Sensitivity', fontweight='bold')
        ax2.grid(alpha=0.3)
        
        # Plot 3: Parameter Value Ranges
        ranges = [max(r.test_values) - min(r.test_values) for r in valid_results]
        ax3.scatter(ranges, sensitivity_indices, 
                   c=range(len(param_names)), cmap=self.color_palette, 
                   s=100, alpha=0.7, edgecolors='black')
        ax3.set_xlabel('Parameter Test Range', fontweight='bold')
        ax3.set_ylabel('Sensitivity Index', fontweight='bold')
        ax3.set_title('Test Range vs Sensitivity', fontweight='bold')
        ax3.grid(alpha=0.3)
        
        # Plot 4: Bubble chart (size = sensitivity)
        normalized_sensitivity = np.array(sensitivity_indices) / max(sensitivity_indices) * 500
        ax4.scatter(baseline_values, mean_changes, 
                   s=normalized_sensitivity, c=range(len(param_names)), 
                   cmap=self.color_palette, alpha=0.6, edgecolors='black')
        ax4.set_xlabel('Baseline Parameter Value', fontweight='bold')
        ax4.set_ylabel('Mean Absolute Change', fontweight='bold')
        ax4.set_title('Parameter Space Overview\n(Size = Sensitivity)', fontweight='bold')
        ax4.grid(alpha=0.3)
        
        plt.tight_layout()
        
        # Save static versions
        for fmt in formats:
            if fmt in ['png', 'pdf', 'svg']:
                filename = self.output_dir / f"parameter_space.{fmt}"
                plt.savefig(filename, format=fmt, bbox_inches='tight', dpi=300)
                saved_files.append(filename)
        
        plt.close()
        
        # Create interactive 3D version
        if self.interactive and 'html' in formats:
            fig_plotly = go.Figure()
            
            # 3D scatter plot
            fig_plotly.add_trace(go.Scatter3d(
                x=baseline_values,
                y=sensitivity_indices,
                z=mean_changes,
                mode='markers+text',
                text=[name.replace('_', ' ').title() for name in param_names],
                textposition='top center',
                marker=dict(
                    size=[s * 20 for s in sensitivity_indices],
                    color=sensitivity_indices,
                    colorscale=self.color_palette,
                    colorbar=dict(title="Sensitivity Index"),
                    opacity=0.8,
                    line=dict(color='black', width=1)
                ),
                hovertemplate='<b>%{text}</b><br>' +
                            'Baseline: %{x:.4f}<br>' +
                            'Sensitivity: %{y:.4f}<br>' +
                            'Mean Change: %{z:.4f}<extra></extra>'
            ))
            
            fig_plotly.update_layout(
                title={
                    'text': '3D Parameter Space Visualization<br><sub>Size and Color = Sensitivity Index</sub>',
                    'x': 0.5,
                    'xanchor': 'center',
                    'font': {'size': 18, 'family': 'Arial Black'}
                },
                scene=dict(
                    xaxis_title='Baseline Parameter Value',
                    yaxis_title='Sensitivity Index',
                    zaxis_title='Mean Absolute Change',
                    camera=dict(eye=dict(x=1.5, y=1.5, z=1.5))
                ),
                template='plotly_white',
                height=700,
                font=dict(family="Arial", size=12)
            )
            
            filename = self.output_dir / "parameter_space.html"
            fig_plotly.write_html(filename)
            saved_files.append(filename)
        
        return saved_files
    
    def create_summary_dashboard(self, formats: List[str] = ['png', 'html']) -> List[Path]:
        """
        Create a comprehensive summary dashboard with key insights.
        """
        saved_files = []
        
        # Create static dashboard
        fig = plt.figure(figsize=(20, 12))
        gs = fig.add_gridspec(3, 4, hspace=0.3, wspace=0.3)
        
        # Title
        fig.suptitle('Sensitivity Analysis Summary Dashboard', fontsize=24, fontweight='bold', y=0.95)
        
        # Top parameters bar chart (top-left)
        ax1 = fig.add_subplot(gs[0, :2])
        top_params = self.results.parameter_rankings[:5]
        if top_params:
            param_names = [name.replace('_', ' ').title() for name, _ in top_params]
            values = [value for _, value in top_params]
            bars = ax1.bar(param_names, values, color=plt.cm.get_cmap(self.color_palette)(np.linspace(0, 1, len(param_names))))
            ax1.set_title('Top 5 Most Sensitive Parameters', fontweight='bold', fontsize=14)
            ax1.set_ylabel('Sensitivity Index', fontweight='bold')
            plt.setp(ax1.get_xticklabels(), rotation=45, ha='right')
            
            # Add value labels
            for bar, value in zip(bars, values):
                ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(values) * 0.01,
                        f'{value:.3f}', ha='center', va='bottom', fontweight='bold')
        
        # Summary statistics (top-right)
        ax2 = fig.add_subplot(gs[0, 2:])
        ax2.axis('off')
        summary = self.results.get_sensitivity_summary()
        
        stats_text = f"""
        ANALYSIS SUMMARY
        
        Total Parameters: {summary.get('total_parameters', 'N/A')}
        Valid Results: {summary.get('valid_parameters', 'N/A')}
        
        Baseline Objective: {summary.get('baseline_objective', 0):.4f}
        
        Most Sensitive: {summary.get('most_sensitive', ['N/A', 0])[0].replace('_', ' ').title()}
        (Sensitivity: {summary.get('most_sensitive', ['N/A', 0])[1]:.3f})
        
        Least Sensitive: {summary.get('least_sensitive', ['N/A', 0])[0].replace('_', ' ').title()}
        (Sensitivity: {summary.get('least_sensitive', ['N/A', 0])[1]:.3f})
        
        Total Evaluations: {summary.get('total_evaluations', 'N/A')}
        Total Time: {summary.get('total_time', 0):.1f} seconds
        """
        
        ax2.text(0.05, 0.95, stats_text, transform=ax2.transAxes, fontsize=12,
                verticalalignment='top', fontfamily='monospace',
                bbox=dict(boxstyle="round,pad=0.5", facecolor="lightgray", alpha=0.8))
        
        # Sensitivity distribution (middle-left)
        ax3 = fig.add_subplot(gs[1, :2])
        valid_results = [r for r in self.results.results if r.is_valid]
        if valid_results:
            sensitivity_values = [r.sensitivity_index for r in valid_results]
            ax3.hist(sensitivity_values, bins=min(10, len(sensitivity_values)), 
                    alpha=0.7, color=plt.cm.get_cmap(self.color_palette)(0.5), edgecolor='black')
            ax3.set_title('Sensitivity Index Distribution', fontweight='bold', fontsize=14)
            ax3.set_xlabel('Sensitivity Index', fontweight='bold')
            ax3.set_ylabel('Frequency', fontweight='bold')
            ax3.grid(alpha=0.3)
        
        # Parameter comparison (middle-right)
        ax4 = fig.add_subplot(gs[1, 2:])
        if len(valid_results) >= 2:
            param_names = [r.parameter_name.replace('_', ' ').title() for r in valid_results]
            baseline_values = [r.baseline_value for r in valid_results]
            sensitivity_indices = [r.sensitivity_index for r in valid_results]
            
            scatter = ax4.scatter(baseline_values, sensitivity_indices, 
                                s=100, alpha=0.7, 
                                c=range(len(param_names)), cmap=self.color_palette,
                                edgecolors='black')
            ax4.set_xlabel('Baseline Parameter Value', fontweight='bold')
            ax4.set_ylabel('Sensitivity Index', fontweight='bold')
            ax4.set_title('Baseline vs Sensitivity', fontweight='bold', fontsize=14)
            ax4.grid(alpha=0.3)
        
        # Key insights (bottom)
        ax5 = fig.add_subplot(gs[2, :])
        ax5.axis('off')
        
        # Generate insights
        insights = self._generate_insights()
        insights_text = "KEY INSIGHTS:\n\n" + "\n".join(f"• {insight}" for insight in insights)
        
        ax5.text(0.05, 0.95, insights_text, transform=ax5.transAxes, fontsize=12,
                verticalalignment='top', fontweight='bold',
                bbox=dict(boxstyle="round,pad=0.5", facecolor="lightyellow", alpha=0.8))
        
        # Save static versions
        for fmt in formats:
            if fmt in ['png', 'pdf', 'svg']:
                filename = self.output_dir / f"summary_dashboard.{fmt}"
                plt.savefig(filename, format=fmt, bbox_inches='tight', dpi=300)
                saved_files.append(filename)
        
        plt.close()
        
        # Interactive dashboard (simplified version)
        if self.interactive and 'html' in formats:
            # Create a multi-panel interactive dashboard
            fig_plotly = make_subplots(
                rows=2, cols=2,
                subplot_titles=('Top Sensitive Parameters', 'Sensitivity Distribution',
                               'Parameter Comparison', 'Response Overview'),
                specs=[[{"type": "bar"}, {"type": "histogram"}],
                      [{"type": "scatter"}, {"type": "scatter"}]],
                vertical_spacing=0.15,
                horizontal_spacing=0.15
            )
            
            # Top parameters bar chart
            if top_params:
                param_names_clean = [name.replace('_', ' ').title() for name, _ in top_params]
                values = [value for _, value in top_params]
                
                fig_plotly.add_trace(
                    go.Bar(x=param_names_clean, y=values, name='Sensitivity',
                          marker_color=px.colors.sample_colorscale(self.color_palette, len(param_names_clean))),
                    row=1, col=1
                )
            
            # Sensitivity distribution
            if valid_results:
                sensitivity_values = [r.sensitivity_index for r in valid_results]
                fig_plotly.add_trace(
                    go.Histogram(x=sensitivity_values, name='Distribution', nbinsx=10),
                    row=1, col=2
                )
            
            # Parameter comparison
            if len(valid_results) >= 2:
                param_names = [r.parameter_name.replace('_', ' ').title() for r in valid_results]
                baseline_values = [r.baseline_value for r in valid_results]
                sensitivity_indices = [r.sensitivity_index for r in valid_results]
                
                fig_plotly.add_trace(
                    go.Scatter(x=baseline_values, y=sensitivity_indices, 
                             mode='markers+text', text=param_names,
                             marker=dict(size=10, color=sensitivity_indices, 
                                       colorscale=self.color_palette)),
                    row=2, col=1
                )
            
            # Response overview (top 3 parameters)
            if len(valid_results) >= 3:
                for i, result in enumerate(valid_results[:3]):
                    all_values = [result.baseline_value] + result.test_values
                    all_objectives = [self.results.baseline_objective] + result.objective_values
                    
                    fig_plotly.add_trace(
                        go.Scatter(x=all_values, y=all_objectives, 
                                 mode='lines+markers', 
                                 name=result.parameter_name.replace('_', ' ').title()),
                        row=2, col=2
                    )
            
            fig_plotly.update_layout(
                title={
                    'text': 'Interactive Sensitivity Analysis Dashboard',
                    'x': 0.5,
                    'xanchor': 'center',
                    'font': {'size': 20, 'family': 'Arial Black'}
                },
                template='plotly_white',
                height=800,
                font=dict(family="Arial", size=12),
                showlegend=True
            )
            
            filename = self.output_dir / "summary_dashboard.html"
            fig_plotly.write_html(filename)
            saved_files.append(filename)
        
        return saved_files
    
    def _generate_insights(self) -> List[str]:
        """Generate key insights from the sensitivity analysis."""
        insights = []
        
        valid_results = [r for r in self.results.results if r.is_valid]
        if not valid_results:
            return ["No valid results available for insights generation."]
        
        # Most and least sensitive parameters
        if self.results.parameter_rankings:
            most_sensitive = self.results.parameter_rankings[0]
            least_sensitive = self.results.parameter_rankings[-1]
            
            insights.append(f"'{most_sensitive[0].replace('_', ' ').title()}' is the most sensitive parameter (index: {most_sensitive[1]:.3f})")
            insights.append(f"'{least_sensitive[0].replace('_', ' ').title()}' is the least sensitive parameter (index: {least_sensitive[1]:.3f})")
        
        # Sensitivity range
        sensitivity_values = [r.sensitivity_index for r in valid_results]
        sensitivity_range = max(sensitivity_values) - min(sensitivity_values)
        insights.append(f"Sensitivity indices range from {min(sensitivity_values):.3f} to {max(sensitivity_values):.3f} (range: {sensitivity_range:.3f})")
        
        # High vs low sensitivity groups
        median_sensitivity = np.median(sensitivity_values)
        high_sensitivity_count = sum(1 for s in sensitivity_values if s > median_sensitivity)
        insights.append(f"{high_sensitivity_count} out of {len(valid_results)} parameters show above-median sensitivity")
        
        # Objective impact
        all_changes = []
        for result in valid_results:
            all_changes.extend(np.abs(result.objective_changes))
        
        if all_changes:
            max_impact = max(all_changes)
            insights.append(f"Maximum objective change observed: {max_impact:.4f}")
        
        # Performance insights
        summary = self.results.get_sensitivity_summary()
        total_time = summary.get('total_time', 0)
        total_evals = summary.get('total_evaluations', 0)
        if total_time > 0 and total_evals > 0:
            evals_per_sec = total_evals / total_time
            insights.append(f"Analysis completed {total_evals} evaluations in {total_time:.1f}s ({evals_per_sec:.1f} eval/s)")
        
        return insights
    
    def generate_visualization_report(self, saved_files: Dict[str, List[Path]]) -> Path:
        """Generate an HTML report summarizing all visualizations."""
        
        # Create HTML report
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Sensitivity Analysis Visualization Report</title>
    <style>
        body {{ 
            font-family: Arial, sans-serif; 
            margin: 40px; 
            background-color: #f8f9fa;
        }}
        .header {{ 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px; 
            border-radius: 10px; 
            margin-bottom: 30px;
            text-align: center;
        }}
        .section {{ 
            background: white;
            margin: 20px 0; 
            padding: 25px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .visualization-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }}
        .viz-card {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            border-left: 4px solid #667eea;
        }}
        .viz-card h3 {{
            margin-top: 0;
            color: #333;
        }}
        .file-list {{
            background: #e9ecef;
            padding: 10px;
            border-radius: 5px;
            font-family: monospace;
            font-size: 12px;
        }}
        .metric {{ 
            display: inline-block; 
            margin: 10px; 
            padding: 15px; 
            background: linear-gradient(45deg, #f093fb 0%, #f5576c 100%);
            color: white;
            border-radius: 8px; 
            font-weight: bold;
            min-width: 120px;
            text-align: center;
        }}
        .insights {{
            background: linear-gradient(45deg, #4facfe 0%, #00f2fe 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            margin: 20px 0;
        }}
        .footer {{
            text-align: center;
            margin-top: 40px;
            padding: 20px;
            background: #6c757d;
            color: white;
            border-radius: 10px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🔥 Forest Fire Sensitivity Analysis</h1>
        <h2>Visualization Report</h2>
        <p>Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
    </div>
    """
        
        # Add summary metrics
        summary = self.results.get_sensitivity_summary()
        html_content += f"""
    <div class="section">
        <h2>📊 Analysis Summary</h2>
        <div class="metric">Parameters: {summary.get('total_parameters', 'N/A')}</div>
        <div class="metric">Valid Results: {summary.get('valid_parameters', 'N/A')}</div>
        <div class="metric">Baseline Objective: {summary.get('baseline_objective', 0):.4f}</div>
        <div class="metric">Evaluations: {summary.get('total_evaluations', 'N/A')}</div>
        <div class="metric">Time: {summary.get('total_time', 0):.1f}s</div>
    </div>
        """
        
        # Add insights
        insights = self._generate_insights()
        html_content += f"""
    <div class="insights">
        <h2>🧠 Key Insights</h2>
        <ul>
        {"".join(f"<li>{insight}</li>" for insight in insights)}
        </ul>
    </div>
        """
        
        # Add visualizations section
        html_content += """
    <div class="section">
        <h2>🎨 Generated Visualizations</h2>
        <p>The following visualizations have been created to analyze parameter sensitivity:</p>
        
        <div class="visualization-grid">
        """
        
        viz_descriptions = {
            'sensitivity_bar_chart': {
                'title': '📊 Parameter Sensitivity Bar Chart',
                'description': 'Horizontal bar chart ranking all parameters by their sensitivity indices. Shows which parameters have the most impact on model behavior.'
            },
            'correlation_heatmap': {
                'title': '🔥 Parameter Correlation Heatmap', 
                'description': 'Correlation matrix showing relationships between parameter sensitivity, baseline values, and objective changes.'
            },
            'sensitivity_distribution': {
                'title': '📈 Sensitivity Distribution Plot',
                'description': 'Box plots and distributions showing the spread of sensitivity values across parameters with uncertainty bars.'
            },
            'response_curves': {
                'title': '📉 Parameter Response Curves',
                'description': 'Line plots showing how the objective function responds to changes in each parameter value around the baseline.'
            },
            'ranking_comparison': {
                'title': '🏆 Ranking Comparison Plot',
                'description': 'Comparison of parameter rankings across different sensitivity metrics (sensitivity index, mean change, max change, variance).'
            },
            'parameter_space': {
                'title': '🌌 Parameter Space Visualization',
                'description': '2D/3D scatter plots exploring relationships between parameter values, sensitivity indices, and objective changes.'
            },
            'summary_dashboard': {
                'title': '📋 Summary Dashboard',
                'description': 'Comprehensive overview combining key metrics, distributions, and insights in a single dashboard view.'
            }
        }
        
        for viz_type, files in saved_files.items():
            if viz_type == 'report':
                continue
                
            viz_info = viz_descriptions.get(viz_type, {
                'title': viz_type.replace('_', ' ').title(),
                'description': f'Visualization showing {viz_type.replace("_", " ")}'
            })
            
            html_content += f"""
        <div class="viz-card">
            <h3>{viz_info['title']}</h3>
            <p>{viz_info['description']}</p>
            <div class="file-list">
                <strong>Generated files:</strong><br>
                {chr(10).join(f"• {file.name}" for file in files)}
            </div>
        </div>
            """
        
        html_content += """
        </div>
    </div>
        """
        
        # Add usage instructions
        html_content += f"""
    <div class="section">
        <h2>📖 Usage Instructions</h2>
        <h3>Static Visualizations (PNG/PDF/SVG)</h3>
        <ul>
            <li><strong>PNG files:</strong> High-resolution images suitable for presentations and documents</li>
            <li><strong>PDF files:</strong> Vector graphics perfect for publication and printing</li>
            <li><strong>SVG files:</strong> Scalable vector graphics for web use and further editing</li>
        </ul>
        
        <h3>Interactive Visualizations (HTML)</h3>
        <ul>
            <li><strong>HTML files:</strong> Interactive plots with hover tooltips, zoom, and pan capabilities</li>
            <li>Open HTML files in any web browser for interactive exploration</li>
            <li>Use zoom, pan, and hover features to explore data in detail</li>
        </ul>
        
        <h3>Interpretation Guidelines</h3>
        <ul>
            <li><strong>Sensitivity Index:</strong> Higher values indicate parameters with greater impact on model behavior</li>
            <li><strong>Response Curves:</strong> Steep slopes indicate high sensitivity to parameter changes</li>
            <li><strong>Correlation Analysis:</strong> Identifies relationships between parameter properties and sensitivity</li>
            <li><strong>Ranking Comparison:</strong> Validates sensitivity rankings across different metrics</li>
        </ul>
    </div>
        """
        
        # Add technical details
        html_content += f"""
    <div class="section">
        <h2>🔧 Technical Details</h2>
        <ul>
            <li><strong>Analysis Method:</strong> {self.results.analysis_metadata.get('method', 'Range-based sensitivity analysis')}</li>
            <li><strong>Total Parameters Analyzed:</strong> {len(self.results.results)}</li>
            <li><strong>Valid Results:</strong> {len([r for r in self.results.results if r.is_valid])}</li>
            <li><strong>Baseline Objective Value:</strong> {self.results.baseline_objective:.6f}</li>
            <li><strong>Visualization Style:</strong> {self.style}</li>
            <li><strong>Color Palette:</strong> {self.color_palette}</li>
            <li><strong>Interactive Features:</strong> {'Enabled (Plotly)' if self.interactive else 'Disabled (Static only)'}</li>
        </ul>
    </div>
        """
        
        # Footer
        html_content += """
    <div class="footer">
        <p><strong>Forest Fire Simulation - Sensitivity Analysis Visualization Report</strong></p>
        <p>Generated by HPC-Optimized Sensitivity Analysis Framework</p>
    </div>
</body>
</html>
        """
        
        # Save report
        report_file = self.output_dir / "visualization_report.html"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info(f"Generated visualization report: {report_file}")
        return report_file


def create_sensitivity_visualizations(sensitivity_results, 
                                    output_dir: Union[str, Path] = "sensitivity_visualizations",
                                    style: str = "publication",
                                    formats: List[str] = ['png', 'pdf', 'html']) -> Dict[str, List[Path]]:
    """
    Convenience function to create all sensitivity analysis visualizations.
    
    Args:
        sensitivity_results: SensitivityResults object from analysis
        output_dir: Directory to save visualizations
        style: Visualization style ('publication', 'presentation', 'paper')
        formats: Output formats to generate
        
    Returns:
        Dictionary mapping visualization types to saved file paths
    """
    visualizer = SensitivityVisualizer(
        sensitivity_results=sensitivity_results,
        output_dir=output_dir,
        style=style,
        interactive=('html' in formats)
    )
    
    return visualizer.create_all_visualizations(formats=formats)


if __name__ == "__main__":
    print("Sensitivity Analysis Visualization Module")
    print("=" * 60)
    print("This module creates publication-quality visualizations for sensitivity analysis results.")
    print("\nAvailable visualizations:")
    print("1. 📊 Parameter Sensitivity Bar Chart")
    print("2. 🔥 Parameter Correlation Heatmap")
    print("3. 📈 Sensitivity Distribution Plot") 
    print("4. 📉 Parameter Response Curves")
    print("5. 🏆 Ranking Comparison Plot")
    print("6. 🌌 Parameter Space Visualization")
    print("7. 📋 Summary Dashboard")
    print("\nSupported formats: PNG, PDF, SVG, HTML (interactive)")
    print("Usage: Import and call create_sensitivity_visualizations() with your results") 