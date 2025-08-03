#!/usr/bin/env python3
"""
Production Simulation Runner for Snellius HPC
Runs full-scale forest fire simulations with comprehensive monitoring and error handling.
"""

import sys
import os
import time
import json
import signal
import traceback
from pathlib import Path
from datetime import datetime, timedelta

# Use the project's standardized path management
try:
    # Try to import from project paths first
    from src.utils.project_paths import setup_python_path, PROJECT_ROOT, SRC_DIR
    setup_python_path()
    CONFIG_PATH = PROJECT_ROOT / "hpc_deployment"
except ImportError:
    # Fallback for when we need to bootstrap the path
    current_file = Path(__file__).resolve()
    PROJECT_ROOT = current_file.parent.parent  # Go up from hpc_deployment to project root
    SRC_DIR = PROJECT_ROOT / "src"
    CONFIG_PATH = current_file.parent
    
    # Add to path for imports
    sys.path.insert(0, str(PROJECT_ROOT))
    sys.path.insert(0, str(SRC_DIR))

class ProductionSimulationRunner:
    """Production-ready simulation runner with monitoring and recovery."""
    
    def __init__(self, config_file=None):
        self.config_file = config_file or (CONFIG_PATH / "production_config.json")
        self.start_time = time.time()
        self.simulation_id = datetime.now().strftime("prod_%Y%m%d_%H%M%S")
        self.checkpoint_dir = None
        self.monitoring_data = []
        self.total_steps = 0
        self.completed_steps = 0
        
        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
        
        # Initialize monitoring
        self.last_checkpoint_time = time.time()
        self.last_memory_check = time.time()
        
    def _signal_handler(self, signum, frame):
        """Handle termination signals gracefully."""
        print(f"\n🛑 Received signal {signum}, initiating graceful shutdown...")
        self._save_checkpoint("emergency_shutdown")
        self._save_monitoring_data()
        print("✅ Emergency checkpoint saved")
        sys.exit(1)
    
    def load_and_validate_config(self):
        """Load and validate the production configuration."""
        print("⚙️  Loading Production Configuration")
        print("=" * 50)
        
        if not self.config_file.exists():
            print(f"❌ Config file not found: {self.config_file}")
            return False
        
        try:
            with open(self.config_file, 'r') as f:
                self.config_dict = json.load(f)
            
            print(f"✅ Config loaded from: {self.config_file}")
            
            # Check for critical TODOs
            critical_paths = [
                ('terrain', 'dem_file'),
                ('vegetation', 'lidar_data_dir'),
                ('hpc', 'email_address')
            ]
            
            missing_configs = []
            for section, key in critical_paths:
                value = self.config_dict.get(section, {}).get(key, '')
                if not value or str(value).startswith('TODO'):
                    missing_configs.append(f"{section}.{key}")
            
            if missing_configs:
                print("❌ CRITICAL: The following config values must be updated:")
                for config in missing_configs:
                    print(f"   - {config}")
                print("   Update these in production_config.json before running!")
                return False
            
            # Validate file paths exist
            dem_file = self.config_dict.get('terrain', {}).get('dem_file')
            lidar_dir = self.config_dict.get('vegetation', {}).get('lidar_data_dir')
            
            if dem_file and not Path(dem_file).exists():
                print(f"❌ DEM file not found: {dem_file}")
                return False
            
            if lidar_dir and not Path(lidar_dir).exists():
                print(f"❌ LiDAR directory not found: {lidar_dir}")
                return False
            
            print("✅ All critical paths validated")
            return True
            
        except Exception as e:
            print(f"❌ Error loading config: {e}")
            return False
    
    def setup_output_directories(self):
        """Set up output and checkpoint directories."""
        print("\n📁 Setting Up Output Directories")
        print("=" * 50)
        
        try:
            # Create a preliminary ModelConfig to access directory resolution methods
            from src.config.config_tools import ModelConfig
            
            # Extract output configuration from JSON config
            output_config = self.config_dict.get('output', {})
            main_output_dir = output_config.get('output_dir', 'results')
            
            # Create a temporary config object with output settings
            temp_config = ModelConfig(
                output_dir=main_output_dir,
                results_output_dir=output_config.get('results_output_dir'),
                logs_output_dir=output_config.get('logs_output_dir'),
                checkpoints_output_dir=output_config.get('checkpoints_output_dir'),
                monitoring_output_dir=output_config.get('monitoring_output_dir'),
                temp_storage_dir=output_config.get('temp_storage_dir')
            )
            
            # Use the configuration methods to resolve all directories
            directories = temp_config.ensure_output_directories(create_dirs=True)
            
            # Create simulation-specific subdirectory in main output
            self.output_dir = directories['main_output'] / self.simulation_id
            self.output_dir.mkdir(parents=True, exist_ok=True)
            
            # Set up all directory paths using resolved paths or subdirectories  
            self.results_dir = directories['results'] if temp_config.results_output_dir else self.output_dir / "results"
            self.logs_dir = directories['logs'] if temp_config.logs_output_dir else self.output_dir / "logs"
            self.checkpoints_dir = directories['checkpoints'] if temp_config.checkpoints_output_dir else self.output_dir / "checkpoints"
            self.monitoring_dir = directories['monitoring'] if temp_config.monitoring_output_dir else self.output_dir / "monitoring"
            
            # Create the final directories
            for directory in [self.results_dir, self.logs_dir, self.checkpoints_dir, self.monitoring_dir]:
                directory.mkdir(parents=True, exist_ok=True)
            
            # Disk storage directory if enabled (using temp_storage_dir)
            if self.config_dict.get('use_disk_storage', False):
                if temp_config.temp_storage_dir:
                    disk_dir = directories['temp_storage']
                else:
                    # Use default temp storage in output subdir
                    disk_dir = self.output_dir / "temp_simulation_states"
                
                disk_dir.mkdir(parents=True, exist_ok=True)
                # Store as temp_storage_dir for consistency
                self.config_dict['temp_storage_dir'] = str(disk_dir)
            
            print(f"✅ Output directory: {self.output_dir}")
            print(f"✅ Results directory: {self.results_dir}")
            print(f"✅ Logs directory: {self.logs_dir}")
            print(f"✅ Checkpoints directory: {self.checkpoints_dir}")
            
            # Save config copy
            config_copy = self.output_dir / "config_used.json"
            with open(config_copy, 'w') as f:
                json.dump(self.config_dict, f, indent=2)
            print(f"✅ Config saved to: {config_copy}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error setting up directories: {e}")
            return False
    
    def initialize_simulation(self):
        """Initialize the simulation with auto-sizing if needed."""
        print("\n🚀 Initializing Production Simulation")
        print("=" * 50)
        
        try:
            # Import required modules
            from src.config.config_tools import ModelConfig, set_global_config
            from src.core.forest_model import create_forest_model
            from src.core.fire_simulation_engine import FireSimulationEngine
            from src.core.vegetation_data_integration import TiledLiDARIntegration
            
            print("✅ All modules imported successfully")
            
            # Set up output directories using existing method
            if not self.setup_output_directories():
                raise Exception("Failed to setup output directories")
            
            # Extract HPC configuration from config
            hpc_config = self.config_dict.get('hpc', {})
            
            # Get HPC resource information for logging
            job_id = os.environ.get('SLURM_JOB_ID', 'local_test')
            allocated_memory_gb = float(os.environ.get('SLURM_MEM_PER_NODE', '120')) / 1024  # Convert MB to GB
            allocated_cores = int(os.environ.get('SLURM_CPUS_PER_TASK', '32'))
            
            print(f"🖥️  HPC Resources: {allocated_memory_gb}GB memory, {allocated_cores} cores")
            print(f"📁 Output directories already configured by setup_output_directories()")
            
            # Create a ModelConfig with the configuration parameters
            preliminary_config = ModelConfig(
                simulation_type=self.config_dict.get('simulation_type', 'standard'),
                grid_size=tuple(self.config_dict.get('grid_size', [1000, 1000])),
                num_layers=self.config_dict.get('num_layers', 10),
                layer_height=self.config_dict.get('layer_height', 2.0),
                model_resolution=self.config_dict.get('model_resolution', 2.0),
                max_steps=self.config_dict.get('max_steps', 200),
                memory_optimization_level=self.config_dict.get('memory_optimization_level', 2),
                wind_speed=self.config_dict.get('wind_speed', 8.0),
                wind_direction=self.config_dict.get('wind_direction', 45.0),
                use_disk_storage=self.config_dict.get('use_disk_storage', True),
                temp_storage_dir=self.config_dict.get('temp_storage_dir', ''),
                store_full_states=self.config_dict.get('store_full_states', True),
                dem_file=self.config_dict.get('terrain', {}).get('dem_file', None),
                auto_size_from_lidar=self.config_dict.get('auto_size_from_lidar', False),
                lidar_data_dir=self.config_dict.get('vegetation', {}).get('lidar_data_dir', None),
                # Extract HPC parameters from nested structure
                tile_size=hpc_config.get('tile_size', 200),
                tile_overlap_ratio=hpc_config.get('tile_overlap_ratio', 0.05),
                max_parallel_tiles=hpc_config.get('max_parallel_tiles', 8),
                reserve_cpus=hpc_config.get('reserve_cpus', 4)
            )
            
            # Set the global configuration
            set_global_config(preliminary_config)
            print("✅ Global configuration initialized")
            
            # Handle auto-sizing from LiDAR
            if self.config_dict.get('vegetation', {}).get('auto_size_from_lidar', False):
                print("🔍 Auto-sizing from LiDAR data...")
                
                lidar_integration = TiledLiDARIntegration(
                    config=preliminary_config,
                    forest_model=None
                )
                
                # Calculate optimal parameters
                auto_params = lidar_integration.calculate_optimal_grid_size()
                
                if auto_params:
                    # auto_params is a tuple: (grid_size, geo_bounds, actual_resolution)
                    grid_size, geo_bounds, actual_resolution = auto_params
                    self.config_dict['grid_size'] = list(grid_size)  # Convert tuple to list for JSON compatibility
                    self.config_dict['geo_bounds'] = geo_bounds
                    self.config_dict['model_resolution'] = actual_resolution
                    
                    # Try to get optimal layers
                    try:
                        optimal_layers = lidar_integration._determine_optimal_num_layers(
                            self.config_dict.get('vegetation', {}).get('lidar_data_dir')
                        )
                        if optimal_layers and optimal_layers > 0:
                            self.config_dict['num_layers'] = optimal_layers
                    except:
                        pass  # Use config default
                    
                    print(f"✅ Auto-sized grid: {self.config_dict['grid_size']}")
                    print(f"✅ Resolution: {actual_resolution:.2f}m")
                    print(f"✅ Geographic bounds: {geo_bounds}")
                    print(f"✅ Layers: {self.config_dict.get('num_layers', 'using default')}")
                else:
                    print("❌ Auto-sizing failed, using config defaults")
                    return False
            
            # Create ModelConfig
            model_config = ModelConfig(
                simulation_type=self.config_dict.get('simulation_type', 'standard'),
                grid_size=tuple(self.config_dict.get('grid_size', [1000, 1000])),
                num_layers=self.config_dict.get('num_layers', 10),
                layer_height=self.config_dict.get('layer_height', 2.0),
                model_resolution=self.config_dict.get('model_resolution', 2.0),
                max_steps=self.config_dict.get('max_steps', 200),
                memory_optimization_level=self.config_dict.get('memory_optimization_level', 2),
                wind_speed=self.config_dict.get('wind_speed', 8.0),
                wind_direction=self.config_dict.get('wind_direction', 45.0),
                use_disk_storage=self.config_dict.get('use_disk_storage', True),
                temp_storage_dir=self.config_dict.get('temp_storage_dir', ''),
                store_full_states=self.config_dict.get('store_full_states', True),
                dem_file=self.config_dict.get('dem_file', None),
                auto_size_from_lidar=self.config_dict.get('auto_size_from_lidar', False),
                lidar_data_dir=self.config_dict.get('vegetation', {}).get('lidar_data_dir', None),
                geo_bounds=self.config_dict.get('geo_bounds', None),
                output_dir=str(self.results_dir),
                # Extract HPC parameters from nested structure
                tile_size=hpc_config.get('tile_size', 200),
                tile_overlap_ratio=hpc_config.get('tile_overlap_ratio', 0.05),
                max_parallel_tiles=hpc_config.get('max_parallel_tiles', 8),
                reserve_cpus=hpc_config.get('reserve_cpus', 4)
            )
            
            self.model_config = model_config
            self.total_steps = model_config.max_steps
            
            print(f"✅ ModelConfig created:")
            print(f"   Grid: {model_config.grid_size} ({model_config.grid_size[0] * model_config.grid_size[1]:,} cells)")
            print(f"   Layers: {model_config.num_layers}")
            print(f"   Resolution: {model_config.model_resolution}m")
            print(f"   Max steps: {model_config.max_steps}")
            
            # Create forest model with memory optimization for large grids
            print("\n🌲 Creating memory-optimized forest model...")
            print("🧠 Using sparse storage to handle large grids efficiently")
            
            # Extract HPC-specific parameters and pass them to the forest model
            model_kwargs = {
                'config': model_config,
                'use_sparse_storage': hpc_config.get('use_sparse_storage', True),
                'tile_size': hpc_config.get('tile_size', 200),
                'use_tiling': True
            }
            
            self.forest_model = create_forest_model(
                model_type='memory_optimized',  # Force memory-optimized version
                **model_kwargs
            )
            
            print(f"✅ Forest model created: {type(self.forest_model).__name__}")
            total_cells = model_config.grid_size[0] * model_config.grid_size[1] * model_config.num_layers
            print(f"📊 Total cell-layers: {total_cells:,} (using sparse storage)")
            
            # Initialize with LiDAR data if specified
            if self.config_dict.get('vegetation', {}).get('use_lidar', False):
                print("🌿 Initializing with LiDAR vegetation data...")
                
                lidar_integration = TiledLiDARIntegration(
                    config=model_config,
                    forest_model=self.forest_model
                )
                
                lidar_integration.initialize_forest_model()
                print("✅ LiDAR vegetation data loaded")
            
            # Load terrain data if specified
            if self.config_dict.get('terrain', {}).get('use_terrain', False):
                dem_file = self.config_dict.get('terrain', {}).get('dem_file')
                if dem_file:
                    print(f"🏔️  Loading terrain data from: {dem_file}")
                    success = self.forest_model.load_terrain_data(dem_file)
                    if success:
                        print("✅ Terrain data loaded successfully")
                        
                        # Initialize terrain-aware wind
                        terrain_strength = self.config_dict.get('terrain', {}).get('terrain_effect_strength', 0.8)
                        self.forest_model.initialize_terrain_wind(
                            model_config.wind_direction,
                            model_config.wind_speed,
                            terrain_strength
                        )
                        print("✅ Terrain-aware wind field initialized")
                    else:
                        print("⚠️  Terrain data loading failed, using uniform wind")
                        self.forest_model.initialize_wind(model_config.wind_direction, model_config.wind_speed)
                else:
                    self.forest_model.initialize_wind(model_config.wind_direction, model_config.wind_speed)
            else:
                self.forest_model.initialize_wind(model_config.wind_direction, model_config.wind_speed)
            
            # Set ignition points
            ignition_points = self.config_dict.get('ignition_points', [{'x': 'AUTO_CENTER', 'y': 'AUTO_CENTER', 'z': 0}])
            
            for point in ignition_points:
                x = point['x']
                y = point['y']
                z = point.get('z', 0)
                
                # Handle auto-center
                if x == 'AUTO_CENTER':
                    x = model_config.grid_size[0] // 2
                if y == 'AUTO_CENTER':
                    y = model_config.grid_size[1] // 2
                
                self.forest_model.set_ignition(x, y, z)
                print(f"✅ Ignition set at ({x}, {y}, {z})")
            
            # Create simulation engine
            print("\n⚡ Creating simulation engine...")
            self.engine = FireSimulationEngine(
                forest_model=self.forest_model,
                config=model_config
            )
            print("✅ Simulation engine created")
            
            return True
            
        except Exception as e:
            print(f"❌ Simulation initialization failed: {e}")
            traceback.print_exc()
            return False
    
    def _monitor_progress(self, step, stats):
        """Monitor simulation progress and handle checkpointing."""
        current_time = time.time()
        self.completed_steps = step
        
        # Update monitoring data
        self.monitoring_data.append({
            'step': step,
            'timestamp': current_time,
            'active_cells': stats.get('active_cells', 0),
            'burned_cells': stats.get('burned_cells', 0),
            'elapsed_time': current_time - self.start_time
        })
        
        # Progress reporting
        if step % 10 == 0:  # Report every 10 steps
            elapsed = current_time - self.start_time
            remaining_steps = self.total_steps - step
            
            if step > 0:
                time_per_step = elapsed / step
                eta_seconds = remaining_steps * time_per_step
                eta = str(timedelta(seconds=int(eta_seconds)))
            else:
                eta = "unknown"
            
            print(f"📊 Step {step}/{self.total_steps} "
                  f"({step/self.total_steps*100:.1f}%) - "
                  f"Active: {stats.get('active_cells', 0):,}, "
                  f"Burned: {stats.get('burned_cells', 0):,} - "
                  f"ETA: {eta}")
        
        # Checkpoint saving
        checkpoint_interval = self.config_dict.get('output', {}).get('checkpoint_interval', 50)
        if step % checkpoint_interval == 0 and step > 0:
            self._save_checkpoint(f"step_{step}")
        
        # Memory monitoring
        if current_time - self.last_memory_check > 60:  # Every minute
            self._check_memory_usage()
            self.last_memory_check = current_time
        
        return True  # Continue simulation
    
    def _save_checkpoint(self, checkpoint_name):
        """Save a simulation checkpoint."""
        try:
            checkpoint_path = self.checkpoints_dir / f"{checkpoint_name}.pkl"
            
            checkpoint_data = {
                'step': self.completed_steps,
                'forest_model_state': self.forest_model.state.copy() if hasattr(self.forest_model, 'state') else None,
                'config': self.config_dict,
                'simulation_id': self.simulation_id,
                'timestamp': time.time(),
                'monitoring_data': self.monitoring_data[-100:]  # Last 100 data points
            }
            
            import pickle
            with open(checkpoint_path, 'wb') as f:
                pickle.dump(checkpoint_data, f)
            
            print(f"💾 Checkpoint saved: {checkpoint_path}")
            
        except Exception as e:
            print(f"⚠️  Failed to save checkpoint: {e}")
    
    def _check_memory_usage(self):
        """Monitor memory usage and warn if approaching limits."""
        try:
            import psutil
            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024
            
            # Get SLURM memory limit if available
            slurm_mem = os.environ.get('SLURM_MEM_PER_NODE')
            if slurm_mem:
                slurm_mem_mb = int(slurm_mem)
                usage_percent = (memory_mb / slurm_mem_mb) * 100
                
                if usage_percent > 90:
                    print(f"🚨 HIGH MEMORY USAGE: {memory_mb:.1f}MB ({usage_percent:.1f}%)")
                elif usage_percent > 75:
                    print(f"⚠️  Memory usage: {memory_mb:.1f}MB ({usage_percent:.1f}%)")
                
        except ImportError:
            pass  # psutil not available
        except Exception as e:
            print(f"⚠️  Memory check failed: {e}")
    
    def _save_monitoring_data(self):
        """Save monitoring data to file."""
        try:
            monitoring_file = self.monitoring_dir / "simulation_monitoring.json"
            with open(monitoring_file, 'w') as f:
                json.dump(self.monitoring_data, f, indent=2)
        except Exception as e:
            print(f"⚠️  Failed to save monitoring data: {e}")
    
    def run_simulation(self):
        """Run the main simulation."""
        print("\n🔥 Starting Production Simulation")
        print("=" * 50)
        
        try:
            # Start simulation with monitoring
            results = self.engine.run_simulation(
                max_steps=self.total_steps,
                store_history=self.model_config.store_full_states,
                step_callback=self._monitor_progress,
                stop_when_fire_extinguished=True
            )
            
            # Save final results
            final_results_file = self.results_dir / "final_results.json"
            
            final_results = {
                'simulation_id': self.simulation_id,
                'config_used': self.config_dict,
                'results': results.get('stats', {}),
                'total_runtime': time.time() - self.start_time,
                'completed_steps': self.completed_steps,
                'total_steps': self.total_steps,
                'completion_rate': self.completed_steps / self.total_steps if self.total_steps > 0 else 0
            }
            
            with open(final_results_file, 'w') as f:
                json.dump(final_results, f, indent=2, default=str)
            
            # === COMPREHENSIVE RESULT SAVING ===
            print("\n💾 Saving comprehensive results...")
            
            # Save using the FileManager utility
            try:
                from src.utils.file_handlers import FileManager
                saved_files = FileManager.save_simulation_results(
                    results=results,
                    output_dir=self.results_dir,
                    prefix="production_"
                )
                print(f"✅ Saved {len(saved_files)} result files:")
                for file_type, file_path in saved_files.items():
                    print(f"   {file_type}: {file_path}")
                
            except Exception as e:
                print(f"⚠️  Error with FileManager saving: {e}")
                import traceback
                traceback.print_exc()
                # Fallback to manual saving
                self._save_comprehensive_results(results)
            
            # Generate visualizations if enabled
            if self.config_dict.get('save_visualizations', False):
                print("🎨 Generating visualizations...")
                try:
                    self._generate_visualizations(results)
                    print("✅ Visualizations generated")
                except Exception as e:
                    print(f"⚠️  Visualization generation failed: {e}")
                    import traceback
                    traceback.print_exc()
            else:
                print("⚠️  Visualizations disabled in config")
            
            # Save animation data if enabled
            if self.config_dict.get('animation', {}).get('enabled', False):
                print("🎬 Saving animation data...")
                try:
                    self._save_animation_data(results)
                    print("✅ Animation data saved")
                except Exception as e:
                    print(f"⚠️  Animation data saving failed: {e}")
                    import traceback
                    traceback.print_exc()
            else:
                print("⚠️  Animation disabled in config")
            
            # === END COMPREHENSIVE SAVING ===
            
            print(f"\n✅ Simulation completed successfully!")
            print(f"📊 Final Statistics:")
            stats = results.get('stats', {})
            print(f"   Steps completed: {stats.get('steps', 0)}")
            print(f"   Total burned cells: {stats.get('total_burned_cells', 0):,}")
            print(f"   Final active cells: {stats.get('final_active_cells', 0):,}")
            print(f"   Runtime: {time.time() - self.start_time:.1f} seconds")
            print(f"📁 Results saved to: {self.results_dir}")
            
            return True
            
        except Exception as e:
            print(f"❌ Simulation failed: {e}")
            traceback.print_exc()
            self._save_checkpoint("error_state")
            return False
    
    def _save_comprehensive_results(self, results):
        """Fallback method to save all results manually."""
        try:
            print("   Using fallback saving method...")
            
            # Save model state
            if 'forest_model' in results and results['forest_model'] is not None:
                model_file = self.results_dir / "production_forest_model_state.pkl"
                try:
                    with open(model_file, 'wb') as f:
                        import pickle
                        pickle.dump(results['forest_model'], f)
                    print(f"   ✅ Model state: {model_file}")
                except Exception as e:
                    print(f"   ❌ Model state failed: {e}")
            
            # Save history if available
            if 'history' in results and results['history']:
                history_file = self.results_dir / "production_simulation_history.pkl"
                try:
                    with open(history_file, 'wb') as f:
                        import pickle
                        pickle.dump(results['history'], f)
                    print(f"   ✅ History: {history_file}")
                except Exception as e:
                    print(f"   ❌ History failed: {e}")
                
            # Save detailed stats
            if 'stats' in results and results['stats']:
                stats_file = self.results_dir / "production_detailed_stats.json"
                try:
                    with open(stats_file, 'w') as f:
                        json.dump(results['stats'], f, indent=2, default=str)
                    print(f"   ✅ Detailed stats: {stats_file}")
                except Exception as e:
                    print(f"   ❌ Detailed stats failed: {e}")
            
            # Save simulation summary text file
            summary_file = self.results_dir / "production_simulation_summary.txt"
            try:
                with open(summary_file, 'w') as f:
                    f.write("===== PRODUCTION SIMULATION SUMMARY =====\n")
                    f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                    f.write(f"Simulation ID: {self.simulation_id}\n")
                    f.write(f"Total runtime: {time.time() - self.start_time:.1f} seconds\n")
                    f.write(f"Steps completed: {self.completed_steps}/{self.total_steps}\n\n")
                    
                    if 'stats' in results:
                        f.write("STATISTICS:\n")
                        for key, value in results['stats'].items():
                            f.write(f"  {key}: {value}\n")
                        f.write("\n")
                        
                    f.write("CONFIGURATION USED:\n")
                    f.write(json.dumps(self.config_dict, indent=2, default=str))
                    
                print(f"   ✅ Summary: {summary_file}")
            except Exception as e:
                print(f"   ❌ Summary failed: {e}")
                
        except Exception as e:
            print(f"⚠️  Comprehensive saving failed: {e}")
            import traceback
            traceback.print_exc()
    
    def _generate_visualizations(self, results):
        """Generate visualizations from simulation results."""
        try:
            from src.utils.visualization import generate_standard_visualizations
            
            forest_model = results.get('forest_model')
            if forest_model:
                viz_dir = self.results_dir / "visualizations"
                viz_dir.mkdir(exist_ok=True)
                
                saved_viz = generate_standard_visualizations(
                    forest_model=forest_model,
                    output_dir=viz_dir,
                    include_animation=self.config_dict.get('animation', {}).get('enabled', False)
                )
                
                print(f"   Generated {len(saved_viz)} visualizations:")
                for viz_type, viz_path in saved_viz.items():
                    print(f"     {viz_type}: {viz_path}")
            else:
                print("   ❌ No forest model available for visualization")
                
        except ImportError as e:
            print(f"⚠️  Visualization module not available: {e}")
        except Exception as e:
            print(f"⚠️  Visualization generation error: {e}")
            
    def _save_animation_data(self, results):
        """Save animation-specific data for post-processing."""
        try:
            animation_config = self.config_dict.get('animation', {})
            
            # Create animation data directory
            animation_dir = self.results_dir / "animation_data"
            animation_dir.mkdir(exist_ok=True)
            
            # Save animation configuration
            animation_config_file = animation_dir / "animation_config.json"
            with open(animation_config_file, 'w') as f:
                json.dump(animation_config, f, indent=2)
            print(f"   Animation config: {animation_config_file}")
            
            # Save checkpoints for animation if enabled
            if animation_config.get('checkpoint_enhancement', False):
                checkpoint_list = []
                for checkpoint_file in self.checkpoints_dir.glob("*.pkl"):
                    checkpoint_list.append(str(checkpoint_file))
                
                checkpoint_index = animation_dir / "checkpoint_index.json"
                with open(checkpoint_index, 'w') as f:
                    json.dump({
                        'checkpoints': checkpoint_list,
                        'total_steps': self.total_steps,
                        'completed_steps': self.completed_steps,
                        'simulation_id': self.simulation_id
                    }, f, indent=2)
                print(f"   Checkpoint index: {checkpoint_index}")
            
            # Save metadata for animation
            if animation_config.get('save_ember_metadata', False):
                metadata = {
                    'grid_size': self.config_dict.get('grid_size', [600, 600]),
                    'num_layers': self.config_dict.get('num_layers', 20),
                    'model_resolution': self.config_dict.get('model_resolution', 33.33),
                    'geo_bounds': self.config_dict.get('geo_bounds'),
                    'crs': self.config_dict.get('crs', 'EPSG:25828'),
                    'ember_parameters': {
                        'ember_probability': self.config_dict.get('ember_probability', 0.1),
                        'ember_distance': self.config_dict.get('ember_distance', 5),
                        'ember_ignition': self.config_dict.get('ember_ignition', 0.3)
                    }
                }
                
                metadata_file = animation_dir / "simulation_metadata.json"
                with open(metadata_file, 'w') as f:
                    json.dump(metadata, f, indent=2)
                print(f"   Simulation metadata: {metadata_file}")
                
            # Save wind conditions if enabled
            if animation_config.get('save_wind_conditions', False):
                wind_data = {
                    'wind_speed': self.config_dict.get('wind_speed', 5.0),
                    'wind_direction': self.config_dict.get('wind_direction', 90.0),
                    'wind_influence': self.config_dict.get('wind_influence_on_spread', 0.5),
                    'terrain_effects': self.config_dict.get('terrain', {}).get('use_terrain', False)
                }
                
                wind_file = animation_dir / "wind_conditions.json"
                with open(wind_file, 'w') as f:
                    json.dump(wind_data, f, indent=2)
                print(f"   Wind conditions: {wind_file}")
                
        except Exception as e:
            print(f"⚠️  Animation data saving error: {e}")
            import traceback
            traceback.print_exc()
    
    def cleanup(self):
        """Perform cleanup operations."""
        print("\n🧹 Cleaning Up")
        print("=" * 50)
        
        # Save final monitoring data
        self._save_monitoring_data()
        
        # Final checkpoint
        self._save_checkpoint("final_state")
        
        # Summary report
        total_runtime = time.time() - self.start_time
        print(f"📈 Simulation Summary:")
        print(f"   Simulation ID: {self.simulation_id}")
        print(f"   Total runtime: {total_runtime:.1f} seconds ({total_runtime/3600:.2f} hours)")
        print(f"   Steps completed: {self.completed_steps}/{self.total_steps}")
        print(f"   Output directory: {self.output_dir}")

def main():
    """Main function to run production simulation."""
    print("🏭 Production Forest Fire Simulation - Snellius HPC")
    print("=" * 60)
    print(f"Start time: {datetime.now()}")
    print(f"Project root: {PROJECT_ROOT}")
    
    # Get config file from command line argument
    config_file = None
    if len(sys.argv) > 1:
        config_file = Path(sys.argv[1])
        if not config_file.is_absolute():
            config_file = CONFIG_PATH / config_file
    else:
        config_file = CONFIG_PATH / "production_config.json"
    
    print(f"Config file: {config_file}")
    
    # Create and run simulation
    runner = ProductionSimulationRunner(config_file)
    
    try:
        # Setup phases
        if not runner.load_and_validate_config():
            print("❌ Configuration validation failed")
            return 1
        
        if not runner.setup_output_directories():
            print("❌ Output directory setup failed")
            return 1
        
        if not runner.initialize_simulation():
            print("❌ Simulation initialization failed")
            return 1
        
        # Run simulation
        if not runner.run_simulation():
            print("❌ Simulation execution failed")
            return 1
        
        # Success
        print("\n🎉 PRODUCTION SIMULATION COMPLETED SUCCESSFULLY!")
        return 0
        
    except KeyboardInterrupt:
        print("\n🛑 Simulation interrupted by user")
        return 1
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        traceback.print_exc()
        return 1
    finally:
        runner.cleanup()

if __name__ == "__main__":
    sys.exit(main()) 