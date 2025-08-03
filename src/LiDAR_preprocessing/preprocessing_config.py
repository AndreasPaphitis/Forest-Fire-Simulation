"""
Unified Configuration System for LiDAR Preprocessing

This module provides a standardized configuration system for all preprocessing steps:
1. Height normalization
2. NRD calculation
3. PAD calculation

It centralizes default values, parameter validation, and configuration loading/saving.
"""

import os
import sys
import json
import argparse
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, field, asdict
import logging
import datetime

# Add parent directory to sys.path to enable relative imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.dirname(current_dir))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

# Try to import from project utilities
try:
    from src.utils.logging_utils import get_logger
    from src.utils.parameter_validation import validate_parameter
    logger = get_logger(__name__)
except ImportError:
    # Fallback to standard logging
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    # Simple parameter validation function
    def validate_parameter(value, param_type, min_val=None, max_val=None, allowed_values=None):
        if param_type and not isinstance(value, param_type):
            raise TypeError(f"Expected {param_type}, got {type(value)}")
        
        if min_val is not None and value < min_val:
            raise ValueError(f"Value {value} is less than minimum {min_val}")
            
        if max_val is not None and value > max_val:
            raise ValueError(f"Value {value} is greater than maximum {max_val}")
            
        if allowed_values is not None and value not in allowed_values:
            raise ValueError(f"Value {value} is not in allowed values {allowed_values}")
            
        return value

# Default configuration values
@dataclass
class HeightNormalizationConfig:
    """Configuration for height normalization process."""
    input_dir: str = field(default="")
    output_dir: str = field(default="")
    num_workers: int = field(default=4)
    
    def validate(self):
        """Validate configuration parameters."""
        if not self.input_dir:
            raise ValueError("Input directory must be specified")
        if not self.output_dir:
            raise ValueError("Output directory must be specified")
        validate_parameter(self.num_workers, int, min_val=1)
        return True

@dataclass
class NRDConfig:
    """Configuration for NRD calculation process."""
    input_dir: str = field(default="")
    output_dir: str = field(default="")
    vegetation_classes: List[int] = field(default_factory=lambda: [3, 4, 5])
    bin_size: float = field(default=2.0)
    min_points_percent: float = field(default=0.1)
    raster_resolution: float = field(default=5.0)
    create_rasters: bool = field(default=True)
    handle_negative_heights: bool = field(default=True)
    filter_negative_heights: bool = field(default=True)
    filter_artifacts: bool = field(default=True)
    filter_method: str = field(default='statistical')
    z_score_threshold: float = field(default=2.5)
    slope_threshold: float = field(default=45.0)
    min_valid_height: float = field(default=-1.0)
    show_cumulative: bool = field(default=True)
    parallel_processing: bool = field(default=True)
    max_workers: int = field(default=4)
    
    def validate(self):
        """Validate configuration parameters."""
        if not self.input_dir:
            raise ValueError("Input directory must be specified")
        if not self.output_dir:
            raise ValueError("Output directory must be specified")
        validate_parameter(self.bin_size, float, min_val=0.1, max_val=10.0)
        validate_parameter(self.min_points_percent, float, min_val=0.0, max_val=100.0)
        validate_parameter(self.raster_resolution, float, min_val=0.1, max_val=100.0)
        validate_parameter(self.filter_method, str, allowed_values=['simple', 'statistical', 'local', 'combined'])
        validate_parameter(self.z_score_threshold, float, min_val=0.1)
        validate_parameter(self.slope_threshold, float, min_val=0.1, max_val=90.0)
        validate_parameter(self.max_workers, int, min_val=1)
        return True

@dataclass
class PADConfig:
    """Configuration for PAD calculation process."""
    input_dir: str = field(default="")
    output_dir: str = field(default="")
    extinction_coefficient: float = field(default=0.5)
    bin_size: float = field(default=2.0)
    create_visualizations: bool = field(default=True)
    parallel_processing: bool = field(default=True)
    max_workers: int = field(default=4)
    
    def validate(self):
        """Validate configuration parameters."""
        if not self.input_dir:
            raise ValueError("Input directory must be specified")
        if not self.output_dir:
            raise ValueError("Output directory must be specified")
        validate_parameter(self.extinction_coefficient, float, min_val=0.1, max_val=1.0)
        validate_parameter(self.bin_size, float, min_val=0.1, max_val=10.0)
        validate_parameter(self.max_workers, int, min_val=1)
        return True

@dataclass
class PreprocessingConfig:
    """Master configuration for the entire preprocessing pipeline."""
    height_normalization: HeightNormalizationConfig = field(default_factory=HeightNormalizationConfig)
    nrd: NRDConfig = field(default_factory=NRDConfig)
    pad: PADConfig = field(default_factory=PADConfig)
    
    def validate(self):
        """Validate all configurations."""
        self.height_normalization.validate()
        self.nrd.validate()
        self.pad.validate()
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return asdict(self)
    
    def save(self, file_path: Union[str, Path]) -> None:
        """Save configuration to JSON file."""
        with open(file_path, 'w') as f:
            json.dump(self.to_dict(), f, indent=4)
    
    @classmethod
    def load(cls, file_path: Union[str, Path]) -> 'PreprocessingConfig':
        """Load configuration from JSON file."""
        with open(file_path, 'r') as f:
            config_dict = json.load(f)
        
        # Create configs from the loaded dictionary
        height_norm_config = HeightNormalizationConfig(**config_dict.get('height_normalization', {}))
        nrd_config = NRDConfig(**config_dict.get('nrd', {}))
        pad_config = PADConfig(**config_dict.get('pad', {}))
        
        return cls(
            height_normalization=height_norm_config,
            nrd=nrd_config,
            pad=pad_config
        )
    
    @classmethod
    def create_from_args(cls, args: argparse.Namespace) -> 'PreprocessingConfig':
        """Create configuration from command line arguments."""
        # Map command line args to configuration objects
        # This assumes a specific argument structure
        height_norm_config = HeightNormalizationConfig(
            input_dir=getattr(args, 'input_dir', ""),
            output_dir=getattr(args, 'output_dir', ""),
            num_workers=getattr(args, 'workers', 4)
        )
        
        nrd_config = NRDConfig(
            input_dir=getattr(args, 'nrd_input', ""),
            output_dir=getattr(args, 'nrd_output', ""),
            bin_size=getattr(args, 'bin_size', 2.0),
            raster_resolution=getattr(args, 'raster_resolution', 5.0),
            max_workers=getattr(args, 'workers', 4)
        )
        
        pad_config = PADConfig(
            input_dir=getattr(args, 'pad_input', ""),
            output_dir=getattr(args, 'pad_output', ""),
            extinction_coefficient=getattr(args, 'extinction_coefficient', 0.5),
            bin_size=getattr(args, 'bin_size', 2.0),
            max_workers=getattr(args, 'workers', 4)
        )
        
        return cls(
            height_normalization=height_norm_config,
            nrd=nrd_config,
            pad=pad_config
        )
    
    def update_from_args(self, args: argparse.Namespace) -> None:
        """Update configuration from command line arguments."""
        # Update height normalization config
        if hasattr(args, 'input_dir') and args.input_dir:
            self.height_normalization.input_dir = args.input_dir
        if hasattr(args, 'output_dir') and args.output_dir:
            self.height_normalization.output_dir = args.output_dir
        if hasattr(args, 'workers'):
            self.height_normalization.num_workers = args.workers
            self.nrd.max_workers = args.workers
            self.pad.max_workers = args.workers
        
        # Update NRD config
        if hasattr(args, 'nrd_input') and args.nrd_input:
            self.nrd.input_dir = args.nrd_input
        if hasattr(args, 'nrd_output') and args.nrd_output:
            self.nrd.output_dir = args.nrd_output
        if hasattr(args, 'bin_size'):
            self.nrd.bin_size = args.bin_size
            self.pad.bin_size = args.bin_size
        if hasattr(args, 'raster_resolution'):
            self.nrd.raster_resolution = args.raster_resolution
        
        # Update PAD config
        if hasattr(args, 'pad_input') and args.pad_input:
            self.pad.input_dir = args.pad_input
        if hasattr(args, 'pad_output') and args.pad_output:
            self.pad.output_dir = args.pad_output
        if hasattr(args, 'extinction_coefficient'):
            self.pad.extinction_coefficient = args.extinction_coefficient

def get_default_config() -> PreprocessingConfig:
    """Get the default preprocessing configuration."""
    return PreprocessingConfig()

def setup_argparse() -> argparse.ArgumentParser:
    """Set up command line argument parsing for preprocessing scripts."""
    parser = argparse.ArgumentParser(description='LiDAR Preprocessing Pipeline')
    
    # General arguments
    parser.add_argument('--config', type=str, help='Path to configuration file')
    parser.add_argument('--workers', type=int, default=4, help='Number of parallel workers')
    parser.add_argument('--bin_size', type=float, default=2.0, help='Vertical bin size in meters')
    
    # Height normalization arguments
    parser.add_argument('--input_dir', type=str, help='Input directory containing LAZ files')
    parser.add_argument('--output_dir', type=str, help='Output directory for processed files')
    
    # NRD calculation arguments
    parser.add_argument('--nrd_input', type=str, help='Input directory for NRD calculation')
    parser.add_argument('--nrd_output', type=str, help='Output directory for NRD results')
    parser.add_argument('--raster_resolution', type=float, default=5.0, help='Raster resolution in meters')
    
    # PAD calculation arguments
    parser.add_argument('--pad_input', type=str, help='Input directory for PAD calculation')
    parser.add_argument('--pad_output', type=str, help='Output directory for PAD results')
    parser.add_argument('--extinction_coefficient', type=float, default=0.5, help='Extinction coefficient for PAD calculation')
    
    return parser

def process_args(args: Optional[List[str]] = None) -> argparse.Namespace:
    """Process command line arguments and return namespace."""
    parser = setup_argparse()
    parsed_args = parser.parse_args(args)
    return parsed_args

def get_config_from_args(args: Optional[List[str]] = None) -> PreprocessingConfig:
    """
    Get configuration from command line arguments.
    
    Args:
        args: Command line arguments (optional, defaults to sys.argv)
        
    Returns:
        Preprocessing configuration
    """
    parsed_args = process_args(args)
    
    if parsed_args.config:
        # Load from config file if provided
        try:
            config = PreprocessingConfig.load(parsed_args.config)
            # Update with any command line arguments provided
            config.update_from_args(parsed_args)
            return config
        except Exception as e:
            logger.error(f"Error loading configuration from {parsed_args.config}: {e}")
            logger.warning("Falling back to default configuration with command line arguments")
    
    # Create new config from arguments
    return PreprocessingConfig.create_from_args(parsed_args)

def save_default_config(output_path: Union[str, Path]) -> None:
    """
    Save the default configuration to a file.
    
    Args:
        output_path: Path to save the configuration
    """
    config = get_default_config()
    config.save(output_path)
    logger.info(f"Default configuration saved to {output_path}")
    
# Command line interface for this module
if __name__ == "__main__":
    # Generate a default configuration file if run directly
    parser = argparse.ArgumentParser(description='LiDAR Preprocessing Configuration Tool')
    parser.add_argument('--output', type=str, default='preprocessing_config.json',
                        help='Output file path for default configuration')
    
    args = parser.parse_args()
    save_default_config(args.output) 