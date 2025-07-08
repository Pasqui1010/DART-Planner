"""
Multiprocessing-based Real-Time Control Loop for DART-Planner.

Avoids Python GIL by running the control loop in a separate process.
"""

import time
import multiprocessing
import queue
from typing import Callable, Optional, Any


class ProcessControlLoop:
    """
    Runs a user-provided function at a fixed frequency in a separate process,
    allowing the control loop to bypass the Python GIL.
    """
    def __init__(self, func: Callable[..., Any], frequency_hz: float):
        self.func = func
        self.frequency_hz = frequency_hz
        self.period_ns = int(1e9 / frequency_hz)
        self.queue: multiprocessing.Queue = multiprocessing.Queue(maxsize=1)
        self.stop_event = multiprocessing.Event()
        self.process: Optional[multiprocessing.Process] = None

    def start(self) -> None:
        """Start the control loop in a separate process."""
        self.process = multiprocessing.Process(target=self._run_loop, daemon=True)
        self.process.start()

    def _run_loop(self) -> None:
        next_call = time.perf_counter_ns()
        while not self.stop_event.is_set():
            start_ns = time.perf_counter_ns()
            try:
                result = self.func()
                # Non-blocking put: always keep latest value
                if not self.queue.full():
                    self.queue.put(result)
            except Exception:
                # Ignore errors in loop to preserve timing
                pass
            next_call += self.period_ns
            sleep_ns = next_call - time.perf_counter_ns()
            if sleep_ns > 0:
                time.sleep(sleep_ns / 1e9)

    def get_result(self, timeout: Optional[float] = None) -> Any:
        """Retrieve the latest result from the control loop."""
        try:
            return self.queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def stop(self) -> None:
        """Stop the control loop process."""
        self.stop_event.set()
        if self.process is not None:
            self.process.join() 