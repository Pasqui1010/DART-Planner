#!/usr/bin/env python3
"""A thin wrapper that chooses between the full AirSim RPC interface and the
HTTP-based simplified interface at run-time.

Why?
-----
* CI environments or fresh developer machines may not have the heavy
  `airsim` Python wheel (or its Tornado<5 dependency tree) installed.
* We still want the rest of the stack to import **one** integration class and
  not litter the codebase with conditional imports.

Usage
~~~~~
```python
from src.hardware.airsim_adapter import AirSimAdapter

adapter = AirSimAdapter()
await adapter.connect()            # delegates to best-available backend
await adapter.start_mission(wps)   # identical signature for both backends
```

Design
------
* If `import airsim` succeeds **and** the user did not explicitly request the
  simplified path (via env var `DART_SIMPLE_AIRSIM=1`), we instantiate the
  rich `AirSimInterface`.
* Otherwise we fall back to `SimpleAirSimInterface` which talks HTTP / raw
  sockets only and therefore works even when the AirSim wheel cannot be
  installed.
* The public API is a strict subset of `AirSimInterface` so existing code
  continues to compile.
"""

from __future__ import annotations

import os
from typing import List, Optional

import numpy as np

try:
    from src.hardware.airsim_interface import AirSimConfig, AirSimInterface  # full RPC

    _FULL_AIRSIM_OK = True
except Exception:  # noqa: BLE001, broad except is fine for fallback detection
    _FULL_AIRSIM_OK = False

from src.hardware.simple_airsim_interface import (
    SimpleAirSimConfig,
    SimpleAirSimInterface,
)

# ---------------------------------------------------------------------------
# Public facade
# ---------------------------------------------------------------------------


class AirSimAdapter:  # noqa: D101, pylint: disable=too-few-public-methods
    def __init__(
        self,
        use_simple: Optional[bool] = None,
        rpc_cfg: Optional["AirSimConfig"] = None,
        simple_cfg: Optional["SimpleAirSimConfig"] = None,
    ) -> None:
        """Create a unified AirSim adaptor.

        Parameters
        ----------
        use_simple
            Force use of the simplified HTTP adaptor, regardless of whether
            the `airsim` package is importable.  If *None* (default) the
            decision is automatic.
        rpc_cfg, simple_cfg
            Optional configuration overrides for the underlying back-ends.
        """
        # Environment variable override beats constructor arg
        if os.getenv("DART_SIMPLE_AIRSIM") is not None:
            self._force_simple = os.getenv("DART_SIMPLE_AIRSIM") == "1"
        else:
            self._force_simple = bool(use_simple)

        self._backend = self._choose_backend(rpc_cfg, simple_cfg)

    # ------------------------------------------------------------------
    # Public API (subset of AirSimInterface)
    # ------------------------------------------------------------------

    async def connect(self) -> bool:  # noqa: D401
        """Establish connection to AirSim via chosen back-end."""
        import asyncio

        if asyncio.iscoroutinefunction(self._backend.connect):
            return await self._backend.connect()  # type: ignore[arg-type]
        # Synchronous fallback (SimpleAirSimInterface)
        return self._backend.connect()  # type: ignore[return-value]

    async def start_mission(self, waypoints: List[np.ndarray]) -> bool:  # noqa: D401
        """Begin an autonomous mission."""
        import asyncio

        if hasattr(self._backend, "start_mission") and asyncio.iscoroutinefunction(
            self._backend.start_mission  # type: ignore[attr-defined]
        ):
            return await self._backend.start_mission(waypoints)  # type: ignore[arg-type]

        # Simplified interface fallback uses test_dart_mission for now
        if hasattr(self._backend, "test_dart_mission"):
            print(
                "⚠️ Simplified interface: using test_dart_mission instead of start_mission"
            )
            return self._backend.test_dart_mission()  # type: ignore[attr-defined]

        raise NotImplementedError("Backend does not support start_mission")

    # Helper for advanced users who might want to call back-end specifics
    # without breaking encapsulation entirely.
    @property
    def backend(self):  # noqa: D401
        """Return underlying interface instance (read-only)."""
        return self._backend

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _choose_backend(
        self,
        rpc_cfg: Optional["AirSimConfig"],
        simple_cfg: Optional["SimpleAirSimConfig"],
    ):
        if not self._force_simple and _FULL_AIRSIM_OK:
            print("🔧 AirSimAdapter: using *full* RPC interface (airsim package found)")
            return AirSimInterface(rpc_cfg) if rpc_cfg else AirSimInterface()

        print("🔧 AirSimAdapter: falling back to simplified HTTP interface")
        return (
            SimpleAirSimInterface(simple_cfg) if simple_cfg else SimpleAirSimInterface()
        )
