import numpy as np
from src.perception.explicit_geometric_mapper import ExplicitGeometricMapper


def test_trace_ray_contiguity():
    """The Bresenham _trace_ray should return contiguous voxels with no gaps."""
    mapper = ExplicitGeometricMapper(resolution=0.5)
    start = np.array([0.0, 0.0, 0.0])
    direction = np.array([1.0, 1.0, 0.0]) / np.sqrt(2)
    voxels = mapper._trace_ray(start, direction, distance=5.0)
    # compute Manhattan distance between consecutive voxels, should be 1 each
    diffs = [
        np.sum(np.abs(np.subtract(v2, v1))) for v1, v2 in zip(voxels[:-1], voxels[1:])
    ]
    assert all(d == 1 for d in diffs), "Non-contiguous voxel sequence detected"
