"""Deprecated import shim for DIAL-MPC.

The full legacy implementation now lives in ``src/legacy/dial_mpc_planner.py``.
This stub exists only to keep historical import paths working and will be
removed after the next minor release.
"""

from __future__ import annotations

import warnings as _warnings
from dataclasses import dataclass
from typing import Any

from src.planning.se3_mpc_planner import SE3MPCPlanner  # fallback modern planner

_warnings.warn(
    "`src.planning.dial_mpc_planner` has moved to `src.legacy.dial_mpc_planner` "
    "and will be removed in a future release. Importing from the new location "
    "avoids this warning.",
    DeprecationWarning,
    stacklevel=2,
)

from src.legacy.dial_mpc_planner import *  # type: ignore  # noqa: F403, F401


class DIALMPCPlanner(SE3MPCPlanner):
    """Legacy alias for the deprecated DIAL-MPC planner.

    The full aerial-robot–specific replacement is SE3MPCPlanner.  We
    subclass it here so that legacy experiment scripts importing
    `DIALMPCPlanner` keep working without pulling in the original,
    incompatible implementation.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:  # noqa: D401
        super().__init__(*args, **kwargs)


@dataclass
class DIALMPCConfig:
    """Minimal config placeholder preserved for legacy experiments."""

    prediction_horizon: int = 6
    dt: float = 0.1


class ContinuousDIALMPC(DIALMPCPlanner):
    """Continuous-time variant placeholder mapping to discrete SE3 planner."""

    # No extra behaviour; legacy scripts expect class presence only.
    pass


__all__ = [
    *[name for name in globals() if name.startswith("SE3")],
    "DIALMPCPlanner",
    "DIALMPCConfig",
    "ContinuousDIALMPC",
]
