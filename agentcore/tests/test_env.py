# test_env.py
"""Quick test to verify environment setup"""

from dotenv import load_dotenv
import os

# Load .env
load_dotenv()

print("🔍 Checking environment variables...\n")

# Check Lightning AI
lightning_key = os.getenv("LIGHTNING_API_KEY")
if lightning_key:
    print(f"✅ LIGHTNING_API_KEY: {lightning_key[:10]}...")
else:
    print("❌ LIGHTNING_API_KEY: Not found")

# Check GitHub
github_token = os.getenv("GITHUB_TOKEN")
if github_token:
    print(f"✅ GITHUB_TOKEN: {github_token[:10]}...")
else:
    print("⚠️  GITHUB_TOKEN: Not found (optional)")

# Check cache dir
cache_dir = os.getenv("REPO_CACHE_DIR", "./cache/repos")
print(f"📁 REPO_CACHE_DIR: {cache_dir}")

print("\n" + "="*50)
if lightning_key:
    print("✅ Configuration OK! You can run the tests.")
else:
    print("❌ Please add LIGHTNING_API_KEY to .env file")
