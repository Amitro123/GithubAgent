import sys
from pathlib import Path

# Add src to Python path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root / 'src'))
