"""End-to-end test for the DART-Planner web demo using Playwright.

This test starts the FastAPI Socket.IO gateway locally, opens a headless
Chromium browser, performs the login flow, and verifies that an
authenticated Socket.IO connection is established (indicated by the UI
changing state and enabling the start button).

Requires the Playwright Python package and browsers installed:
    pip install playwright
    playwright install

You can skip this test with `pytest -m 'not e2e'` if the environment is
headless-unfriendly (CI without display) or Playwright is unavailable.
"""

import os
import subprocess
import time
from contextlib import contextmanager

import pytest
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

SERVER_HOST = "127.0.0.1"
SERVER_PORT = 8080
BASE_URL = f"http://{SERVER_HOST}:{SERVER_PORT}"

# Default demo credentials (from AuthManager defaults)
USERNAME = "pilot"
PASSWORD = "dart_pilot_2025"

@contextmanager
def start_server():
    """Start the FastAPI/Socket.IO server in a subprocess."""
    env = os.environ.copy()
    # Use test-specific secret key for E2E tests
    env.setdefault("DART_SECRET_KEY", "test_secret_key_e2e_only_do_not_use_in_production")

    proc = subprocess.Popen(
        [
            "python",
            "-m",
            "uvicorn",
            "demos.web_demo.app:socket_app",
            "--host",
            SERVER_HOST,
            "--port",
            str(SERVER_PORT),
            "--log-level",
            "error",
        ],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # Give the server a moment to start
    try:
        for _ in range(30):
            try:
                import requests

                if requests.get(f"{BASE_URL}/health", timeout=1).status_code == 200:
                    break
            except Exception:
                time.sleep(0.5)
        else:
            raise RuntimeError("Server did not start within expected time")
        yield
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()

@pytest.mark.e2e
def test_web_demo_login_and_socket_connection():
    with start_server():
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()

            # Load the web demo page
            page.goto(BASE_URL, timeout=20_000)

            # Fill and submit login form
            page.fill("#username", USERNAME)
            page.fill("#password", PASSWORD)
            page.click("#login-btn")

            # Wait for status badge to indicate login success
            try:
                page.wait_for_selector(
                    "#status-badge:text('LOGGED IN')", timeout=10_000
                )
            except PlaywrightTimeout:
                pytest.fail("Login flow did not complete or status badge not updated")

            # Start button should now be enabled
            assert page.is_enabled("#start-btn"), "Start button should be enabled after login"

            # Optionally click start and verify autonomous badge
            page.click("#start-btn")
            page.wait_for_selector("#status-badge:text('AUTONOMOUS')", timeout=6_000)

            # Success criteria: socket connection established and UI updated
            browser.close() 
