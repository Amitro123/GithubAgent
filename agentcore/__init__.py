# Add this at the top of your main files or in __init__.py

from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Verify they're loaded
if os.getenv("LIGHTNING_API_KEY"):
    print("✅ Lightning AI key loaded")
else:
    print("❌ Lightning AI key missing!")