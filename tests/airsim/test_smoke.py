import asyncio
import os

import pytest

pytest.importorskip("src.hardware.airsim_adapter")

from dart_planner.hardware.airsim_adapter import AirSimAdapter  # noqa: E402

# Mark entire module so it can be excluded with -m "not slow" if desired
pytestmark = pytest.mark.airsim


@pytest.mark.asyncio
async def test_airsim_connect():
    """Smoke-test connecting via AirSimAdapter.

    The test is skipped automatically unless the environment variable
    AIRSIM_TEST=1 is set *and* an AirSim instance is reachable on the default
    RPC port.  This makes it safe to run in developer machines without
    simulator running.
    """
    if os.getenv("AIRSIM_TEST") != "1":
        pytest.skip("Set AIRSIM_TEST=1 to enable AirSim smoke tests.")

    adapter = AirSimAdapter()
    connected = await adapter.connect()
    assert connected, "Failed to connect to AirSim"
