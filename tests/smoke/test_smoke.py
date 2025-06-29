"""Smoke test: verifies that DART-Planner core stack boots without runtime errors.

Runs the short hover simulation provided in ``examples/minimal_takeoff.py``.
The test is marked with the ``smoke`` marker so it can be run stand-alone:

    pytest -m smoke

It should finish in <10-15 s on CI hardware.
"""

import pytest  # type: ignore

# Mark the entire module so it is easy to include/exclude
pytestmark = pytest.mark.smoke


def test_minimal_takeoff_example():
    """Execute the hover example for 1 s to catch import/runtime errors."""

    from examples.minimal_takeoff import run_smoke_test

    # Run much shorter than the example default to keep CI fast.
    run_smoke_test(duration=1.0, hz=50.0)
