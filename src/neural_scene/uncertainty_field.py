"""
Uncertainty Field Module

This module provides uncertainty quantification capabilities for neural scene representations.
It enables uncertainty-aware exploration planning in the Global Mission Planner.

Key features:
- Spatial uncertainty field management
- High-uncertainty region identification
- Uncertainty-based exploration target generation
- Multi-scale uncertainty analysis
"""

from typing import List, Dict, Optional, Tuple, Any
import numpy as np
import time
from dataclasses import dataclass


@dataclass
class UncertaintyRegion:
    """High uncertainty region for exploration targeting"""

    center: np.ndarray  # [x, y, z] center of region
    bounds: np.ndarray  # [[x_min, y_min, z_min], [x_max, y_max, z_max]]
    uncertainty_value: float  # Average uncertainty in region [0, 1]
    volume: float  # Volume of the region in m³
    priority: float  # Exploration priority [0, 1]
    last_updated: float  # Timestamp of last update


class UncertaintyField:
    """
    Manages uncertainty fields for neural scene representations.

    This class provides interfaces for uncertainty-aware exploration
    planning and active learning in neural scene reconstruction.
    """

    def __init__(self, scene_bounds: np.ndarray, resolution: float):
        """
        Initialize uncertainty field.

        Args:
            scene_bounds: [[x_min, y_min, z_min], [x_max, y_max, z_max]]
            resolution: Spatial resolution in meters
        """
        self.scene_bounds = scene_bounds
        self.resolution = resolution

        # Calculate grid dimensions
        self.grid_size = np.ceil(
            (scene_bounds[1] - scene_bounds[0]) / resolution
        ).astype(int)

        # Initialize uncertainty field
        self.uncertainty_grid = np.ones(self.grid_size)  # Start with high uncertainty
        self.observation_count = np.zeros(self.grid_size)  # Track observation frequency

        # Uncertainty regions cache
        self.high_uncertainty_regions: List[UncertaintyRegion] = []
        self.uncertainty_threshold = 0.7
        self.last_region_update = 0.0

    def update_uncertainty_at_position(
        self, position: np.ndarray, uncertainty: float, observation_weight: float = 1.0
    ):
        """
        Update uncertainty at a specific position.

        Args:
            position: [x, y, z] coordinates
            uncertainty: New uncertainty value [0, 1]
            observation_weight: Weight of this observation
        """
        grid_idx = self._position_to_grid_index(position)

        if self._is_valid_grid_index(grid_idx):
            # Exponential moving average for uncertainty
            alpha = 0.1  # Learning rate
            current_uncertainty = self.uncertainty_grid[tuple(grid_idx)]
            self.uncertainty_grid[tuple(grid_idx)] = (
                alpha * uncertainty + (1 - alpha) * current_uncertainty
            )

            # Update observation count
            self.observation_count[tuple(grid_idx)] += observation_weight

    def update_uncertainty_field(
        self,
        positions: np.ndarray,
        uncertainties: np.ndarray,
        weights: Optional[np.ndarray] = None,
    ):
        """
        Batch update uncertainty field.

        Args:
            positions: Array of positions shape (N, 3)
            uncertainties: Array of uncertainties shape (N,)
            weights: Optional observation weights shape (N,)
        """
        if weights is None:
            weights = np.ones(len(positions))

        for pos, unc, weight in zip(positions, uncertainties, weights):
            self.update_uncertainty_at_position(pos, unc, weight)

    def get_uncertainty_at_position(self, position: np.ndarray) -> float:
        """
        Get uncertainty value at a specific position.

        Args:
            position: [x, y, z] coordinates

        Returns:
            float: Uncertainty value [0, 1]
        """
        grid_idx = self._position_to_grid_index(position)

        if self._is_valid_grid_index(grid_idx):
            return float(self.uncertainty_grid[tuple(grid_idx)])
        else:
            return 1.0  # High uncertainty outside bounds

    def get_uncertainty_field_region(self, bounds: np.ndarray) -> np.ndarray:
        """
        Get uncertainty field for a specific region.

        Args:
            bounds: [[x_min, y_min, z_min], [x_max, y_max, z_max]]

        Returns:
            np.ndarray: 3D uncertainty field for the region
        """
        # Convert bounds to grid indices
        min_idx = self._position_to_grid_index(bounds[0])
        max_idx = self._position_to_grid_index(bounds[1])

        # Clamp to valid grid range
        min_idx = np.maximum(min_idx, 0)
        max_idx = np.minimum(max_idx, self.grid_size - 1)

        # Extract region
        region = self.uncertainty_grid[
            min_idx[0] : max_idx[0] + 1,
            min_idx[1] : max_idx[1] + 1,
            min_idx[2] : max_idx[2] + 1,
        ]

        return region.copy()

    def identify_high_uncertainty_regions(
        self, threshold: Optional[float] = None, min_volume: float = 1.0
    ) -> List[UncertaintyRegion]:
        """
        Identify regions with high uncertainty for exploration.

        Args:
            threshold: Uncertainty threshold [0, 1], defaults to self.uncertainty_threshold
            min_volume: Minimum volume for a region to be considered (m³)

        Returns:
            List of high uncertainty regions sorted by priority
        """
        if threshold is None:
            threshold = self.uncertainty_threshold

        # Find high uncertainty voxels
        high_uncertainty_mask = self.uncertainty_grid > threshold

        # Connected component analysis to group nearby voxels
        regions = self._find_connected_regions(high_uncertainty_mask, min_volume)

        # Sort by priority (uncertainty value and volume)
        regions.sort(key=lambda r: float(r.priority), reverse=True)

        self.high_uncertainty_regions = regions
        self.last_region_update = time.time()

        return regions

    def get_exploration_targets(
        self, num_targets: int = 5, current_position: Optional[np.ndarray] = None
    ) -> List[np.ndarray]:
        """
        Get exploration targets based on uncertainty.

        Args:
            num_targets: Number of exploration targets to return
            current_position: Current drone position for distance-based prioritization

        Returns:
            List of target positions [x, y, z]
        """
        # Update high uncertainty regions if needed
        if (
            not self.high_uncertainty_regions
            or time.time() - self.last_region_update > 5.0
        ):  # Update every 5 seconds
            self.identify_high_uncertainty_regions()

        targets = []

        for region in self.high_uncertainty_regions[:num_targets]:
            # Use region center as exploration target
            target = region.center.copy()

            # Adjust target height for drone navigation
            target[2] = max(target[2], 2.0)  # Minimum 2m altitude

            targets.append(target)

        # Sort by distance if current position provided
        if current_position is not None:
            targets.sort(key=lambda t: np.linalg.norm(t - current_position))

        return targets[:num_targets]

    def reduce_uncertainty_around_position(
        self, position: np.ndarray, radius: float = 2.0, reduction_factor: float = 0.5
    ):
        """
        Reduce uncertainty around a position (simulates sensor observation).

        Args:
            position: [x, y, z] center position
            radius: Radius of uncertainty reduction (meters)
            reduction_factor: How much to reduce uncertainty [0, 1]
        """
        # Find all grid points within radius
        grid_center = self._position_to_grid_index(position)
        radius_in_voxels = int(radius / self.resolution)

        for i in range(
            max(0, grid_center[0] - radius_in_voxels),
            min(self.grid_size[0], grid_center[0] + radius_in_voxels + 1),
        ):
            for j in range(
                max(0, grid_center[1] - radius_in_voxels),
                min(self.grid_size[1], grid_center[1] + radius_in_voxels + 1),
            ):
                for k in range(
                    max(0, grid_center[2] - radius_in_voxels),
                    min(self.grid_size[2], grid_center[2] + radius_in_voxels + 1),
                ):
                    # Check if within radius
                    grid_pos = np.array([i, j, k])
                    world_pos = self._grid_index_to_position(grid_pos)
                    distance = np.linalg.norm(world_pos - position)

                    if distance <= radius:
                        # Reduce uncertainty
                        current_uncertainty = self.uncertainty_grid[i, j, k]
                        new_uncertainty = current_uncertainty * (1.0 - reduction_factor)
                        self.uncertainty_grid[i, j, k] = new_uncertainty

                        # Increase observation count
                        self.observation_count[i, j, k] += 1

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get uncertainty field statistics.

        Returns:
            Dict containing uncertainty statistics
        """
        total_voxels = np.prod(self.grid_size)
        observed_voxels = np.sum(self.observation_count > 0)
        high_uncertainty_voxels = np.sum(
            self.uncertainty_grid > self.uncertainty_threshold
        )

        return {
            "total_voxels": int(total_voxels),
            "observed_voxels": int(observed_voxels),
            "observation_coverage": float(observed_voxels / total_voxels),
            "high_uncertainty_voxels": int(high_uncertainty_voxels),
            "high_uncertainty_percentage": float(
                high_uncertainty_voxels / total_voxels * 100
            ),
            "average_uncertainty": float(np.mean(self.uncertainty_grid)),
            "min_uncertainty": float(np.min(self.uncertainty_grid)),
            "max_uncertainty": float(np.max(self.uncertainty_grid)),
            "uncertainty_regions": len(self.high_uncertainty_regions),
            "resolution": self.resolution,
            "grid_size": self.grid_size.tolist(),
        }

    def _position_to_grid_index(self, position: np.ndarray) -> np.ndarray:
        """Convert world position to grid index"""
        relative_pos = position - self.scene_bounds[0]
        grid_idx = np.floor(relative_pos / self.resolution).astype(int)
        return grid_idx

    def _grid_index_to_position(self, grid_idx: np.ndarray) -> np.ndarray:
        """Convert grid index to world position"""
        grid_idx = np.array(grid_idx)  # Ensure it's a numpy array
        relative_pos = (grid_idx + 0.5) * self.resolution  # Center of voxel
        world_pos = relative_pos + self.scene_bounds[0]
        return world_pos

    def _is_valid_grid_index(self, grid_idx: np.ndarray) -> bool:
        """Check if grid index is valid"""
        return np.all(grid_idx >= 0) and np.all(grid_idx < self.grid_size)

    def _find_connected_regions(
        self, mask: np.ndarray, min_volume: float
    ) -> List[UncertaintyRegion]:
        """
        Find connected components in uncertainty mask.

        This is a simplified implementation. For production, consider using
        scipy.ndimage.label for more sophisticated connected component analysis.
        """
        regions = []
        visited = np.zeros_like(mask, dtype=bool)

        # Simple flood-fill to find connected regions
        for i in range(mask.shape[0]):
            for j in range(mask.shape[1]):
                for k in range(mask.shape[2]):
                    if mask[i, j, k] and not visited[i, j, k]:
                        # Start flood-fill from this point
                        region_voxels = self._flood_fill(mask, visited, (i, j, k))

                        if len(region_voxels) * (self.resolution**3) >= min_volume:
                            region = self._create_uncertainty_region(region_voxels)
                            regions.append(region)

        return regions

    def _flood_fill(
        self, mask: np.ndarray, visited: np.ndarray, start: Tuple[int, int, int]
    ) -> List[Tuple[int, int, int]]:
        """Simple flood-fill algorithm"""
        stack = [start]
        region_voxels = []

        while stack:
            i, j, k = stack.pop()

            if (
                i < 0
                or i >= mask.shape[0]
                or j < 0
                or j >= mask.shape[1]
                or k < 0
                or k >= mask.shape[2]
            ):
                continue

            if visited[i, j, k] or not mask[i, j, k]:
                continue

            visited[i, j, k] = True
            region_voxels.append((i, j, k))

            # Add neighbors to stack (6-connectivity)
            for di, dj, dk in [
                (-1, 0, 0),
                (1, 0, 0),
                (0, -1, 0),
                (0, 1, 0),
                (0, 0, -1),
                (0, 0, 1),
            ]:
                stack.append((i + di, j + dj, k + dk))

        return region_voxels

    def _create_uncertainty_region(
        self, voxels: List[Tuple[int, int, int]]
    ) -> UncertaintyRegion:
        """Create UncertaintyRegion from list of voxels"""
        import time

        # Convert voxel indices to world positions
        voxel_array = np.array(voxels)
        world_positions = np.array(
            [self._grid_index_to_position(voxel) for voxel in voxels]
        )

        # Calculate region properties
        min_bounds = np.min(world_positions, axis=0)
        max_bounds = np.max(world_positions, axis=0)
        center = (min_bounds + max_bounds) / 2
        volume = len(voxels) * (self.resolution**3)

        # Calculate average uncertainty in region
        uncertainty_values = [self.uncertainty_grid[tuple(voxel)] for voxel in voxels]
        avg_uncertainty = np.mean(uncertainty_values)

        # Calculate priority (based on uncertainty and volume)
        priority = avg_uncertainty * np.log(1 + volume)  # Log scaling for volume

        return UncertaintyRegion(
            center=center,
            bounds=np.array([min_bounds, max_bounds]),
            uncertainty_value=float(avg_uncertainty),
            volume=float(volume),
            priority=float(priority),
            last_updated=time.time(),
        )
