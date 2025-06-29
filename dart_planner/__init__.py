"""DART-Planner public package shim.

Until we physically rename the codebase from `src/` to `dart_planner/` we
publish this lightweight compatibility layer that re-exports everything
that lives in `src.*`.  External users can simply do:

    import dart_planner as dp
    from dart_planner.planning import se3_mpc_planner

Internally the original `src.` namespace continues to work, so existing
imports are not broken.  Once the rename is complete this shim can be
removed.
"""
from __future__ import annotations

import importlib
import sys
from types import ModuleType
from typing import List

# The legacy root package that currently contains all real code.
_SRC_PACKAGE_NAME = "src"

try:
    _src_pkg: ModuleType = importlib.import_module(_SRC_PACKAGE_NAME)
except ModuleNotFoundError as exc:  # pragma: no cover – should never happen
    raise ImportError(
        "DART-Planner expects the legacy 'src' package to be importable."
    ) from exc

# Expose `dart_planner` itself as an alias of `src` so attribute access falls
# through transparently (e.g. `dart_planner.utils` → `src.utils`).
# We intentionally do NOT just assign `globals()` because we still want the
# shim metadata (docstring, __version__, etc.).  Instead we delegate attribute
# lookup to the underlying package when not found locally.


def __getattr__(name: str):  # type: ignore[override]
    # First check if the attribute already exists in this shim (e.g. __doc__)
    if name in globals():
        return globals()[name]
    return getattr(_src_pkg, name)


# Populate `sys.modules` so that importing sub-packages via
# `import dart_planner.utils` works out of the box.
_subpackages: List[str] = [
    "common",
    "utils",
    "control",
    "planning",
    "perception",
    "edge",
    "cloud",
    "communication",
]

for _sub in _subpackages:
    _qualified_new = f"dart_planner.{_sub}"
    _qualified_old = f"{_SRC_PACKAGE_NAME}.{_sub}"
    try:
        _mod = importlib.import_module(_qualified_old)
    except ModuleNotFoundError:
        continue
    sys.modules[_qualified_new] = _mod
    # Also set as attribute for "from dart_planner import planning" style.
    globals()[_sub] = _mod  # type: ignore[misc]
    # Also allow legacy bare import style: `import planning`.
    sys.modules[_sub] = _mod

# Optional metadata
__all__ = _subpackages
__version__ = "0.1.0"
