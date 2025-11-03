import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from repofactor.infrastructure.ui.repo_integrator_ui import app

__all__ = ["app"]
