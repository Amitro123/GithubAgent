import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

try:
    from repofactor.infrastructure.ui.repo_integrator_ui import app
    print("✅ Import successful!")
    print(f"App type: {type(app)}")
except Exception as e:
    print(f"❌ Import failed: {e}")
    import traceback
    traceback.print_exc()
