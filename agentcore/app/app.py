"""Reflex app entry point."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Import the actual UI app
from repofactor.infrastructure.ui.repo_integrator_ui import app

# Export for Reflex
__all__ = ["app"]
