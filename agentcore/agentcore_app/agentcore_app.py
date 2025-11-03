"""
Reflex app entry point for agentcore.
This file re-exports the app from the actual implementation.
"""

from repofactor.infrastructure.ui.repo_integrator_ui import app

__all__ = ["app"]
