"""RepoIntegrator - Entry point for Reflex application."""

# Import the app from our infrastructure layer
from repofactor.infrastructure.ui.repo_integrator_ui import app

# This makes the app available to Reflex
__all__ = ["app"]
