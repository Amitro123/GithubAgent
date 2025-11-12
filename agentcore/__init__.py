# Add this at the top of your main files or in __init__.py
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    def load_dotenv():
        pass
import os


# Verify they're loaded
if os.getenv("LIGHTNING_API_KEY"):
    print("[OK] Lightning AI key loaded")
else:
    print("[ERROR] Lightning AI key missing!")