#!/usr/bin/env python3
"""
LNNTÉ / DNCL Phone Number Verifier
Main entry point for the application.

This tool verifies Canadian phone numbers against the National Do Not Call List (DNCL)
using the official LNNTÉ consumer verification portal.
"""

import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

# Set up Playwright environment BEFORE importing modules that use it
from src.bundle_utils import setup_playwright_env
setup_playwright_env()

from src.ui import main

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    main()
