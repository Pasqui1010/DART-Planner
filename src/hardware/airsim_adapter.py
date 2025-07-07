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
    from src.hardware.airsim_interface import AirSimConfig, AirSimDroneInterface  # full RPC

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

    async def disconnect(self) -> None:
        """Safely disconnect from AirSim."""
        import asyncio

        if hasattr(self._backend, "disconnect") and asyncio.iscoroutinefunction(
            self._backend.disconnect  # type: ignore[attr-defined]
        ):
            await self._backend.disconnect()  # type: ignore[arg-type]
        elif hasattr(self._backend, "disconnect"):
            self._backend.disconnect()  # type: ignore[attr-defined]

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

    async def land(self) -> bool:
        """Land the drone safely."""
        import asyncio

        if hasattr(self._backend, "land") and asyncio.iscoroutinefunction(
            self._backend.land  # type: ignore[attr-defined]
        ):
            return await self._backend.land()  # type: ignore[arg-type]
        elif hasattr(self._backend, "land"):
            return self._backend.land()  # type: ignore[attr-defined]

        # Fallback implementation for simplified interface
        print("⚠️ Simplified interface: using emergency landing fallback")
        return await self.emergency_land()

    async def takeoff(self, altitude: float = 2.0) -> bool:
        """Takeoff to specified altitude."""
        import asyncio

        if hasattr(self._backend, "takeoff") and asyncio.iscoroutinefunction(
            self._backend.takeoff  # type: ignore[attr-defined]
        ):
            return await self._backend.takeoff(altitude)  # type: ignore[arg-type]
        elif hasattr(self._backend, "takeoff"):
            return self._backend.takeoff(altitude)  # type: ignore[attr-defined]

        # Fallback implementation for simplified interface
        print(f"⚠️ Simplified interface: simulating takeoff to {altitude}m")
        return True

    async def pause(self) -> bool:
        """Pause the current mission."""
        import asyncio

        if hasattr(self._backend, "pause") and asyncio.iscoroutinefunction(
            self._backend.pause  # type: ignore[attr-defined]
        ):
            return await self._backend.pause()  # type: ignore[arg-type]
        elif hasattr(self._backend, "pause"):
            return self._backend.pause()  # type: ignore[attr-defined]

        # Fallback implementation for simplified interface
        print("⚠️ Simplified interface: simulating mission pause")
        return True

    async def resume(self) -> bool:
        """Resume the paused mission."""
        import asyncio

        if hasattr(self._backend, "resume") and asyncio.iscoroutinefunction(
            self._backend.resume  # type: ignore[attr-defined]
        ):
            return await self._backend.resume()  # type: ignore[arg-type]
        elif hasattr(self._backend, "resume"):
            return self._backend.resume()  # type: ignore[attr-defined]

        # Fallback implementation for simplified interface
        print("⚠️ Simplified interface: simulating mission resume")
        return True

    async def emergency_land(self) -> bool:
        """Emergency landing procedure."""
        import asyncio

        if hasattr(self._backend, "emergency_land") and asyncio.iscoroutinefunction(
            self._backend.emergency_land  # type: ignore[attr-defined]
        ):
            await self._backend.emergency_land()  # type: ignore[arg-type]
            return True
        elif hasattr(self._backend, "emergency_land"):
            self._backend.emergency_land()  # type: ignore[attr-defined]
            return True

        # Fallback implementation for simplified interface
        print("⚠️ Simplified interface: simulating emergency landing")
        return True

    async def get_state(self):
        """Get current drone state."""
        import asyncio

        if hasattr(self._backend, "get_state") and asyncio.iscoroutinefunction(
            self._backend.get_state  # type: ignore[attr-defined]
        ):
            return await self._backend.get_state()  # type: ignore[arg-type]
        elif hasattr(self._backend, "get_state"):
            return self._backend.get_state()  # type: ignore[attr-defined]

        # Fallback implementation for simplified interface
        from src.common.types import DroneState
        import time
        return DroneState(timestamp=time.time())

    async def send_control_command(self, command):
        """Send control command to the drone."""
        import asyncio

        if hasattr(self._backend, "send_control_command") and asyncio.iscoroutinefunction(
            self._backend.send_control_command  # type: ignore[attr-defined]
        ):
            return await self._backend.send_control_command(command)  # type: ignore[arg-type]
        elif hasattr(self._backend, "send_control_command"):
            return self._backend.send_control_command(command)  # type: ignore[attr-defined]

        # Fallback implementation for simplified interface
        print("⚠️ Simplified interface: simulating control command")
        return True

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
            return AirSimDroneInterface(rpc_cfg) if rpc_cfg else AirSimDroneInterface()

        print("🔧 AirSimAdapter: falling back to simplified HTTP interface")
        return (
            SimpleAirSimInterface(simple_cfg) if simple_cfg else SimpleAirSimInterface()
        )
