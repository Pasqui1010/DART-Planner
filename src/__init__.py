"""Legacy package root.

This file ensures that sub-packages under the historical `src.*` namespace can
still be imported directly via their bare names (e.g. `import common`) even
before the new public shim `dart_planner` is imported.  This is required for
older modules and test suites that haven't been updated yet.
"""

from __future__ import annotations

import importlib
import sys
from types import ModuleType
from typing import List
from pathlib import Path

_subpackages: List[str] = [
    "common",
    "utils",
    "control",
    "planning",
    "perception",
    "edge",
    "cloud",
    "communication",
    "neural_scene",
    "hardware",
]

for _sub in _subpackages:
    _qualified = f"src.{_sub}"
    try:
        _mod: ModuleType = importlib.import_module(_qualified)
    except ModuleNotFoundError:
        # Sub-package might not exist – skip.
        continue

    # Register bare import alias so that `import common` succeeds.
    sys.modules[_sub] = _mod

# ---------------------------------------------------------------------------
# Legacy single-file modules that live outside the src/ hierarchy
# ---------------------------------------------------------------------------

# Support `import communication_optimizer` used by some old experiment scripts.
import importlib.util
from importlib.machinery import SourceFileLoader

_root_dir = Path(__file__).resolve().parent.parent
_legacy_experiments_dir = _root_dir / "legacy" / "legacy_experiments"
if str(_legacy_experiments_dir) not in sys.path:
    sys.path.insert(0, str(_legacy_experiments_dir))

_comm_path = _root_dir / "legacy" / "legacy_experiments" / "communication_optimizer.py"

if _comm_path.is_file():
    _module_name = "communication_optimizer"
    if _module_name not in sys.modules:
        _loader = SourceFileLoader(_module_name, str(_comm_path))
        _spec = importlib.util.spec_from_loader(_module_name, _loader)
        if _spec and _spec.loader is not None:
            _legacy_mod = importlib.util.module_from_spec(_spec)
            _spec.loader.exec_module(_legacy_mod)  # type: ignore[arg-type]
            sys.modules[_module_name] = _legacy_mod
