"""Reflex entry point - wrapper for the actual UI app."""

import sys
import os

# Add src to path - get absolute path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(os.path.dirname(current_dir), "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# Import the actual app from the infrastructure layer
from repofactor.infrastructure.ui.repo_integrator_ui import app

# Export for Reflex
__all__ = ["app"]
