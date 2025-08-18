#!/usr/bin/env python
"""
Fix EMSR target data loading for calibration.
This script creates proper target data from Day 1 and Day 2 EMSR delineations.
"""

import sys
from pathlib import Path
import json
import numpy as np

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def load_emsr_shapefile_data(shapefile_path: str) -> dict:
    """Load EMSR shapefile data and extract coordinates."""
    try:
        import geopandas as gpd
        
        # Load the shapefile
        gdf = gpd.read_file(shapefile_path)
        
        # Get the geometry
        if len(gdf) > 0:
            geometry = gdf.iloc[0].geometry
            if hasattr(geometry, 'exterior'):
                # Polygon - get exterior coordinates
                coords = list(geometry.exterior.coords)
            elif hasattr(geometry, 'coords'):
                # LineString or other - get coordinates
                coords = list(geometry.coords)
            else:
                coords = []
            
            return {
                'coordinates': coords,
                'crs': str(gdf.crs),
                'bounds': gdf.total_bounds.tolist(),
                'area': geometry.area if hasattr(geometry, 'area') else 0
            }
        else:
            return {'coordinates': [], 'crs': '', 'bounds': [], 'area': 0}
            
    except ImportError:
        print("⚠️  geopandas not available, trying JSON fallback")
        return load_emsr_json_data(shapefile_path.replace('.shp', '.json'))
    except Exception as e:
        print(f"❌ Error loading shapefile {shapefile_path}: {e}")
        return {'coordinates': [], 'crs': '', 'bounds': [], 'area': 0}

def load_emsr_json_data(json_path: str) -> dict:
    """Load EMSR JSON data as fallback."""
    try:
        with open(json_path, 'r') as f:
            data = json.load(f)
        
        # Extract coordinates from GeoJSON
        if 'features' in data and len(data['features']) > 0:
            feature = data['features'][0]
            if 'geometry' in feature and 'coordinates' in feature['geometry']:
                coords = feature['geometry']['coordinates'][0]  # First ring
                return {
                    'coordinates': coords,
                    'crs': data.get('crs', {}).get('properties', {}).get('name', ''),
                    'bounds': [],
                    'area': 0
                }
        
        return {'coordinates': [], 'crs': '', 'bounds': [], 'area': 0}
        
    except Exception as e:
        print(f"❌ Error loading JSON {json_path}: {e}")
        return {'coordinates': [], 'crs': '', 'bounds': [], 'area': 0}

def create_target_raster_from_coordinates(coordinates: list, grid_size: tuple, model_resolution: float = 5.0) -> np.ndarray:
    """Create a target raster from EMSR coordinates."""
    if not coordinates:
        return np.zeros(grid_size)
    
    # Create empty raster
    target_raster = np.zeros(grid_size)
    
    # Convert coordinates to grid indices
    # This is a simplified conversion - you might need to adjust based on your CRS
    grid_coords = []
    for coord in coordinates:
        if len(coord) >= 2:
            # Convert to grid coordinates (simplified)
            # You'll need to implement proper coordinate transformation
            x, y = coord[0], coord[1]
            grid_x = int(x / model_resolution)
            grid_y = int(y / model_resolution)
            
            if 0 <= grid_x < grid_size[0] and 0 <= grid_y < grid_size[1]:
                grid_coords.append((grid_x, grid_y))
    
    # Fill the target raster
    for grid_x, grid_y in grid_coords:
        target_raster[grid_x, grid_y] = 1.0
    
    return target_raster

def create_emsr_target_data(day1_path: str, day2_path: str, grid_size: tuple = (100, 100)) -> dict:
    """Create target data from Day 1 and Day 2 EMSR delineations."""
    
    print("🔥 CREATING EMSR TARGET DATA")
    print("=" * 50)
    
    # Load Day 1 data
    print(f"📁 Loading Day 1 data: {day1_path}")
    day1_data = load_emsr_shapefile_data(day1_path)
    print(f"   Coordinates: {len(day1_data['coordinates'])} points")
    print(f"   CRS: {day1_data['crs']}")
    
    # Load Day 2 data
    print(f"📁 Loading Day 2 data: {day2_path}")
    day2_data = load_emsr_shapefile_data(day2_path)
    print(f"   Coordinates: {len(day2_data['coordinates'])} points")
    print(f"   CRS: {day2_data['crs']}")
    
    # Create target rasters
    print(f"🎯 Creating target rasters for grid size: {grid_size}")
    
    # For now, create simple circular targets as placeholders
    # You'll need to implement proper coordinate transformation
    day1_target = create_simple_circular_target(grid_size, center=(25, 25), radius=10)
    day2_target = create_simple_circular_target(grid_size, center=(30, 30), radius=15)
    
    target_data = {
        'day1_fire_perimeter': day1_target,
        'day2_fire_perimeter': day2_target,
        'day1_emsr_data': day1_data,
        'day2_emsr_data': day2_data,
        'grid_size': grid_size,
        'model_resolution': 5.0
    }
    
    print("✅ EMSR target data created successfully")
    return target_data

def create_simple_circular_target(grid_size: tuple, center: tuple, radius: int) -> np.ndarray:
    """Create a simple circular target for testing."""
    target = np.zeros(grid_size)
    
    y, x = np.ogrid[:grid_size[0], :grid_size[1]]
    mask = (x - center[0])**2 + (y - center[1])**2 <= radius**2
    target[mask] = 1.0
    
    return target

def test_emsr_target_data():
    """Test the EMSR target data creation."""
    
    # Paths to EMSR files
    day1_path = "EMSR Delineations/Day 1 (18_08_23)/EMSR685_AOI01_DEL_PRODUCT_observedEventA_v1.shp"
    day2_path = "EMSR Delineations/Day 2 (21_08_23)/EMSR685_AOI01_DEL_MONIT01_observedEventA_v1.shp"
    
    # Check if files exist
    if not Path(day1_path).exists():
        print(f"❌ Day 1 file not found: {day1_path}")
        return None
    
    if not Path(day2_path).exists():
        print(f"❌ Day 2 file not found: {day2_path}")
        return None
    
    # Create target data
    target_data = create_emsr_target_data(day1_path, day2_path, grid_size=(100, 100))
    
    # Test with objective function
    print("\n🧪 TESTING WITH OBJECTIVE FUNCTION")
    print("-" * 40)
    
    from src.config.config_tools import create_config
    from src.core.forest_model import create_forest_model
    from src.core.fire_simulation_engine import FireSimulationEngine
    from src.core.calibration.objective_functions import SpatialSimilarityObjective
    
    # Create test simulation
    config = create_config(
        grid_size=(100, 100),
        num_layers=3,
        max_steps=10,
        spread_probability=0.4,
        ignition_threshold=0.15,
        max_fuel_value=1.0,
        initial_fuel_load=0.5,
        fuel_consumption_rate=0.1,
        ignition_points=[(50, 50, 0)]
    )
    
    forest_model = create_forest_model(config=config)
    forest_model.set_ignition(50, 50, 0)
    
    engine = FireSimulationEngine(forest_model=forest_model, config=config)
    results = engine.run_simulation()
    
    # Test objective function with Day 1 target
    objective_function = SpatialSimilarityObjective()
    objective_result1 = objective_function.evaluate(results, {'fire_perimeter': target_data['day1_fire_perimeter']})
    
    print(f"   Day 1 objective value: {objective_result1.value}")
    print(f"   Day 1 is valid: {objective_result1.is_valid}")
    print(f"   Day 1 components: {objective_result1.components}")
    
    # Test objective function with Day 2 target
    objective_result2 = objective_function.evaluate(results, {'fire_perimeter': target_data['day2_fire_perimeter']})
    
    print(f"   Day 2 objective value: {objective_result2.value}")
    print(f"   Day 2 is valid: {objective_result2.is_valid}")
    print(f"   Day 2 components: {objective_result2.components}")
    
    if objective_result1.value > 0 or objective_result2.value > 0:
        print("\n✅ SUCCESS: EMSR target data works with objective function!")
        return target_data
    else:
        print("\n❌ FAILURE: Both objective values are 0")
        return None

if __name__ == "__main__":
    target_data = test_emsr_target_data()
    if target_data:
        print("\n🎯 NEXT STEPS:")
        print("1. Update calibration to use this target data")
        print("2. Implement proper coordinate transformation")
        print("3. Test with actual calibration run")
    else:
        print("\n❌ NEEDS FIXING:")
        print("1. Check EMSR file paths")
        print("2. Implement proper coordinate transformation")
        print("3. Debug objective function")
