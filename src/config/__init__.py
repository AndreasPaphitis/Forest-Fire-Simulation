"""
Configuration package for Forest Fire Simulation.

This package contains configuration tools and constants for the simulation system.
"""

from src.config.config_tools import (
    ModelConfig,
    get_global_config,
    # get_constant # This was also deprecated
)

# Removed import from src.config.constants as these are now in ModelConfig
# from src.config.constants import (
#     MODEL_RESOLUTION,
#     LAYER_HEIGHT_METERS,
#     DEFAULT_NUM_LAYERS,
#     GRID_SIZE,
#     NUM_STEPS,
#     STORE_FULL_STATES,
#     WIND_INFLUENCE,
#     SLOPE_INFLUENCE,
#     VERTICAL_CONNECTIVITY,
#     SIGMOID_STEEPNESS,
#     SIGMOID_THRESHOLD,
#     SPREAD_THRESHOLD,
#     WIND_EFFECT_MAX,
#     DEFAULT_FUEL_MOISTURE,
#     MIN_FUEL_VALUE,
#     MAX_FUEL_VALUE,
#     DEFAULT_FUEL_LOAD
# )

__all__ = [
    'ModelConfig',
    'get_global_config',
    # 'get_constant',
    # 'MODEL_RESOLUTION',
    # 'LAYER_HEIGHT_METERS',
    # 'DEFAULT_NUM_LAYERS',
    # 'GRID_SIZE',
    # 'NUM_STEPS',
    # 'STORE_FULL_STATES',
    # 'WIND_INFLUENCE',
    # 'SLOPE_INFLUENCE',
    # 'VERTICAL_CONNECTIVITY',
    # 'SIGMOID_STEEPNESS',
    # 'SIGMOID_THRESHOLD',
    # 'SPREAD_THRESHOLD',
    # 'WIND_EFFECT_MAX',
    # 'DEFAULT_FUEL_MOISTURE',
    # 'MIN_FUEL_VALUE',
    # 'MAX_FUEL_VALUE',
    # 'DEFAULT_FUEL_LOAD'
] 