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
    _qualified = f"src.{_sub}"
    try:
        _mod: ModuleType = importlib.import_module(_qualified)
    except ModuleNotFoundError:
        # Sub-package might not exist – skip.
        continue

    # Register bare import alias so that `import common` succeeds.
    sys.modules[_sub] = _mod
