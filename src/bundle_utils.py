"""
Utilities for bundled executable support.
Handles finding Playwright browsers when running as a PyInstaller bundle.
"""

import os
import sys
from pathlib import Path


def is_bundled() -> bool:
    """Check if running as a PyInstaller bundle."""
    return getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')


def get_bundle_dir() -> Path:
    """Get the bundle directory (where the .exe is located)."""
    if is_bundled():
        return Path(sys.executable).parent
    return Path(__file__).parent.parent


def get_browsers_path() -> str:
    """
    Get the path to Playwright browsers.
    When bundled, browsers are in a 'browsers' folder next to the .exe.
    """
    if is_bundled():
        browsers_path = get_bundle_dir() / "browsers"
        if browsers_path.exists():
            return str(browsers_path)
    return None


def setup_playwright_env():
    """
    Set up environment variables for Playwright to find bundled browsers.
    Call this before importing playwright.
    """
    browsers_path = get_browsers_path()
    if browsers_path:
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = browsers_path
