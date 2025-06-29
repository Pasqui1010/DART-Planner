"""Deprecated import shim for DIAL-MPC.

The full legacy implementation now lives in ``src/legacy/dial_mpc_planner.py``.
This stub exists only to keep historical import paths working and will be
removed after the next minor release.
"""

from __future__ import annotations

import warnings as _warnings

_warnings.warn(
    "`src.planning.dial_mpc_planner` has moved to `src.legacy.dial_mpc_planner` "
    "and will be removed in a future release. Importing from the new location "
    "avoids this warning.",
    DeprecationWarning,
    stacklevel=2,
)

from src.legacy.dial_mpc_planner import *  # type: ignore  # noqa: F403, F401
