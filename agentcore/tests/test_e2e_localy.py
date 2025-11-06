# tests/test_e2e_local.py
"""
End-to-end test of the integration flow
Run locally to verify everything works
"""

import sys
import os
from pathlib import Path

# Add src to Python path
project_root = Path(__file__).parent.parent.parent  # Go up from agentcore/tests/ to project root
src_path = project_root / "src"
sys.path.insert(0, str(src_path))
print(f"Added to path: {src_path}")  # Debug

import asyncio
from dotenv import load_dotenv
load_dotenv()

from repofactor.application.services.repo_integrator_service import (
    RepoIntegratorService
)


async def test_simple_repo():
    """Test with a small, simple repository"""
    
    print("="*60)
    print("🧪 E2E Test: Simple Repository")
    print("="*60)
    
    service = RepoIntegratorService()
    
    # Use a TINY repo to test quickly
    test_repo = "https://github.com/tiangolo/fastapi"
    
    try:
        print("\n1️⃣ Validating repository...")
        is_valid = await service.validate_repository(test_repo)
        assert is_valid, "Repo validation failed"
        print("✅ Repository valid")
        
        print("\n2️⃣ Getting repo info...")
        info = await service.get_repository_info(test_repo)
        print(f"✅ Repo: {info['full_name']}")
        print(f"   Stars: {info['stars']}")
        print(f"   Language: {info['language']}")
        
        print("\n3️⃣ Analyzing repository...")
        print("   (This uses 1 Lightning AI call)")
        
        result = await service.analyze_repository(
            repo_url=test_repo,
            user_instructions="Add rate limiting to API endpoints",
            max_files=3  # IMPORTANT: Limit files for testing
        )
        
        print("\n✅ Analysis Complete!")
        print(f"   Files to modify: {result.file_count}")
        print(f"   Dependencies: {len(result.dependencies)}")
        print(f"   Risks: {len(result.risks)}")
        
        # Print details
        print("\n📋 Affected Files:")
        for file in result.affected_files[:3]:
            print(f"   • {file.path}")
            print(f"     Reason: {file.reason}")
            print(f"     Confidence: {file.confidence:.0%}")
        
        print("\n📦 Dependencies:")
        for dep in result.dependencies:
            print(f"   • {dep}")
        
        print("\n⚠️  Risks:")
        for risk in result.risks:
            print(f"   • {risk}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        await service.close()


async def test_validation_only():
    """Quick test without using API quota"""
    
    print("="*60)
    print("🧪 Quick Test: Validation Only (No Quota)")
    print("="*60)
    
    service = RepoIntegratorService()
    
    test_cases = [
        ("https://github.com/microsoft/LLMLingua", True),
        ("https://github.com/invalid/nonexistent", False),
        ("not-a-url", False),
    ]
    
    for url, expected in test_cases:
        result = await service.validate_repository(url)
        status = "✅" if result == expected else "❌"
        print(f"{status} {url}: {result}")


if __name__ == "__main__":
    print("Choose test:")
    print("1. Quick validation test (no quota)")
    print("2. Full E2E test (uses 1 API call)")
    
    choice = input("\nEnter choice (1 or 2): ")
    
    if choice == "1":
        asyncio.run(test_validation_only())
    else:
        asyncio.run(test_simple_repo())