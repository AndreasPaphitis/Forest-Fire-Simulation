#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Calibration Utilities Module

This module provides utility functions for calibration operations including
data loading, result saving, report generation, and configuration validation.

Author: Forest Fire Simulation Team
Date: 2025
Version: 1.0
"""

import os
import json
import pickle
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Tuple
import numpy as np

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


def load_historical_fire_data(file_path: Union[str, Path], 
                             data_format: str = 'auto') -> Dict[str, Any]:
    """
    Load historical fire data from various formats.
    
    Args:
        file_path: Path to the fire data file
        data_format: Format of the data ('geotiff', 'shapefile', 'numpy', 'auto')
        
    Returns:
        Dictionary containing fire perimeter and metadata
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        raise FileNotFoundError(f"Fire data file not found: {file_path}")
    
    # Auto-detect format if not specified
    if data_format == 'auto':
        suffix = file_path.suffix.lower()
        if suffix in ['.tif', '.tiff']:
            data_format = 'geotiff'
        elif suffix in ['.shp']:
            data_format = 'shapefile'
        elif suffix in ['.npy']:
            data_format = 'numpy'
        elif suffix in ['.json']:
            data_format = 'json'
        else:
            raise ValueError(f"Cannot auto-detect format for file: {file_path}")
    
    logger.info(f"Loading fire data from {file_path} (format: {data_format})")
    
    try:
        if data_format == 'geotiff':
            return _load_geotiff_fire_data(file_path)
        elif data_format == 'shapefile':
            return _load_shapefile_fire_data(file_path)
        elif data_format == 'numpy':
            return _load_numpy_fire_data(file_path)
        elif data_format == 'json':
            return _load_json_fire_data(file_path)
        else:
            raise ValueError(f"Unsupported data format: {data_format}")
            
    except Exception as e:
        logger.error(f"Failed to load fire data: {e}")
        raise


def _load_geotiff_fire_data(file_path: Path) -> Dict[str, Any]:
    """Load fire data from GeoTIFF format."""
    try:
        from osgeo import gdal
        import numpy as np
        
        gdal.UseExceptions()
        dataset = gdal.Open(str(file_path))
        
        if dataset is None:
            raise ValueError(f"Could not open GeoTIFF file: {file_path}")
        
        # Read the raster data
        band = dataset.GetRasterBand(1)
        fire_perimeter = band.ReadAsArray()
        
        # Get geospatial information
        geotransform = dataset.GetGeoTransform()
        projection = dataset.GetProjection()
        
        # Convert to binary (assume non-zero values are burned)
        fire_binary = (fire_perimeter > 0).astype(np.uint8)
        
        return {
            'fire_perimeter': fire_binary,
            'original_data': fire_perimeter,
            'geotransform': geotransform,
            'projection': projection,
            'file_path': str(file_path),
            'format': 'geotiff',
            'shape': fire_binary.shape,
            'burned_cells': np.sum(fire_binary),
            'total_cells': fire_binary.size
        }
        
    except ImportError:
        logger.error("GDAL not available for GeoTIFF loading")
        raise ImportError("GDAL is required to load GeoTIFF files")


def _load_shapefile_fire_data(file_path: Path) -> Dict[str, Any]:
    """Load fire data from shapefile format."""
    try:
        import geopandas as gpd
        from rasterio.features import rasterize
        from rasterio.transform import from_bounds
        
        # Read shapefile
        gdf = gpd.read_file(str(file_path))
        
        if gdf.empty:
            raise ValueError(f"Empty shapefile: {file_path}")
        
        # Get bounds and create transform
        bounds = gdf.total_bounds
        
        # Create a reasonable resolution (adjust as needed)
        resolution = 100  # meters per pixel
        width = int((bounds[2] - bounds[0]) / resolution)
        height = int((bounds[3] - bounds[1]) / resolution)
        
        transform = from_bounds(bounds[0], bounds[1], bounds[2], bounds[3], width, height)
        
        # Rasterize the geometries
        shapes = [(geom, 1) for geom in gdf.geometry]
        fire_perimeter = rasterize(shapes, out_shape=(height, width), transform=transform)
        
        return {
            'fire_perimeter': fire_perimeter,
            'bounds': bounds,
            'transform': transform,
            'resolution': resolution,
            'file_path': str(file_path),
            'format': 'shapefile',
            'shape': fire_perimeter.shape,
            'burned_cells': np.sum(fire_perimeter),
            'total_cells': fire_perimeter.size,
            'num_features': len(gdf)
        }
        
    except ImportError:
        logger.error("GeoPandas/Rasterio not available for shapefile loading")
        raise ImportError("GeoPandas and Rasterio are required to load shapefiles")


def _load_numpy_fire_data(file_path: Path) -> Dict[str, Any]:
    """Load fire data from numpy array format."""
    fire_perimeter = np.load(str(file_path))
    
    # Ensure binary format
    if fire_perimeter.dtype != bool and fire_perimeter.dtype != np.uint8:
        fire_perimeter = (fire_perimeter > 0).astype(np.uint8)
    
    return {
        'fire_perimeter': fire_perimeter,
        'file_path': str(file_path),
        'format': 'numpy',
        'shape': fire_perimeter.shape,
        'burned_cells': np.sum(fire_perimeter),
        'total_cells': fire_perimeter.size
    }


def _load_json_fire_data(file_path: Path) -> Dict[str, Any]:
    """Load fire data from JSON format."""
    with open(file_path, 'r') as f:
        data = json.load(f)
    
    # Expect fire_perimeter as nested list
    if 'fire_perimeter' not in data:
        raise ValueError("JSON file must contain 'fire_perimeter' field")
    
    fire_perimeter = np.array(data['fire_perimeter'])
    
    result = {
        'fire_perimeter': fire_perimeter,
        'file_path': str(file_path),
        'format': 'json',
        'shape': fire_perimeter.shape,
        'burned_cells': np.sum(fire_perimeter),
        'total_cells': fire_perimeter.size
    }
    
    # Add any additional metadata from JSON
    for key, value in data.items():
        if key != 'fire_perimeter':
            result[key] = value
    
    return result


def save_calibration_results(results: Any, 
                           output_dir: Union[str, Path],
                           experiment_name: str = "calibration",
                           save_formats: List[str] = ['json', 'pickle']) -> Dict[str, Path]:
    """
    Save calibration results in multiple formats.
    
    Args:
        results: Calibration results object
        output_dir: Directory to save results
        experiment_name: Name for the experiment files
        save_formats: List of formats to save ('json', 'pickle', 'csv')
        
    Returns:
        Dictionary mapping format names to saved file paths
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_filename = f"{experiment_name}_{timestamp}"
    
    saved_files = {}
    
    for format_name in save_formats:
        try:
            if format_name == 'json':
                file_path = output_dir / f"{base_filename}.json"
                if hasattr(results, 'save_results'):
                    results.save_results(file_path)
                else:
                    # Generic JSON saving
                    with open(file_path, 'w') as f:
                        json.dump(_convert_to_serializable(results), f, indent=2)
                saved_files['json'] = file_path
                
            elif format_name == 'pickle':
                file_path = output_dir / f"{base_filename}.pkl"
                with open(file_path, 'wb') as f:
                    pickle.dump(results, f)
                saved_files['pickle'] = file_path
                
            elif format_name == 'csv':
                file_path = output_dir / f"{base_filename}.csv"
                _save_results_as_csv(results, file_path)
                saved_files['csv'] = file_path
                
            else:
                logger.warning(f"Unknown save format: {format_name}")
                
        except Exception as e:
            logger.error(f"Failed to save results in {format_name} format: {e}")
    
    logger.info(f"Saved calibration results to {len(saved_files)} files in {output_dir}")
    return saved_files


def _convert_to_serializable(obj: Any) -> Any:
    """Convert object to JSON-serializable format."""
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, dict):
        return {key: _convert_to_serializable(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [_convert_to_serializable(item) for item in obj]
    elif hasattr(obj, '__dict__'):
        return _convert_to_serializable(obj.__dict__)
    else:
        return obj


def _save_results_as_csv(results: Any, file_path: Path) -> None:
    """Save calibration results as CSV format."""
    try:
        import pandas as pd
        
        # Extract results data
        if hasattr(results, 'results') and hasattr(results.results[0], 'parameter_values'):
            # Grid search results format
            data_rows = []
            for result in results.results:
                row = result.parameter_values.copy()
                row['objective_value'] = result.objective_value
                row['is_valid'] = result.is_valid
                row['evaluation_time'] = result.evaluation_time
                
                # Add objective components
                for comp_name, comp_value in result.objective_components.items():
                    row[f"obj_{comp_name}"] = comp_value
                
                data_rows.append(row)
            
            df = pd.DataFrame(data_rows)
            df.to_csv(file_path, index=False)
            
        else:
            logger.warning("Results format not suitable for CSV export")
            
    except ImportError:
        logger.warning("Pandas not available for CSV export")


def create_calibration_report(results: Any, 
                            config: Any,
                            output_dir: Union[str, Path],
                            include_plots: bool = True) -> Path:
    """
    Create a comprehensive calibration report.
    
    Args:
        results: Calibration results
        config: Calibration configuration
        output_dir: Directory to save the report
        include_plots: Whether to include plots in the report
        
    Returns:
        Path to the generated report file
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = output_dir / f"calibration_report_{timestamp}.html"
    
    # Generate report content
    html_content = _generate_html_report(results, config, include_plots)
    
    # Save report
    with open(report_file, 'w') as f:
        f.write(html_content)
    
    logger.info(f"Created calibration report: {report_file}")
    return report_file


def _generate_html_report(results: Any, config: Any, include_plots: bool) -> str:
    """Generate HTML content for calibration report."""
    
    # Basic report structure
    html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Fire Simulation Calibration Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        .header {{ background-color: #f5f5f5; padding: 20px; border-radius: 5px; }}
        .section {{ margin: 20px 0; }}
        .metric {{ display: inline-block; margin: 10px; padding: 10px; background-color: #e9e9e9; border-radius: 3px; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        .code {{ background-color: #f8f8f8; padding: 10px; border-radius: 3px; font-family: monospace; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Forest Fire Simulation Calibration Report</h1>
        <p>Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
        <p>Experiment: {getattr(config, 'experiment_name', 'Unknown')}</p>
    </div>
    """
    
    # Add experiment overview
    html += _generate_experiment_overview(config)
    
    # Add results summary
    html += _generate_results_summary(results)
    
    # Add parameter analysis
    html += _generate_parameter_analysis(results)
    
    # Add best configuration
    html += _generate_best_configuration(results)
    
    # Add plots if requested
    if include_plots:
        html += _generate_plots_section(results)
    
    # Close HTML
    html += """
</body>
</html>
"""
    
    return html


def _generate_experiment_overview(config: Any) -> str:
    """Generate experiment overview section."""
    return f"""
    <div class="section">
        <h2>Experiment Overview</h2>
        <div class="metric">Method: {getattr(config, 'method', 'Unknown')}</div>
        <div class="metric">Objective: {getattr(config, 'objective', 'Unknown')}</div>
        <div class="metric">Parameters: {len(getattr(config, 'calibration_parameters', []))}</div>
        <div class="metric">Max Iterations: {getattr(config, 'max_iterations', 'Unknown')}</div>
    </div>
    """


def _generate_results_summary(results: Any) -> str:
    """Generate results summary section."""
    best_value = results.get_best_objective_value() if hasattr(results, 'get_best_objective_value') else None
    if best_value is None:
        best_value = 'Unknown'
    total_evals = getattr(results, 'total_evaluations', 'Unknown')
    success_rate = 'Unknown'
    
    if hasattr(results, 'successful_evaluations') and hasattr(results, 'total_evaluations'):
        if results.total_evaluations > 0:
            success_rate = f"{results.successful_evaluations / results.total_evaluations * 100:.1f}%"
    
    return f"""
    <div class="section">
        <h2>Results Summary</h2>
        <div class="metric">Best Objective: {best_value}</div>
        <div class="metric">Total Evaluations: {total_evals}</div>
        <div class="metric">Success Rate: {success_rate}</div>
        <div class="metric">Total Time: {getattr(results, 'total_time', 'Unknown')} seconds</div>
    </div>
    """


def _generate_parameter_analysis(results: Any) -> str:
    """Generate parameter analysis section."""
    html = """
    <div class="section">
        <h2>Parameter Analysis</h2>
    """
    
    if hasattr(results, 'get_parameter_sensitivity'):
        sensitivity = results.get_parameter_sensitivity()
        
        html += """
        <h3>Parameter Sensitivity</h3>
        <table>
            <tr><th>Parameter</th><th>Correlation</th><th>Sensitivity Score</th></tr>
        """
        
        for param_name, sensitivity_data in sensitivity.items():
            correlation = sensitivity_data.get('correlation', 0.0)
            score = sensitivity_data.get('sensitivity_score', 0.0)
            html += f"<tr><td>{param_name}</td><td>{correlation:.3f}</td><td>{score:.3f}</td></tr>"
        
        html += "</table>"
    
    html += "</div>"
    return html


def _generate_best_configuration(results: Any) -> str:
    """Generate best configuration section."""
    html = """
    <div class="section">
        <h2>Best Configuration</h2>
    """
    
    best_params = results.get_best_parameters() if hasattr(results, 'get_best_parameters') else None
    
    if best_params:
        html += "<div class='code'>"
        for param_name, param_value in best_params.items():
            html += f"{param_name}: {param_value:.4f}<br>"
        html += "</div>"
    else:
        html += "<p>No valid configuration found.</p>"
    
    html += "</div>"
    return html


def _generate_plots_section(results: Any) -> str:
    """Generate plots section (placeholder for future implementation)."""
    return """
    <div class="section">
        <h2>Visualization</h2>
        <p><em>Plots will be generated in future versions.</em></p>
        <p>Recommended plots:</p>
        <ul>
            <li>Parameter correlation matrix</li>
            <li>Objective value distribution</li>
            <li>Parameter sensitivity bar chart</li>
            <li>Convergence plot (if applicable)</li>
        </ul>
    </div>
    """


def validate_calibration_config(config: Any) -> Tuple[bool, List[str]]:
    """
    Validate a calibration configuration.
    
    Args:
        config: Calibration configuration to validate
        
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    
    # Check required attributes
    required_attrs = [
        'method', 'objective', 'calibration_parameters',
        'max_iterations', 'results_dir'
    ]
    
    for attr in required_attrs:
        if not hasattr(config, attr):
            errors.append(f"Missing required attribute: {attr}")
    
    # Check calibration parameters
    if hasattr(config, 'calibration_parameters'):
        if not config.calibration_parameters:
            errors.append("At least one calibration parameter must be specified")
        
        if len(config.calibration_parameters) > 15:
            errors.append("Too many calibration parameters (max 15 recommended)")
    
    # Check max_iterations
    if hasattr(config, 'max_iterations'):
        if config.max_iterations <= 0:
            errors.append("max_iterations must be positive")
        
        if config.max_iterations > 10000:
            errors.append("max_iterations is very large (>10000), consider reducing")
    
    # Check results directory
    if hasattr(config, 'results_dir'):
        try:
            results_dir = Path(config.results_dir)
            results_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            errors.append(f"Cannot create results directory: {e}")
    
    # Check weights for multi-objective
    if hasattr(config, 'objective') and hasattr(config, 'spatial_similarity_weight'):
        if hasattr(config, 'fire_behavior_weight'):
            total_weight = config.spatial_similarity_weight + config.fire_behavior_weight
            if abs(total_weight - 1.0) > 1e-6:
                errors.append(f"Objective weights must sum to 1.0, got {total_weight}")
    
    return len(errors) == 0, errors


def create_synthetic_target_data(grid_size: Tuple[int, int], 
                               fire_type: str = "circular") -> Dict[str, Any]:
    """
    Create synthetic target data for testing calibration.
    
    Args:
        grid_size: Size of the grid (width, height)
        fire_type: Type of fire pattern ("circular", "elliptical", "random")
        
    Returns:
        Dictionary with synthetic fire perimeter data
    """
    width, height = grid_size
    fire_perimeter = np.zeros((width, height), dtype=np.uint8)
    
    center_x, center_y = width // 2, height // 2
    
    if fire_type == "circular":
        radius = min(width, height) // 4
        y, x = np.ogrid[:width, :height]
        mask = (x - center_x)**2 + (y - center_y)**2 <= radius**2
        fire_perimeter[mask] = 1
        
    elif fire_type == "elliptical":
        a = width // 4  # Semi-major axis
        b = height // 6  # Semi-minor axis
        y, x = np.ogrid[:width, :height]
        mask = ((x - center_x)**2 / a**2) + ((y - center_y)**2 / b**2) <= 1
        fire_perimeter[mask] = 1
        
    elif fire_type == "random":
        # Random scattered fire patches
        np.random.seed(42)
        num_patches = 5
        for _ in range(num_patches):
            patch_x = np.random.randint(0, width - 10)
            patch_y = np.random.randint(0, height - 10)
            patch_size = np.random.randint(3, 8)
            fire_perimeter[patch_x:patch_x+patch_size, patch_y:patch_y+patch_size] = 1
    
    return {
        'fire_perimeter': fire_perimeter,
        'fire_type': fire_type,
        'grid_size': grid_size,
        'burned_cells': np.sum(fire_perimeter),
        'total_cells': fire_perimeter.size,
        'burn_fraction': np.sum(fire_perimeter) / fire_perimeter.size
    }


def create_emsr_target_data(day1_path: str, day2_path: str, grid_size: tuple = (100, 100), model_resolution: float = 5.0) -> List['FirePerimeterData']:
    """
    Create target data from Day 1 and Day 2 EMSR delineations.
    
    Args:
        day1_path: Path to Day 1 EMSR shapefile
        day2_path: Path to Day 2 EMSR shapefile  
        grid_size: Grid size for target raster
        model_resolution: Model resolution in meters
        
    Returns:
        List of FirePerimeterData objects for calibration
    """
    import numpy as np
    from pathlib import Path
    from .fire_perimeter_calibration import FirePerimeterData
    
    logger.info("🔥 Creating EMSR target data from Day 1 and Day 2 delineations")
    
    # Check if files exist
    if not Path(day1_path).exists():
        raise FileNotFoundError(f"Day 1 EMSR file not found: {day1_path}")
    if not Path(day2_path).exists():
        raise FileNotFoundError(f"Day 2 EMSR file not found: {day2_path}")
    
    # Create FirePerimeterData objects for Day 1 and Day 2
    day1_fire_perimeter = FirePerimeterData(
        shapefile_path=day1_path,
        date="2023-08-18",  # Day 1 date
        day_number=1,
        fire_id="EMSR685_Day1",
        is_valid=True
    )
    
    day2_fire_perimeter = FirePerimeterData(
        shapefile_path=day2_path,
        date="2023-08-21",  # Day 2 date
        day_number=2,
        fire_id="EMSR685_Day2",
        is_valid=True
    )
    
    # Validate the fire perimeter data
    from .fire_perimeter_calibration import FirePerimeterDiscovery
    discovery = FirePerimeterDiscovery()
    discovery._validate_and_extract_metadata(day1_fire_perimeter)
    discovery._validate_and_extract_metadata(day2_fire_perimeter)
    
    logger.info(f"✅ Created EMSR target data with grid size {grid_size}")
    logger.info(f"   Day 1 target: {day1_fire_perimeter.area_hectares:.1f} ha" if day1_fire_perimeter.area_hectares else "   Day 1 target: Unknown area")
    logger.info(f"   Day 2 target: {day2_fire_perimeter.area_hectares:.1f} ha" if day2_fire_perimeter.area_hectares else "   Day 2 target: Unknown area")
    
    return [day1_fire_perimeter, day2_fire_perimeter]

def create_simple_circular_target(grid_size: tuple, center: tuple, radius: int) -> np.ndarray:
    """Create a simple circular target for testing."""
    import numpy as np
    
    target = np.zeros(grid_size)
    
    y, x = np.ogrid[:grid_size[0], :grid_size[1]]
    mask = (x - center[0])**2 + (y - center[1])**2 <= radius**2
    target[mask] = 1.0
    
    return target


def create_production_target_data(dem_file: str, 
                                 lidar_data_dir: str,
                                 grid_size: Tuple[int, int] = (80, 80),
                                 num_layers: int = 5,
                                 model_resolution: float = 5.0) -> Dict[str, Any]:
    """
    Create production target data using real terrain and fuel data.
    
    This function loads real DTM and LiDAR-derived PAD data to create
    a realistic fire simulation environment for sensitivity analysis.
    
    Args:
        dem_file: Path to Digital Elevation Model (DTM) file
        lidar_data_dir: Path to directory containing PAD Results
        grid_size: Size of the grid (width, height)
        num_layers: Number of vertical layers
        model_resolution: Resolution in meters per grid cell
        
    Returns:
        Dictionary with production data including terrain and fuel information
    """
    try:
        from src.config.config_tools import ModelConfig
        from src.core.forest_model import create_forest_model
        from src.core.vegetation_data_integration import TiledLiDARIntegration
        
        logger.info("🏔️  Creating production target data with real terrain and fuel...")
        logger.info(f"DEM file: {dem_file}")
        logger.info(f"LiDAR data directory: {lidar_data_dir}")
        logger.info(f"Grid size: {grid_size}")
        logger.info(f"Vertical layers: {num_layers}")
        
        # Validate file paths
        if not os.path.exists(dem_file):
            raise FileNotFoundError(f"DEM file not found: {dem_file}")
        if not os.path.exists(lidar_data_dir):
            raise FileNotFoundError(f"LiDAR data directory not found: {lidar_data_dir}")
        
        # Create production-ready model configuration
        production_config = ModelConfig(
            grid_size=grid_size,
            num_layers=num_layers,
            model_resolution=model_resolution,
            layer_height=2.0,  # 2m per layer
            
            # Enable production data loading
            fuel_load_method="tiled_lidar",
            lidar_data_dir=lidar_data_dir,
            dem_file=dem_file,
            
            # Realistic fire parameters (will be varied in sensitivity analysis)
            spread_probability=0.4,
            fuel_consumption_rate=1.0,
            ignition_threshold=0.15,  # Reduced threshold for easier ignition with PAD data
            min_fuel_value=0.1,
            max_fuel_value=1.0,  # Fixed for PAD data (0-1 range)
            
            # Wind and terrain settings
            wind_speed=5.0,
            wind_direction=45.0,
            slope_influence=0.3,
            wind_influence_on_spread=0.2,
            terrain_effect_strength=0.6,
            
            # Optimization settings
            memory_optimization_level=2,
            
            # Shorter simulation for sensitivity analysis
            max_steps=25,
            random_seed=42,
            debug=False
        )
        
        # Create forest model with production data
        logger.info("🌲 Creating forest model with production data...")
        forest_model = create_forest_model(config=production_config)
        
        # Load terrain data
        logger.info("🏔️  Loading terrain data...")
        terrain_success = forest_model.load_terrain_data(dem_file)
        if not terrain_success:
            raise RuntimeError(f"Failed to load terrain data from {dem_file}")
        
        # Load LiDAR vegetation data
        logger.info("🌿 Loading LiDAR vegetation data...")
        lidar_integrator = TiledLiDARIntegration(
            config=production_config,
            forest_model=forest_model
        )
        
        # Initialize the forest model with real fuel data
        lidar_integrator.initialize_forest_model()
        
        # Initialize terrain-influenced wind
        forest_model.initialize_terrain_wind(
            production_config.wind_direction,
            production_config.wind_speed,
            production_config.terrain_effect_strength
        )
        
        # Extract terrain statistics
        terrain_stats = {
            'elevation_min': float(np.min(forest_model.terrain_elevation)),
            'elevation_max': float(np.max(forest_model.terrain_elevation)),
            'elevation_mean': float(np.mean(forest_model.terrain_elevation)),
            'slope_min': float(np.min(forest_model.terrain_slope)),
            'slope_max': float(np.max(forest_model.terrain_slope)),
            'slope_mean': float(np.mean(forest_model.terrain_slope)),
        }
        
        # Extract fuel statistics
        fuel_stats = {
            'fuel_min': float(np.min(forest_model.fuel_load)),
            'fuel_max': float(np.max(forest_model.fuel_load)),
            'fuel_mean': float(np.mean(forest_model.fuel_load)),
            'fuel_total': float(np.sum(forest_model.fuel_load)),
        }
        
        # Count cells with fuel (non-zero fuel load)
        fuel_cells = np.sum(forest_model.fuel_load > 0)
        total_cells = forest_model.fuel_load.size
        
        logger.info("✅ Production target data created successfully:")
        logger.info(f"  • Terrain: {terrain_stats['elevation_min']:.1f}m to {terrain_stats['elevation_max']:.1f}m elevation")
        logger.info(f"  • Slopes: {terrain_stats['slope_min']:.1f}° to {terrain_stats['slope_max']:.1f}°")
        logger.info(f"  • Fuel: {fuel_stats['fuel_min']:.2f} to {fuel_stats['fuel_max']:.2f} kg/m²")
        logger.info(f"  • Fuel coverage: {fuel_cells}/{total_cells} cells ({fuel_cells/total_cells*100:.1f}%)")
        
        return {
            'forest_model': forest_model,
            'config': production_config,
            'data_type': 'production',
            'grid_size': grid_size,
            'num_layers': num_layers,
            'model_resolution': model_resolution,
            
            # Data source information
            'dem_file': dem_file,
            'lidar_data_dir': lidar_data_dir,
            
            # Statistics for reporting
            'terrain_stats': terrain_stats,
            'fuel_stats': fuel_stats,
            'fuel_cells': int(fuel_cells),
            'total_cells': int(total_cells),
            'fuel_coverage_percent': float(fuel_cells/total_cells*100),
            
            # Compatibility with existing synthetic data format
            'fire_perimeter': None,  # Will be generated by running fire simulation
            'burned_cells': 0,  # Will be calculated after simulation
            'burn_fraction': 0.0,  # Will be calculated after simulation
        }
        
    except Exception as e:
        logger.error(f"Failed to create production target data: {e}")
        logger.error("Falling back to synthetic data generation...")
        
        # Fallback to synthetic data if production data fails
        synthetic = create_synthetic_target_data(grid_size, "elliptical")
        # Add missing keys with None or dummy values for compatibility
        synthetic.update({
            'forest_model': None,
            'config': None,
            'data_type': 'synthetic',
            'num_layers': num_layers,
            'model_resolution': model_resolution,
            'dem_file': dem_file,
            'lidar_data_dir': lidar_data_dir,
            'terrain_stats': None,
            'fuel_stats': None,
            'fuel_cells': None,
            'total_cells': None,
            'fuel_coverage_percent': None
        })
        return synthetic


def calculate_optimal_grid_size_from_emsr(day1_path: str, day2_path: str, buffer_percent: float = 10.0) -> Tuple[int, int]:
    """
    Calculate optimal grid size based on EMSR fire perimeter data.
    
    Args:
        day1_path: Path to Day 1 EMSR shapefile
        day2_path: Path to Day 2 EMSR shapefile
        buffer_percent: Percentage buffer to add around fire perimeter
        
    Returns:
        Tuple of (grid_width, grid_height) in cells
    """
    try:
        import geopandas as gpd
        import pandas as pd
        
        # Load both Day 1 and Day 2 data to get the full fire extent
        gdf1 = gpd.read_file(day1_path)
        gdf2 = gpd.read_file(day2_path)
        
        # Ensure both are in EPSG:25828 (Tenerife UTM Zone 28N)
        if gdf1.crs != "EPSG:25828":
            gdf1 = gdf1.to_crs("EPSG:25828")
        if gdf2.crs != "EPSG:25828":
            gdf2 = gdf2.to_crs("EPSG:25828")
        
        # Combine both datasets to get the full fire extent
        combined_gdf = gpd.GeoDataFrame(pd.concat([gdf1, gdf2], ignore_index=True))
        
        # Get bounds of the entire fire complex
        bounds = combined_gdf.total_bounds  # [minx, miny, maxx, maxy]
        
        # Calculate dimensions in meters
        width_m = bounds[2] - bounds[0]  # maxx - minx
        height_m = bounds[3] - bounds[1]  # maxy - miny
        
        # Add buffer
        buffer_factor = 1.0 + (buffer_percent / 100.0)
        buffered_width_m = width_m * buffer_factor
        buffered_height_m = height_m * buffer_factor
        
        # Calculate grid size in cells (using 5m resolution)
        cell_size_m = 5.0
        grid_width = int(buffered_width_m / cell_size_m)
        grid_height = int(buffered_height_m / cell_size_m)
        
        # Ensure minimum size
        grid_width = max(grid_width, 500)  # Minimum 500x500 cells
        grid_height = max(grid_height, 500)
        
        logger.info(f"🗺️  Fire bounds (EPSG:25828): {bounds}")
        logger.info(f"🔥 Fire complex dimensions: {width_m:.0f}m × {height_m:.0f}m")
        logger.info(f"🎯 Calculated grid: {grid_width} × {grid_height} cells")
        
        return (grid_width, grid_height)
        
    except Exception as e:
        logger.error(f"❌ Error calculating optimal grid size: {e}")
        logger.warning("⚠️  Using fallback grid size")
        return (1000, 1000)  # Fallback size


if __name__ == "__main__":
    # Example usage
    print("Calibration Utilities Example")
    print("=" * 50)
    
    # Create synthetic target data
    target_data = create_synthetic_target_data((50, 50), "circular")
    print(f"Created synthetic target with {target_data['burned_cells']} burned cells")
    
    # Example validation
    class MockConfig:
        method = "grid_search"
        objective = "spatial_similarity"
        calibration_parameters = ["spread_probability", "fuel_consumption_rate"]
        max_iterations = 100
        results_dir = "test_results"
    
    config = MockConfig()
    is_valid, errors = validate_calibration_config(config)
    print(f"\nConfig validation: {'PASS' if is_valid else 'FAIL'}")
    if errors:
        for error in errors:
            print(f"  Error: {error}")
    
    print(f"\nSynthetic target stats:")
    print(f"  Shape: {target_data['fire_perimeter'].shape}")
    print(f"  Burned fraction: {target_data['burn_fraction']:.3f}")
    print(f"  Fire type: {target_data['fire_type']}") 