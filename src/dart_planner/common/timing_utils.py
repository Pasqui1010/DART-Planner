"""Timing utilities for high-precision sleeps.

Provides an awaitable ``high_res_sleep`` that attempts nanosecond-level sleep on
Linux via ``clock_nanosleep`` and falls back to ``asyncio.sleep`` elsewhere.
The helper emits a warning if requested resolution <1 ms but the underlying
platform cannot guarantee it.
"""
from __future__ import annotations

import asyncio
import os
import time
import warnings
import platform
from typing import Optional

__all__ = ["high_res_sleep"]

# Detect platform specifics
_IS_LINUX = platform.system().lower() == "linux"

if _IS_LINUX:
    try:
        import ctypes
        from ctypes.util import find_library

        librt = ctypes.CDLL(find_library("rt"), use_errno=True)
        CLOCK_MONOTONIC = 1  # from <time.h>

        class timespec(ctypes.Structure):
            _fields_ = [("tv_sec", ctypes.c_long), ("tv_nsec", ctypes.c_long)]

        _clock_nanosleep = librt.clock_nanosleep
        _clock_nanosleep.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.POINTER(timespec), ctypes.POINTER(timespec)]
        _clock_nanosleep.restype = ctypes.c_int
    except Exception:  # pragma: no cover – fallback path
        _clock_nanosleep = None
else:
    _clock_nanosleep = None


async def high_res_sleep(duration_s: float, _loop: Optional[asyncio.AbstractEventLoop] = None) -> None:
    """High-resolution async sleep.

    If on Linux and ``clock_nanosleep`` is available, we perform the sleep in a
    thread to avoid blocking the event loop. Otherwise we fall back to
    ``asyncio.sleep``.

    A warning is emitted if ``duration_s < 0.001`` and we cannot guarantee
    sub-millisecond resolution.
    """
    if duration_s <= 0:
        return

    if _clock_nanosleep is not None:
        # Offload to thread so we don't block.
        if _loop is None:
            _loop = asyncio.get_event_loop()

        await _loop.run_in_executor(None, _clock_nanosleep_sleep, duration_s)
    else:
        if duration_s < 0.001:
            warnings.warn(
                "Requested sleep {:.3f} ms but high-resolution timer not available; timing jitter may exceed 1 ms".format(
                    duration_s * 1000
                ),
                RuntimeWarning,
            )
        await asyncio.sleep(duration_s)


def _clock_nanosleep_sleep(duration_s: float) -> None:
    """Blocking helper executed in a thread to perform high-res sleep."""
    if _clock_nanosleep is None:
        time.sleep(duration_s)
        return

    ts = timespec(int(duration_s), int((duration_s % 1) * 1_000_000_000))
    # flags=0 for relative sleep
    err = _clock_nanosleep(CLOCK_MONOTONIC, 0, ctypes.byref(ts), None)
    if err != 0:  # pragma: no cover
        # Fallback to time.sleep if call failed
        time.sleep(duration_s) 