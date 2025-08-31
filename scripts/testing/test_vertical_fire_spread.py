#!/usr/bin/env python3
"""
Test script to analyze vertical fire spread performance
Uses pdal_env_new environment as requested
"""

import logging
import sys
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent))

# Set up minimal logging
logging.basicConfig(
    level=logging.WARNING,
    format='%(levelname)s: %(message)s'
)

# Set specific loggers to WARNING level
logging.getLogger('src.core.forest_model').setLevel(logging.WARNING)
logging.getLogger('src.core.calibration').setLevel(logging.WARNING)
logging.getLogger('src.core.fire_simulation_engine').setLevel(logging.WARNING)
logging.getLogger('src.utils.lidar_utils').setLevel(logging.WARNING)
logging.getLogger('src.utils.terrain_preprocessor').setLevel(logging.WARNING)

def test_vertical_fire_spread():
    """Test and analyze vertical fire spread performance"""
    print("🔥 Testing Vertical Fire Spread Performance")
    print("=" * 50)
    
    try:
        from src.core.forest_model import MemoryOptimizedForestModel
        from src.core.fire_simulation_engine import FireSimulationEngine
        from src.config.config_tools import ModelConfig
        from src.utils.visualization import ForestFireVisualizer
        import numpy as np
        
        print("✅ Successfully imported required modules")
        
        # Create a test configuration
        config = ModelConfig(
            grid_size=100,  # Smaller grid for testing
            max_steps=50,   # Shorter simulation for quick results
            ignition_points=[(50, 50, 0)],  # Center ignition
            use_lidar=True,
            preprocessed_lidar_dir=r'C:\Users\user\Desktop\UvA\YEAR 2\Thesis\Coding\QGIS python scripts\preprocessed_lidar',
            use_preprocessed_terrain=True,
            preprocessed_terrain_dir="calibration_terrain",
            spread_probability=0.8,
            ignition_threshold=0.5,
            wind_speed=5.0,  # Moderate wind
            wind_direction=45.0,  # Northeast wind
            max_vegetation_height_m=25.0,
            layer_height=2.0
        )
        
        print("✅ Created test configuration")
        
        # Initialize forest model
        print("🌲 Initializing forest model...")
        forest_model = MemoryOptimizedForestModel(
            grid_size=config.grid_size,
            num_layers=config.num_layers,
            model_resolution=config.model_resolution,
            layer_height_meters=config.layer_height,
            initial_fuel_load=config.initial_fuel_load,
            use_sparse_storage=True,
            config=config
        )
        
        # Set ignition point in forest model
        print("🔥 Setting ignition point...")
        forest_model.set_ignition(50, 50, 0)  # Center ignition point
        
        # Initialize simulation engine
        print("🔥 Initializing fire simulation engine...")
        engine = FireSimulationEngine(forest_model, config)
        
        # Run simulation
        print("🚀 Running fire simulation...")
        result = engine.run_simulation()
        
        print("✅ Simulation completed!")
        
        # Analyze spread statistics
        print("\n📊 SPREAD STATISTICS ANALYSIS")
        print("-" * 30)
        
        if hasattr(forest_model, 'spread_stats') and forest_model.spread_stats:
            stats = forest_model.spread_stats
            
            # Calculate totals
            total_spread = sum(stats.values())
            vertical_spread = stats.get('vertical_spread', 0)
            horizontal_spread = stats.get('horizontal_spread', 0)
            ember_spread = stats.get('ember_spread', 0)
            ember_ignitions = stats.get('ember_ignitions', 0)
            total_ignitions = stats.get('total_ignitions', 0)
            wind_assisted = stats.get('wind_assisted_spread', 0)
            slope_assisted = stats.get('slope_assisted_spread', 0)
            barranco_assisted = stats.get('barranco_assisted_spread', 0)
            
            print(f"🔥 Total Spread Events: {total_spread}")
            
            if total_spread > 0:
                print(f"📈 Vertical Spread: {vertical_spread} ({vertical_spread/total_spread*100:.1f}%)")
                print(f"➡️  Horizontal Spread: {horizontal_spread} ({horizontal_spread/total_spread*100:.1f}%)")
                print(f"💨 Ember Spread: {ember_spread} ({ember_spread/total_spread*100:.1f}%)")
                print(f"⚡ Ember Ignitions: {ember_ignitions}")
                print(f"🎯 Total Ignitions: {total_ignitions}")
                print(f"💨 Wind-Assisted: {wind_assisted} ({wind_assisted/total_spread*100:.1f}%)")
                print(f"⛰️  Slope-Assisted: {slope_assisted} ({slope_assisted/total_spread*100:.1f}%)")
                print(f"🏞️  Barranco-Assisted: {barranco_assisted} ({barranco_assisted/total_spread*100:.1f}%)")
            else:
                print("❌ No spread events detected - fire may not have ignited properly")
                print(f"📈 Vertical Spread: {vertical_spread}")
                print(f"➡️  Horizontal Spread: {horizontal_spread}")
                print(f"💨 Ember Spread: {ember_spread}")
                print(f"⚡ Ember Ignitions: {ember_ignitions}")
                print(f"🎯 Total Ignitions: {total_ignitions}")
                print(f"💨 Wind-Assisted: {wind_assisted}")
                print(f"⛰️  Slope-Assisted: {slope_assisted}")
                print(f"🏞️  Barranco-Assisted: {barranco_assisted}")
            
            # Vertical spread analysis
            print(f"\n🔍 VERTICAL SPREAD ANALYSIS")
            print("-" * 25)
            
            if vertical_spread > 0:
                print(f"✅ Vertical spread is ACTIVE")
                print(f"   - {vertical_spread} vertical spread events detected")
                print(f"   - Vertical spread represents {vertical_spread/total_spread*100:.1f}% of total spread")
                
                # Calculate vertical spread efficiency
                if total_ignitions > 0:
                    vertical_efficiency = vertical_spread / total_ignitions * 100
                    print(f"   - Vertical spread efficiency: {vertical_efficiency:.1f}%")
                
                # Compare with horizontal spread
                if horizontal_spread > 0:
                    vertical_horizontal_ratio = vertical_spread / horizontal_spread
                    print(f"   - Vertical/Horizontal ratio: {vertical_horizontal_ratio:.3f}")
                    
                    if vertical_horizontal_ratio > 0.1:
                        print("   - ⚠️  High vertical spread detected - may indicate strong convection")
                    elif vertical_horizontal_ratio > 0.05:
                        print("   - ✅ Moderate vertical spread - normal fire behavior")
                    else:
                        print("   - ℹ️  Low vertical spread - primarily horizontal fire")
            else:
                print("❌ No vertical spread detected")
                print("   - This may indicate:")
                print("     * Insufficient fuel connectivity between layers")
                print("     * Low vertical spread probability")
                print("     * Simulation too short to observe vertical spread")
                print("     * Terrain/vegetation conditions not conducive to vertical spread")
            
            # Performance metrics
            print(f"\n📈 PERFORMANCE METRICS")
            print("-" * 20)
            
            if hasattr(forest_model, 'stats') and forest_model.stats:
                sim_stats = forest_model.stats
                max_active = sim_stats.get('max_active_cells', 0)
                total_burned = sim_stats.get('burned_cells', 0)
                simulation_steps = sim_stats.get('simulation_steps', 0)
                
                print(f"🔥 Maximum Active Cells: {max_active}")
                print(f"🔥 Total Burned Cells: {total_burned}")
                print(f"⏱️  Simulation Steps: {simulation_steps}")
                
                if simulation_steps > 0:
                    burn_rate = total_burned / simulation_steps
                    print(f"📊 Average Burn Rate: {burn_rate:.1f} cells/step")
            
            # Create visualization
            print(f"\n🎨 Creating spread statistics visualization...")
            try:
                visualizer = ForestFireVisualizer(forest_model)
                
                # Save visualization
                output_dir = Path("results")
                output_dir.mkdir(exist_ok=True)
                
                # Create spread stats visualization
                fig, axes = visualizer.visualize_fire_spread_stats(
                    figsize=(12, 8), 
                    save_path=output_dir / "vertical_spread_analysis.png"
                )
                
                if fig is not None:
                    print(f"✅ Spread statistics visualization saved to: {output_dir / 'vertical_spread_analysis.png'}")
                    
                    # Add custom vertical spread analysis plot
                    import matplotlib.pyplot as plt
                    
                    # Create a new figure for detailed spread analysis
                    fig2, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))
                    
                    # Plot 1: Spread type distribution
                    spread_types = ['Vertical', 'Horizontal', 'Ember', 'Wind-Assisted']
                    spread_counts = [vertical_spread, horizontal_spread, ember_spread, wind_assisted]
                    colors = ['red', 'blue', 'orange', 'green']
                    
                    ax1.pie(spread_counts, labels=spread_types, colors=colors, autopct='%1.1f%%', startangle=90)
                    ax1.set_title('Fire Spread Type Distribution')
                    
                    # Plot 2: Vertical vs Horizontal ratio over time (if history available)
                    if hasattr(forest_model, 'fire_history') and forest_model.fire_history:
                        history = forest_model.fire_history
                        steps = [entry.get('step', i) for i, entry in enumerate(history)]
                        active_cells = [entry.get('active_cells', 0) for entry in history]
                        
                        ax2.plot(steps, active_cells, 'r-', linewidth=2)
                        ax2.set_xlabel('Simulation Step')
                        ax2.set_ylabel('Active Cells')
                        ax2.set_title('Active Fire Cells Over Time')
                        ax2.grid(True, alpha=0.3)
                    
                    # Plot 3: Spread efficiency metrics
                    metrics = ['Vertical\nEfficiency', 'Horizontal\nEfficiency', 'Ember\nEfficiency']
                    if total_ignitions > 0:
                        efficiencies = [
                            vertical_spread / total_ignitions * 100,
                            horizontal_spread / total_ignitions * 100,
                            ember_spread / total_ignitions * 100
                        ]
                    else:
                        efficiencies = [0, 0, 0]
                    
                    bars = ax3.bar(metrics, efficiencies, color=['red', 'blue', 'orange'])
                    ax3.set_ylabel('Efficiency (%)')
                    ax3.set_title('Spread Type Efficiency')
                    ax3.set_ylim(0, max(efficiencies) * 1.1 if efficiencies else 100)
                    
                    # Add value labels on bars
                    for bar, eff in zip(bars, efficiencies):
                        height = bar.get_height()
                        ax3.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                                f'{eff:.1f}%', ha='center', va='bottom')
                    
                    # Plot 4: Summary statistics
                    ax4.axis('off')
                    summary_text = f"""
                    FIRE SPREAD SUMMARY
                    
                    Total Spread Events: {total_spread}
                    Vertical Spread: {vertical_spread} ({vertical_spread/total_spread*100:.1f}%)
                    Horizontal Spread: {horizontal_spread} ({horizontal_spread/total_spread*100:.1f}%)
                    Ember Spread: {ember_spread} ({ember_spread/total_spread*100:.1f}%)
                    
                    Total Ignitions: {total_ignitions}
                    Wind-Assisted: {wind_assisted}
                    Slope-Assisted: {slope_assisted}
                    Barranco-Assisted: {barranco_assisted}
                    
                    Vertical/Horizontal Ratio: {vertical_spread/horizontal_spread:.3f if horizontal_spread > 0 else 0}
                    """
                    ax4.text(0.1, 0.9, summary_text, transform=ax4.transAxes, 
                            fontsize=10, verticalalignment='top', fontfamily='monospace')
                    
                    plt.tight_layout()
                    plt.savefig(output_dir / "detailed_vertical_spread_analysis.png", dpi=300, bbox_inches='tight')
                    print(f"✅ Detailed analysis visualization saved to: {output_dir / 'detailed_vertical_spread_analysis.png'}")
                    plt.close()
                    
                else:
                    print("⚠️  Could not create spread statistics visualization")
                    
            except Exception as e:
                print(f"⚠️  Visualization error: {e}")
            
        else:
            print("❌ No spread statistics available")
            print("   - This may indicate the simulation didn't run properly")
            print("   - Or spread statistics weren't tracked")
        
        # Clean up
        if hasattr(forest_model, 'cleanup'):
            forest_model.cleanup()
        
        print(f"\n✅ Vertical fire spread analysis completed!")
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("   Make sure you're using the pdal_env_new environment")
        print("   Run: conda activate pdal_env_new")
    except Exception as e:
        print(f"❌ Error during vertical fire spread test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_vertical_fire_spread()
