"""Legacy modules kept only for backward compatibility.

Importing from this package will raise a DeprecationWarning so that
contributors are aware the code is no longer maintained. New development
must take place in the core `dart_planner` package tree.
"""

import warnings as _warnings

_warnings.warn(
    "You are importing a module from the legacy namespace. This code is no "
    "longer maintained and will be removed in a future release.",
    DeprecationWarning,
    stacklevel=2,
) 