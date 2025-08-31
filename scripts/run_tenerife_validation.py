#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Validation script for Tenerife fire simulation using Day 3 and Day 4 test data.
This script loads the best parameters from calibration and validates them on unseen data.
ANIMATION-READY: Saves simulation history and model states for post-hoc animation generation.
"""

import argparse
import json
import sys
import time
import pickle
from pathlib import Path
from typing import Dict, Any, List

import numpy as np

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.calibration.fire_perimeter_calibration import (
    FirePerimeterDiscovery, 
    TenerifeFirePerimeterCalibrator,
    FirePerimeterDataset
)
from src.core.calibration.calibration_config import CalibrationConfig
from src.core.calibration.objective_functions import SpatialSimilarityObjective
from src.config.config_tools import ModelConfig
from src.core.forest_model import create_forest_model
from src.core.fire_simulation_engine import FireSimulationEngine

def load_best_parameters(results_dir: str, experiment_name: str) -> Dict[str, float]:
    """Load the best parameters from calibration results."""
    # Check if results are in a subdirectory (new format) or directly in results_dir (old format)
    results_file = Path(results_dir) / experiment_name / f"{experiment_name}_grid_search_results.json"
    
    if not results_file.exists():
        # Try old format (direct in results_dir)
        results_file = Path(results_dir) / f"{experiment_name}_grid_search_results.json"
    
    if not results_file.exists():
        raise FileNotFoundError(f"Results file not found: {results_file}")
    
    with open(results_file, 'r') as f:
        results_data = json.load(f)
    
    # Find the best result
    best_result = None
    best_objective = -1.0
    
    for result in results_data.get('results', []):
        objective_value = result.get('objective_value', 0.0)
        if objective_value > best_objective:
            best_objective = objective_value
            best_result = result
    
    if best_result is None:
        raise ValueError("No valid results found in calibration output")
    
    print(f"✅ Loaded best parameters (objective: {best_objective:.8f})")
    return best_result.get('parameters', {})

def save_animation_data(forest_model, engine, config, day_number, output_dir: Path):
    """Save animation data for post-hoc visualization."""
    print(f"    🎬 Saving animation data for Day {day_number}...")
    
    # Create animation data directory
    animation_dir = output_dir / "animation_data"
    animation_dir.mkdir(exist_ok=True)
    
    # Save forest model state
    model_state_file = animation_dir / f"validation_day_{day_number}_model_state.pkl"
    with open(model_state_file, 'wb') as f:
        pickle.dump(forest_model, f)
    print(f"      ✅ Model state saved: {model_state_file.name}")
    
    # Save simulation history if available
    if hasattr(engine, 'history') and engine.history:
        history_file = animation_dir / f"validation_day_{day_number}_history.pkl"
        with open(history_file, 'wb') as f:
            pickle.dump(engine.history, f)
        print(f"      ✅ Simulation history saved: {history_file.name} ({len(engine.history)} steps)")
    else:
        print(f"      ⚠️  No simulation history available for Day {day_number}")
    
    # Create and save animation metadata
    metadata = {
        'grid_size': config.grid_size,
        'num_layers': config.num_layers,
        'model_resolution': config.model_resolution,
        'day_number': day_number,
        'simulation_steps': len(engine.history) if hasattr(engine, 'history') else 0,
        'max_steps': config.max_steps,
        'ignition_points': config.ignition_points,
        'use_lidar': config.use_lidar,
        'use_preprocessed_terrain': config.use_preprocessed_terrain,
        'validation_timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        'animation_ready': True
    }
    
    metadata_file = animation_dir / f"validation_day_{day_number}_metadata.json"
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)
    print(f"      ✅ Animation metadata saved: {metadata_file.name}")
    
    return {
        'model_state_file': str(model_state_file),
        'history_file': str(history_file) if hasattr(engine, 'history') and engine.history else None,
        'metadata_file': str(metadata_file)
    }

def run_validation_simulation(
    config: ModelConfig,
    test_fire_perimeter: Any,
    day_number: int,
    output_dir: Path
) -> Dict[str, Any]:
    """Run a single validation simulation with animation data saving."""
    print(f"  🧪 Running Day {day_number} validation simulation...")
    
    # Initialize forest model using the same factory function as calibration
    forest_model = create_forest_model(
        model_type="memory_optimized",
        config=config
    )
    
    # Set ignition points (same as calibration)
    for ignition_point in config.ignition_points:
        forest_model.set_ignition(ignition_point[0], ignition_point[1], ignition_point[2])
    
    # Initialize simulation engine (same as calibration)
    engine = FireSimulationEngine(forest_model=forest_model, config=config)
    
    # Run simulation with history storage enabled for animation
    start_time = time.time()
    simulation_result = engine.run_simulation(
        max_steps=config.max_steps,
        store_history=True  # Enable history storage for animation
    )
    simulation_time = time.time() - start_time
    
    # Create simulation result dictionary (same structure as calibration)
    simulation_result_dict = {
        'forest_model': forest_model,
        'engine': engine,
        'config': config
    }
    
    # Calculate validation metrics using same objective function as calibration
    objective = SpatialSimilarityObjective()
    
    # Create target data structure (same as calibration)
    target_data = {
        'fire_perimeter': test_fire_perimeter,
        'grid_size': config.grid_size,
        'model_resolution': config.model_resolution
    }
    
    # Evaluate similarity using same method as calibration
    result = objective.evaluate(simulation_result_dict, target_data)
    
    # Extract fire perimeter (same as calibration)
    predicted_2d = forest_model.get_2d_fire_perimeter()
    
    # Extract comprehensive fire spread statistics (same as calibration)
    vertical_spread_stats = None
    if forest_model and hasattr(forest_model, 'spread_stats') and forest_model.spread_stats:
        stats = forest_model.spread_stats
        
        # Calculate key metrics (same as calibration)
        total_spread = sum(stats.values())
        vertical_spread = stats.get('vertical_spread', 0)
        horizontal_spread = stats.get('horizontal_spread', 0)
        ember_spread = stats.get('ember_spread', 0)
        total_ignitions = stats.get('total_ignitions', 0)
        
        # Calculate percentages (same as calibration)
        vertical_percentage = (vertical_spread / total_spread * 100) if total_spread > 0 else 0
        horizontal_percentage = (horizontal_spread / total_spread * 100) if total_spread > 0 else 0
        ember_percentage = (ember_spread / total_spread * 100) if total_spread > 0 else 0
        
        # Calculate efficiency (same as calibration)
        vertical_efficiency = (vertical_spread / total_ignitions * 100) if total_ignitions > 0 else 0
        horizontal_efficiency = (horizontal_spread / total_ignitions * 100) if total_ignitions > 0 else 0
        ember_efficiency = (ember_spread / total_ignitions * 100) if total_ignitions > 0 else 0
        
        # Calculate ratios (same as calibration)
        vertical_horizontal_ratio = vertical_spread / horizontal_spread if horizontal_spread > 0 else 0
        ember_horizontal_ratio = ember_spread / horizontal_spread if horizontal_spread > 0 else 0
        ember_vertical_ratio = ember_spread / vertical_spread if vertical_spread > 0 else 0
        
        # Classify spread behavior (same as calibration)
        if vertical_horizontal_ratio > 0.1:
            spread_classification = "High vertical spread - strong convection"
        elif vertical_horizontal_ratio > 0.05:
            spread_classification = "Moderate vertical spread - normal behavior"
        else:
            spread_classification = "Low vertical spread - primarily horizontal"
        
        # Add ember classification
        if ember_percentage > 10:
            ember_classification = "High ember activity - significant spotting"
        elif ember_percentage > 5:
            ember_classification = "Moderate ember activity - some spotting"
        else:
            ember_classification = "Low ember activity - minimal spotting"
        
        vertical_spread_stats = {
            'total_spread_events': total_spread,
            'vertical_spread_events': vertical_spread,
            'vertical_spread_percentage': vertical_percentage,
            'horizontal_spread_events': horizontal_spread,
            'horizontal_spread_percentage': horizontal_percentage,
            'ember_spread_events': ember_spread,
            'ember_spread_percentage': ember_percentage,
            'total_ignitions': total_ignitions,
            'vertical_efficiency': vertical_efficiency,
            'horizontal_efficiency': horizontal_efficiency,
            'ember_efficiency': ember_efficiency,
            'vertical_horizontal_ratio': vertical_horizontal_ratio,
            'ember_horizontal_ratio': ember_horizontal_ratio,
            'ember_vertical_ratio': ember_vertical_ratio,
            'spread_classification': spread_classification,
            'ember_classification': ember_classification,
            'raw_spread_stats': stats  # Include raw stats for detailed analysis
        }
    
    # Save animation data
    animation_files = save_animation_data(forest_model, engine, config, day_number, output_dir)
    
    validation_result = {
        'day_number': day_number,
        'date': getattr(test_fire_perimeter, 'date', f'Day {day_number}'),
        'simulation_time_seconds': simulation_time,
        'burned_cells': int(np.sum(predicted_2d > 0)),
        'burned_area_hectares': float(np.sum(predicted_2d > 0) * (config.model_resolution ** 2) / 10000),
        'objective_value': result.objective_value,
        'is_valid': result.is_valid,
        'jaccard_similarity': result.metrics.get('jaccard', 0.0),
        'dice_similarity': result.metrics.get('dice', 0.0),
        'vertical_fire_spread': vertical_spread_stats,  # Same as calibration
        'target_area_hectares': getattr(test_fire_perimeter, 'area_hectares', 0.0),
        'animation_files': animation_files,  # Include animation file paths
        'simulation_steps': len(engine.history) if hasattr(engine, 'history') else 0
    }
    
    # Enhanced output with spread statistics
    if vertical_spread_stats:
        print(f"    ✅ Day {day_number}: {validation_result['burned_cells']} cells burned, "
              f"Jaccard: {validation_result['jaccard_similarity']:.4f}, "
              f"Dice: {validation_result['dice_similarity']:.4f}, "
              f"Steps: {validation_result['simulation_steps']}")
        print(f"       🔥 Spread: H:{horizontal_spread}({horizontal_percentage:.1f}%) "
              f"V:{vertical_spread}({vertical_percentage:.1f}%) "
              f"E:{ember_spread}({ember_percentage:.1f}%)")
        print(f"       📊 Classification: {spread_classification} | {ember_classification}")
    else:
        print(f"    ✅ Day {day_number}: {validation_result['burned_cells']} cells burned, "
              f"Jaccard: {validation_result['jaccard_similarity']:.4f}, "
              f"Dice: {validation_result['dice_similarity']:.4f}, "
              f"Steps: {validation_result['simulation_steps']}")
    
    return validation_result

def main():
    parser = argparse.ArgumentParser(description="Validate calibrated parameters on Day 3 and Day 4 test data")
    parser.add_argument("--results-dir", default="calibration_results", help="Directory containing calibration results")
    parser.add_argument("--experiment-name", required=True, help="Name of the calibration experiment")
    parser.add_argument("--max-steps", type=int, default=200, help="Maximum simulation steps")
    parser.add_argument("--output-dir", default="validation_results", help="Output directory for validation results")
    
    args = parser.parse_args()
    
    print("🧪 TENERIFE FIRE SIMULATION VALIDATION")
    print("🎬 ANIMATION-READY: Will save simulation data for post-hoc visualization")
    print("=" * 60)
    print(f"Experiment: {args.experiment_name}")
    print(f"Results directory: {args.results_dir}")
    print(f"Max steps: {args.max_steps}")
    print()
    
    try:
        # Step 1: Load best parameters from calibration
        print("📋 Step 1: Loading best parameters from calibration...")
        best_parameters = load_best_parameters(args.results_dir, args.experiment_name)
        
        print("Best parameters:")
        for param, value in best_parameters.items():
            print(f"   {param}: {value:.6f}")
        print()
        
        # Step 2: Discover fire perimeters
        print("📊 Step 2: Discovering fire perimeters...")
        discovery = FirePerimeterDiscovery('EMSR Delineations')
        fire_dataset = discovery.discover_fire_perimeters()
        
        if not fire_dataset.fire_perimeters:
            raise ValueError("No fire perimeters found!")
        
        print(f"Found {len(fire_dataset.fire_perimeters)} fire perimeters")
        
        # Step 3: Set up test data (Day 3 and Day 4)
        print("🧪 Step 3: Setting up test data (Day 3 and Day 4)...")
        calibrator = TenerifeFirePerimeterCalibrator(
            memory_gb=16,
            workers=1,  # Single worker for validation
            grid_search_points=1,
            experiment_name="validation_run",
            grid_size=(609, 609),
            base_directory='EMSR Delineations'
        )
        
        training_data, test_data = calibrator.setup_training_test_split(
            fire_dataset,
            training_days=[1, 2],
            test_days=[3, 4]
        )
        
        print(f"✅ Test data: {len(test_data)} fire perimeters (Days 3-4)")
        for test_fp in test_data:
            print(f"   Day {test_fp.day_number}: {test_fp.area_hectares:.1f} ha")
        print()
        
        # Calculate and display grid information
        grid_cells = 609 * 609 * 20  # 7,416,180 cells (20 layers for preprocessed terrain)
        grid_area_km2 = (609 * 609 * 20 * 20) / 1000000  # CORRECTED: 2D area only
        print(f"Grid configuration:")
        print(f"   Grid size: 609 × 609 × 20 = {grid_cells:,} cells")
        print(f"   Resolution: 20m per cell")
        print(f"   Total area: {grid_area_km2:.1f} km² ({grid_area_km2*100:.1f} ha)")
        print()
        
        # Step 4: Create validation configuration
        print("⚙️  Step 4: Creating validation configuration...")
        base_config = ModelConfig(
            grid_size=(609, 609),
            num_layers=20,  # Use 20 layers (preprocessed terrain)
            max_steps=args.max_steps,
            model_resolution=20.0,
            simulation_type="memory_optimized",
            memory_optimization_level=3,
            use_disk_storage=True,
            use_differential_history=True,
            use_sparse_storage=True,
            
            # Enable LiDAR
            use_lidar=True,
            auto_size_from_lidar=False,
            preprocessed_lidar_dir='preprocessed_lidar',
            
            # Preprocessed terrain
            use_preprocessed_terrain=True,
            preprocessed_terrain_dir='preprocessed_terrain',
            
            # Set ignition points (same as calibration)
            ignition_points=[(395, 377, 0)]
        )
        
        # Apply best parameters to config
        for param, value in best_parameters.items():
            if hasattr(base_config, param):
                setattr(base_config, param, value)
                print(f"   Applied {param}: {value:.6f}")
        
        print()
        
        # Step 5: Run validation simulations
        print("🚀 Step 5: Running validation simulations...")
        validation_results = []
        output_dir = Path(args.output_dir)
        output_dir.mkdir(exist_ok=True)
        
        for test_fp in test_data:
            validation_result = run_validation_simulation(
                base_config, 
                test_fp, 
                test_fp.day_number,
                output_dir
            )
            validation_results.append(validation_result)
        
        # Step 6: Calculate overall validation metrics
        print("\n📊 Step 6: Calculating validation metrics...")
        
        total_jaccard = sum(r['jaccard_similarity'] for r in validation_results)
        total_dice = sum(r['dice_similarity'] for r in validation_results)
        avg_jaccard = total_jaccard / len(validation_results)
        avg_dice = total_dice / len(validation_results)
        
        total_burned_cells = sum(r['burned_cells'] for r in validation_results)
        total_target_area = sum(r['target_area_hectares'] for r in validation_results)
        total_simulated_area = sum(r['burned_area_hectares'] for r in validation_results)
        
        print(f"✅ Validation Summary:")
        print(f"   Average Jaccard Similarity: {avg_jaccard:.4f}")
        print(f"   Average Dice Similarity: {avg_dice:.4f}")
        print(f"   Total Burned Cells: {total_burned_cells:,}")
        print(f"   Total Target Area: {total_target_area:.1f} ha")
        print(f"   Total Simulated Area: {total_simulated_area:.1f} ha")
        print(f"   Area Ratio (Simulated/Target): {total_simulated_area/total_target_area:.3f}")
        
        # Step 7: Save validation results
        print("\n💾 Step 7: Saving validation results...")
        
        validation_summary = {
            'experiment_info': {
                'calibration_experiment': args.experiment_name,
                'validation_timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                'test_days': [3, 4],
                'max_steps': args.max_steps,
                'animation_ready': True
            },
            'best_parameters': best_parameters,
            'validation_metrics': {
                'average_jaccard_similarity': avg_jaccard,
                'average_dice_similarity': avg_dice,
                'total_burned_cells': total_burned_cells,
                'total_target_area_hectares': total_target_area,
                'total_simulated_area_hectares': total_simulated_area,
                'area_ratio': total_simulated_area/total_target_area
            },
            'individual_results': validation_results,
            'animation_info': {
                'animation_data_directory': str(output_dir / "animation_data"),
                'available_days': [r['day_number'] for r in validation_results],
                'animation_files_per_day': {
                    r['day_number']: r['animation_files'] for r in validation_results
                }
            }
        }
        
        # Save detailed results
        results_file = output_dir / f"{args.experiment_name}_validation_results.json"
        with open(results_file, 'w') as f:
            json.dump(validation_summary, f, indent=2)
        
        # Save summary report
        summary_file = output_dir / f"{args.experiment_name}_validation_summary.txt"
        with open(summary_file, 'w') as f:
            f.write("TENERIFE FIRE SIMULATION VALIDATION SUMMARY\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"Calibration Experiment: {args.experiment_name}\n")
            f.write(f"Validation Date: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Test Days: 3, 4\n")
            f.write(f"Animation Ready: YES\n\n")
            
            f.write("BEST PARAMETERS:\n")
            for param, value in best_parameters.items():
                f.write(f"   {param}: {value:.6f}\n")
            f.write("\n")
            
            f.write("VALIDATION METRICS:\n")
            f.write(f"   Average Jaccard Similarity: {avg_jaccard:.4f}\n")
            f.write(f"   Average Dice Similarity: {avg_dice:.4f}\n")
            f.write(f"   Total Burned Cells: {total_burned_cells:,}\n")
            f.write(f"   Total Target Area: {total_target_area:.1f} ha\n")
            f.write(f"   Total Simulated Area: {total_simulated_area:.1f} ha\n")
            f.write(f"   Area Ratio (Simulated/Target): {total_simulated_area/total_target_area:.3f}\n\n")
            
            f.write("ANIMATION DATA:\n")
            f.write(f"   Animation data directory: {output_dir / 'animation_data'}\n")
            for result in validation_results:
                f.write(f"   Day {result['day_number']}: {result['simulation_steps']} simulation steps\n")
            f.write("\n")
            
            f.write("INDIVIDUAL RESULTS:\n")
            for result in validation_results:
                f.write(f"   Day {result['day_number']}:\n")
                f.write(f"     Jaccard: {result['jaccard_similarity']:.4f}\n")
                f.write(f"     Dice: {result['dice_similarity']:.4f}\n")
                f.write(f"     Burned Cells: {result['burned_cells']:,}\n")
                f.write(f"     Simulated Area: {result['burned_area_hectares']:.1f} ha\n")
                f.write(f"     Target Area: {result['target_area_hectares']:.1f} ha\n")
                f.write(f"     Simulation Steps: {result['simulation_steps']}\n\n")
        
        print(f"✅ Validation results saved to: {output_dir}")
        print(f"   Detailed results: {results_file.name}")
        print(f"   Summary report: {summary_file.name}")
        print(f"   🎬 Animation data: {output_dir / 'animation_data'}")
        
        print(f"\n🎉 VALIDATION COMPLETED!")
        print(f"   The model achieved {avg_jaccard:.4f} average Jaccard similarity")
        print(f"   and {avg_dice:.4f} average Dice similarity on unseen test data.")
        print(f"   🎬 Animation data saved for post-hoc visualization!")
        
        if avg_jaccard > 0.3 and avg_dice > 0.4:
            print("   🎯 EXCELLENT: Model generalizes well to unseen data!")
        elif avg_jaccard > 0.2 and avg_dice > 0.3:
            print("   ✅ GOOD: Model shows reasonable generalization.")
        else:
            print("   ⚠️  MODERATE: Model may need further calibration.")
        
    except Exception as e:
        print(f"❌ Validation failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
