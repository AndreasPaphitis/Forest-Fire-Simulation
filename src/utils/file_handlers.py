"""
File Handling Utilities Module

Provides standardized file operations for consistent file handling across the codebase.
"""

import os
import glob
import shutil
import logging
import json
import pickle
import numpy as np
import csv
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional, Union, BinaryIO, TextIO, Tuple, Generator
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

logger = logging.getLogger(__name__)

class FileManager:
    """Centralized file management utilities."""
    
    @staticmethod
    def ensure_directory(directory_path: Union[str, Path]) -> Path:
        """
        Ensure a directory exists, creating it if necessary.
        
        Args:
            directory_path: Path to the directory
            
        Returns:
            Path object for the directory
        """
        path = Path(directory_path)
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    @staticmethod
    def find_files(base_dir: Union[str, Path], pattern: str, recursive: bool = True) -> List[Path]:
        """
        Find files matching a pattern.
        
        Args:
            base_dir: Base directory to search
            pattern: Glob pattern for matching files
            recursive: Whether to search recursively
            
        Returns:
            List of Path objects for matching files
        """
        base_path = Path(base_dir)
        if not base_path.exists():
            logger.warning(f"Directory does not exist: {base_dir}")
            return []
        
        search_pattern = os.path.join(str(base_path), "**", pattern) if recursive else os.path.join(str(base_path), pattern)
        return [Path(f) for f in glob.glob(search_pattern, recursive=recursive)]
    
    @staticmethod
    def safe_save_json(data: Any, filepath: Union[str, Path], indent: int = 2) -> bool:
        """
        Safely save data to a JSON file.
        
        Args:
            data: Data to save
            filepath: Path to save to
            indent: JSON indentation
            
        Returns:
            True if successful, False otherwise
        """
        try:
            filepath = Path(filepath)
            FileManager.ensure_directory(filepath.parent)
            
            # Write to temporary file first
            temp_path = filepath.with_suffix('.tmp')
            with open(temp_path, 'w') as f:
                json.dump(data, f, indent=indent)
            
            # Rename to target file (atomic operation)
            temp_path.replace(filepath)
            return True
        except Exception as e:
            logger.error(f"Error saving JSON to {filepath}: {e}")
            return False
    
    @staticmethod
    def safe_save_pickle(data: Any, filepath: Union[str, Path], protocol: int = pickle.HIGHEST_PROTOCOL) -> bool:
        """
        Safely save data to a pickle file.
        
        Args:
            data: Data to save
            filepath: Path to save to
            protocol: Pickle protocol version
            
        Returns:
            True if successful, False otherwise
        """
        try:
            filepath = Path(filepath)
            FileManager.ensure_directory(filepath.parent)
            
            # Write to temporary file first
            temp_path = filepath.with_suffix('.tmp')
            with open(temp_path, 'wb') as f:
                pickle.dump(data, f, protocol=protocol)
            
            # Rename to target file (atomic operation)
            temp_path.replace(filepath)
            return True
        except Exception as e:
            logger.error(f"Error saving pickle to {filepath}: {e}")
            return False
    
    @staticmethod
    def safe_load_json(filepath: Union[str, Path], default: Any = None) -> Any:
        """
        Safely load data from a JSON file.
        
        Args:
            filepath: Path to load from
            default: Default value if loading fails
            
        Returns:
            Loaded data or default
        """
        try:
            with open(filepath, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading JSON from {filepath}: {e}")
            return default
    
    @staticmethod
    def safe_load_pickle(filepath: Union[str, Path], default: Any = None) -> Any:
        """
        Safely load data from a pickle file.
        
        Args:
            filepath: Path to load from
            default: Default value if loading fails
            
        Returns:
            Loaded data or default
        """
        try:
            with open(filepath, 'rb') as f:
                return pickle.load(f)
        except Exception as e:
            logger.error(f"Error loading pickle from {filepath}: {e}")
            return default
            
    @staticmethod
    def get_checkpoint_path(base_dir: Union[str, Path], run_id: str, create_dir: bool = True) -> Path:
        """
        Get a standardized checkpoint path.
        
        Args:
            base_dir: Base directory for checkpoints
            run_id: Unique identifier for the run
            create_dir: Whether to create the directory if it doesn't exist
            
        Returns:
            Path to the checkpoint file
        """
        checkpoint_dir = Path(base_dir) / "checkpoints"
        if create_dir:
            checkpoint_dir.mkdir(parents=True, exist_ok=True)
        
        return checkpoint_dir / f"checkpoint_{run_id}.pkl"

    @staticmethod
    def save_array_as_csv(array: np.ndarray, filepath: Union[str, Path], header: Optional[List[str]] = None) -> bool:
        """
        Save a numpy array as a CSV file.
        
        Args:
            array: Numpy array to save
            filepath: Path to save to
            header: Optional header row
            
        Returns:
            True if successful, False otherwise
        """
        try:
            filepath = Path(filepath)
            FileManager.ensure_directory(filepath.parent)
            
            with open(filepath, 'w', newline='') as f:
                writer = csv.writer(f)
                if header:
                    writer.writerow(header)
                
                if array.ndim == 1:
                    writer.writerows([[x] for x in array])
                else:
                    writer.writerows(array)
            
            return True
        except Exception as e:
            logger.error(f"Error saving array as CSV to {filepath}: {e}")
            return False
    
    @staticmethod
    def load_csv_as_array(filepath: Union[str, Path], dtype=float, has_header: bool = False) -> Optional[np.ndarray]:
        """
        Load a CSV file as a numpy array.
        
        Args:
            filepath: Path to load from
            dtype: Data type for the array
            has_header: Whether the CSV has a header row
            
        Returns:
            Numpy array or None if loading fails
        """
        try:
            with open(filepath, 'r', newline='') as f:
                reader = csv.reader(f)
                
                # Skip header if present
                if has_header:
                    next(reader)
                
                # Read all rows
                data = [row for row in reader]
                
                # Convert to numpy array
                return np.array(data, dtype=dtype)
        except Exception as e:
            logger.error(f"Error loading CSV as array from {filepath}: {e}")
            return None

    @staticmethod
    def save_simulation_results(results: Dict[str, Any], output_dir: Union[str, Path], prefix: str = "") -> Dict[str, Path]:
        """
        Save simulation results to various files.
        
        Args:
            results: Dictionary of simulation results
            output_dir: Directory to save to
            prefix: Prefix for filenames
            
        Returns:
            Dictionary of saved file paths
        """
        output_dir = Path(output_dir)
        FileManager.ensure_directory(output_dir)
        
        saved_files = {}
        
        # Extract components
        stats = results.get('stats', {})
        history = results.get('history', [])
        forest_model = results.get('forest_model', None)
        
        # Save statistics
        if stats:
            stats_file = output_dir / f"{prefix}results.json"
            if FileManager.safe_save_json(stats, stats_file):
                saved_files['stats'] = stats_file
        
        # Save history if available
        if history:
            history_file = output_dir / f"{prefix}simulation_history.pkl"
            if FileManager.safe_save_pickle(history, history_file):
                saved_files['history'] = history_file
        
        # Save forest model if available
        if forest_model:
            model_file = output_dir / f"{prefix}final_forest_model_state.pkl"
            try:
                if hasattr(forest_model, 'save_state_to_file'):
                    forest_model.save_state_to_file(str(model_file))
                    saved_files['model'] = model_file
                else:
                    # Fallback - try pickling the entire model
                    if FileManager.safe_save_pickle(forest_model, model_file):
                        saved_files['model'] = model_file
            except Exception as e:
                logger.error(f"Error saving forest model: {e}")
        
        # Generate summary text file
        try:
            summary_file = output_dir / f"{prefix}simulation_summary.txt"
            
            with open(summary_file, 'w') as f:
                f.write("===== SIMULATION SUMMARY =====\n")
                
                # Add timestamp
                f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                
                # Add statistics
                if stats:
                    f.write("STATISTICS:\n")
                    for key, value in stats.items():
                        f.write(f"  {key}: {value}\n")
                    f.write("\n")
                
                # Add list of saved files
                f.write("SAVED FILES:\n")
                for key, path in saved_files.items():
                    f.write(f"  {key}: {path.name}\n")
            
            saved_files['summary'] = summary_file
        except Exception as e:
            logger.error(f"Error generating summary file: {e}")
        
        return saved_files

    @staticmethod
    def save_numpy_arrays(arrays: Dict[str, np.ndarray], base_dir: Union[str, Path], 
                           format: str = 'npy', compress: bool = False) -> Dict[str, Path]:
        """
        Save a dictionary of numpy arrays.
        
        Args:
            arrays: Dictionary of arrays to save
            base_dir: Directory to save to
            format: Format to save as ('npy', 'csv', 'txt')
            compress: Whether to compress the data (only for 'npy')
            
        Returns:
            Dictionary of saved file paths
        """
        base_dir = Path(base_dir)
        FileManager.ensure_directory(base_dir)
        
        saved_files = {}
        
        for name, array in arrays.items():
            try:
                if format == 'npy':
                    filepath = base_dir / f"{name}.npy"
                    if compress:
                        np.savez_compressed(filepath, array=array)
                        filepath = Path(f"{filepath}z")  # Add 'z' to extension
                    else:
                        np.save(filepath, array)
                    
                elif format == 'csv':
                    filepath = base_dir / f"{name}.csv"
                    FileManager.save_array_as_csv(array, filepath)
                    
                elif format == 'txt':
                    filepath = base_dir / f"{name}.txt"
                    np.savetxt(filepath, array)
                    
                else:
                    logger.error(f"Unsupported format: {format}")
                    continue
                
                saved_files[name] = filepath
                
            except Exception as e:
                logger.error(f"Error saving array '{name}': {e}")
        
        return saved_files
    
    @staticmethod
    def create_timestamped_dir(base_dir: Union[str, Path], prefix: str = "sim_") -> Path:
        """
        Create a timestamped directory for results.
        
        Args:
            base_dir: Base directory
            prefix: Prefix for directory name
            
        Returns:
            Path to the created directory
        """
        base_dir = Path(base_dir)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        result_dir = base_dir / f"{prefix}{timestamp}"
        result_dir.mkdir(parents=True, exist_ok=True)
        return result_dir
    
    @staticmethod
    def save_config_copy(config: Any, output_dir: Union[str, Path], filename: str = "simulation_config.json") -> Path:
        """
        Save a copy of the configuration to the output directory.
        
        Args:
            config: Configuration object or dictionary
            output_dir: Directory to save to
            filename: Name of the config file
            
        Returns:
            Path to the saved file
        """
        output_dir = Path(output_dir)
        config_dir = output_dir / "config"
        config_dir.mkdir(exist_ok=True, parents=True)
        
        config_file = config_dir / filename
        
        try:
            # Convert to dict if it's an object
            if hasattr(config, 'to_dict') and callable(config.to_dict):
                config_data = config.to_dict()
            else:
                config_data = config
            
            with open(config_file, 'w') as f:
                json.dump(config_data, f, indent=2, default=str)
            
            logger.info(f"Saved configuration to {config_file}")
            return config_file
            
        except Exception as e:
            logger.warning(f"Could not save configuration copy: {e}")
            return config_file
    
    @staticmethod
    def save_visualization(fig, output_dir: Union[str, Path], filename: str, 
                            dpi: int = 300, formats: List[str] = ['png']) -> List[Path]:
        """
        Save a matplotlib figure to multiple formats.
        
        Args:
            fig: Matplotlib figure
            output_dir: Directory to save to
            filename: Base filename (without extension)
            dpi: DPI for raster formats
            formats: List of formats to save as
            
        Returns:
            List of saved file paths
        """
        try:
            import matplotlib.pyplot as plt
            
            output_dir = Path(output_dir)
            FileManager.ensure_directory(output_dir)
            
            saved_files = []
            
            for fmt in formats:
                filepath = output_dir / f"{filename}.{fmt}"
                fig.savefig(filepath, dpi=dpi, bbox_inches='tight')
                saved_files.append(filepath)
            
            return saved_files
            
        except ImportError:
            logger.warning("matplotlib not available, skipping visualization save")
            return []
        except Exception as e:
            logger.error(f"Error saving visualization: {e}")
            return []

    @staticmethod
    def chunk_reader(file_path: Union[str, Path], chunk_size: int = 1024*1024) -> Generator[bytes, None, None]:
        """
        Read a file in chunks to reduce memory usage.
        
        Args:
            file_path: Path to the file
            chunk_size: Size of each chunk in bytes
            
        Yields:
            Chunks of the file
        """
        with open(file_path, 'rb') as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                yield chunk
    
    @staticmethod
    def md5_hash_file(file_path: Union[str, Path]) -> str:
        """
        Calculate MD5 hash of a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            MD5 hash as a hex string
        """
        try:
            import hashlib
            md5 = hashlib.md5()
            
            for chunk in FileManager.chunk_reader(file_path):
                md5.update(chunk)
            
            return md5.hexdigest()
        except Exception as e:
            logger.error(f"Error calculating MD5 hash: {e}")
            return ""

# Add HPC storage path handling
def resolve_hpc_storage_path(storage_path: str, 
                           job_id: Optional[str] = None, 
                           user: Optional[str] = None,
                           fallback_base: str = "/tmp") -> Path:
    """
    Resolve storage paths for HPC environments with proper absolute paths.
    
    This function addresses disk storage path issues by:
    - Converting relative paths to absolute paths
    - Using HPC-appropriate storage locations (scratch, shared storage)
    - Creating job-specific directories for isolation
    - Handling permission and quota issues
    
    Args:
        storage_path: Original storage path (may be relative)
        job_id: SLURM job ID for unique directory naming
        user: Username for storage location
        fallback_base: Fallback directory if HPC storage unavailable
        
    Returns:
        Resolved absolute path for HPC storage
    """
    logger.info(f"Resolving HPC storage path: {storage_path}")
    
    # Get environment variables commonly available on HPC systems
    if job_id is None:
        job_id = os.environ.get('SLURM_JOB_ID', f'local_{int(time.time())}')
    
    if user is None:
        user = os.environ.get('USER', os.environ.get('USERNAME', 'unknown'))
    
    # Try to resolve to absolute path if relative
    if not os.path.isabs(storage_path):
        logger.info(f"Converting relative path '{storage_path}' to absolute")
        
        # Common HPC storage locations (in order of preference)
        hpc_storage_candidates = [
            # Scratch storage (fastest, temporary)
            f"/scratch-shared/{user}",
            f"/scratch/{user}",
            f"/tmp/{user}",
            
            # Home directory (persistent but may have quotas)
            f"/home/{user}/simulation_storage",
            f"/gpfs/home1/{user}/simulation_storage",
            
            # Current working directory (fallback)
            os.getcwd(),
            
            # System temp (last resort)
            fallback_base
        ]
        
        # Find the first accessible storage location
        resolved_base = None
        for candidate in hpc_storage_candidates:
            try:
                candidate_path = Path(candidate)
                
                # Check if base directory exists or can be created
                if candidate_path.exists() or candidate_path.parent.exists():
                    # Test write permissions
                    test_dir = candidate_path / f"test_write_{job_id}"
                    test_dir.mkdir(parents=True, exist_ok=True)
                    
                    # Test file creation
                    test_file = test_dir / "write_test.tmp"
                    test_file.write_text("test")
                    test_file.unlink()
                    test_dir.rmdir()
                    
                    resolved_base = candidate_path
                    logger.info(f"Selected HPC storage base: {resolved_base}")
                    break
                    
            except (PermissionError, OSError, IOError) as e:
                logger.debug(f"Storage candidate {candidate} not accessible: {e}")
                continue
        
        if resolved_base is None:
            logger.warning("No accessible HPC storage found, using fallback")
            resolved_base = Path(fallback_base)
        
        # Create job-specific directory
        job_storage_dir = resolved_base / f"fire_sim_{job_id}" / storage_path
        
    else:
        # Already absolute path, but make it job-specific for isolation
        base_path = Path(storage_path)
        job_storage_dir = base_path.parent / f"{base_path.name}_{job_id}"
    
    # Ensure the directory structure exists
    try:
        job_storage_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created HPC storage directory: {job_storage_dir}")
        
        # Test write access
        test_file = job_storage_dir / ".write_test"
        test_file.write_text(f"Storage test for job {job_id}")
        test_file.unlink()
        
    except (PermissionError, OSError) as e:
        logger.error(f"Cannot create storage directory {job_storage_dir}: {e}")
        
        # Fallback to a safer location
        safer_path = Path(fallback_base) / f"fire_sim_fallback_{job_id}"
        safer_path.mkdir(parents=True, exist_ok=True)
        logger.warning(f"Using fallback storage: {safer_path}")
        return safer_path
    
    return job_storage_dir

def setup_hpc_output_directories(config: Dict[str, Any], 
                                job_id: Optional[str] = None) -> Dict[str, Path]:
    """
    Set up all output directories for HPC simulation with proper paths.
    
    Args:
        config: Configuration dictionary
        job_id: SLURM job ID
        
    Returns:
        Dictionary mapping directory types to resolved paths
    """
    logger.info("Setting up HPC output directories")
    
    if job_id is None:
        job_id = os.environ.get('SLURM_JOB_ID', f'local_{int(time.time())}')
    
    # Main output directory
    output_config = config.get('output', {})
    base_output_dir = output_config.get('output_dir', '~/results/production')
    
    # Expand user directory
    if base_output_dir.startswith('~'):
        base_output_dir = os.path.expanduser(base_output_dir)
    
    # Resolve main output directory
    main_output = resolve_hpc_storage_path(base_output_dir, job_id)
    
    # Create subdirectories
    directories = {
        'main_output': main_output,
        'results': main_output / "results",
        'logs': main_output / "logs", 
        'checkpoints': main_output / "checkpoints",
        'monitoring': main_output / "monitoring",
        'config_backup': main_output / "config"
    }
    
    # Disk storage directory (if enabled)
    if config.get('use_disk_storage', False):
        disk_storage_dir = config.get('disk_storage_dir', 'temp_simulation_states')
        
        # Use high-performance storage for disk cache if available
        disk_storage_path = resolve_hpc_storage_path(disk_storage_dir, job_id)
        directories['disk_storage'] = disk_storage_path
        
        # Update config with resolved path
        config['disk_storage_dir'] = str(disk_storage_path)
    
    # Create all directories
    created_dirs = {}
    for dir_type, dir_path in directories.items():
        try:
            dir_path.mkdir(parents=True, exist_ok=True)
            
            # Set appropriate permissions for shared HPC environments
            try:
                os.chmod(dir_path, 0o755)
            except OSError:
                pass  # Permissions might not be changeable
            
            created_dirs[dir_type] = dir_path
            logger.info(f"Created {dir_type} directory: {dir_path}")
            
        except (PermissionError, OSError) as e:
            logger.error(f"Failed to create {dir_type} directory {dir_path}: {e}")
            
            # Create in fallback location
            fallback_path = Path("/tmp") / f"fire_sim_fallback_{job_id}" / dir_type
            fallback_path.mkdir(parents=True, exist_ok=True)
            created_dirs[dir_type] = fallback_path
            logger.warning(f"Using fallback for {dir_type}: {fallback_path}")
    
    return created_dirs 