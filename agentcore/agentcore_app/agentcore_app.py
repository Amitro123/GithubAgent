"""
Reflex app entry point for agentcore.
This is the main entry point for the Reflex application.
"""

from src.repofactor.infrastructure.ui.repo_integrator_ui import app as agentcore_app
import reflex as rx

# The following is a placeholder for the actual app definition.
# The actual app is defined in src.repofactor.infrastructure.ui.repo_integrator_ui.
app = agentcore_app

if __name__ == "__main__":
    app.run()
