# Neural Scene Representation Module
# 
# This module provides the foundation for NeRF/3DGS integration
# in the three-layer drone architecture
#
# Key Components:
# - Base neural scene interface
# - Uncertainty quantification
# - Semantic understanding
# - Real-time scene updates

from .base_neural_scene import BaseNeuralScene, PlaceholderNeuralScene
from .uncertainty_field import UncertaintyField

__all__ = [
    'BaseNeuralScene',
    'PlaceholderNeuralScene',
    'UncertaintyField'
] 