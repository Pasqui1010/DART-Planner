"""TEMPORARY shim – will be removed once all imports migrate to di_container_v2."""
from warnings import warn

warn(
    "⚠️  'dart_planner.common.di_container' is deprecated; "
    "use 'dart_planner.common.di_container_v2' instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export everything from di_container_v2
from .di_container_v2 import *  # noqa: F403,F401 