# quick_test.py
"""
Quick integration test to verify all services work together
Run this to test without using full quota
"""

from dotenv import load_dotenv
load_dotenv()

import asyncio
import sys
from pathlib import Path

# Add src to path if needed
src_path = Path(__file__).parent / 'src'
if src_path.exists():
    sys.path.insert(0, str(src_path))

from repofactor.application.services.lightning_ai_service import (
    LightningAIClient,
    CodeAnalysisAgent,
    LightningModel
)
from repofactor.application.services.repo_integrator_service import (
    RepoIntegratorService
)


async def test_lightning_client():
    """Test 1: Lightning AI client basics"""
    print("="*60)
    print("Test 1: Lightning AI Client")
    print("="*60)
    
    try:
        client = LightningAIClient()
        print(f"✅ Client created successfully")
        print(f"   Quota: {client.get_remaining_quota()}/{client.monthly_quota}")
        
        # Don't make actual API call to save quota
        print("✅ Test passed (no API call made)")
        
        await client.close()
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False


async def test_code_analysis_agent():
    """Test 2: Code Analysis Agent setup"""
    print("\n" + "="*60)
    print("Test 2: Code Analysis Agent")
    print("="*60)
    
    try:
        agent = CodeAnalysisAgent(
            preferred_model=LightningModel.CODE_LLAMA_34B
        )
        print(f"✅ Agent created with model: {agent.model.value}")
        print(f"   Quota: {agent.client.get_remaining_quota()}/20")
        
        # Don't make actual API call
        print("✅ Test passed (no API call made)")
        
        await agent.close()
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False


async def test_repo_integrator_service():
    """Test 3: Full integration service"""
    print("\n" + "="*60)
    print("Test 3: RepoIntegrator Service")
    print("="*60)
    
    try:
        service = RepoIntegratorService(
            preferred_model=LightningModel.GEMINI_2_5_FLASH
        )
        print("✅ Service created successfully")
        print(f"   Model: {service.model.value}")
        print(f"   Git service: {service.repo_service is not None}")
        
        # Test validation (no API call, no quota used)
        test_url = "https://github.com/microsoft/LLMLingua"
        is_valid = await service.validate_repository(test_url)
        print(f"✅ URL validation works: {test_url} -> {is_valid}")
        
        # Don't run full analysis to save quota
        print("✅ Test passed (no full analysis made)")
        
        await service.close()
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_full_flow_with_small_repo():
    """Test 4: Full flow with tiny repo (uses 1 API call)"""
    print("\n" + "="*60)
    print("Test 4: Full Integration Flow (USES 1 API CALL)")
    print("="*60)
    
    # Ask user before using quota
    print("\n⚠️  This test will use 1 Lightning AI call from your quota.")
    response = input("Continue? (y/n): ")
    
    if response.lower() != 'y':
        print("⏭️  Skipped")
        return True
    
    try:
        service = RepoIntegratorService()
        
        # Use a small, simple repo
        test_repo = "https://github.com/gvanrossum/patma"  # Small Python repo
        
        print(f"\n📦 Testing with: {test_repo}")
        print("⏳ This may take 30-60 seconds...")
        
        result = await service.analyze_repository(
            repo_url=test_repo,
            user_instructions="Analyze the pattern matching implementation",
            max_files=3  # Limit to save time
        )
        
        print("\n✅ Analysis Complete!")
        print(f"   Repository: {result.repo_name}")
        print(f"   Files to modify: {len(result.affected_files)}")
        print(f"   Dependencies: {len(result.dependencies)}")
        print(f"   Risks: {len(result.risks)}")
        print(f"   Estimated time: {result.estimated_time}")
        
        if result.affected_files:
            print("\n   Affected files:")
            for file_info in result.affected_files[:3]:
                path = file_info.get('path', 'unknown')
                confidence = file_info.get('confidence', 0)
                print(f"     • {path} ({confidence}% confidence)")
        
        await service.close()
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("🧪 RepoIntegrator - Integration Tests")
    print("="*60)
    
    results = []
    
    # Test 1: Lightning AI Client
    results.append(("Lightning Client", await test_lightning_client()))
    
    # Test 2: Code Analysis Agent
    results.append(("Analysis Agent", await test_code_analysis_agent()))
    
    # Test 3: RepoIntegrator Service
    results.append(("Integrator Service", await test_repo_integrator_service()))
    
    # Test 4: Full flow (optional, uses quota)
    results.append(("Full Flow", await test_full_flow_with_small_repo()))
    
    # Summary
    print("\n" + "="*60)
    print("📊 Test Summary")
    print("="*60)
    
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    all_passed = all(result[1] for result in results)
    
    print("\n" + "="*60)
    if all_passed:
        print("✅ All tests passed!")
        print("\nYou're ready to:")
        print("1. Run full integration: python -m repofactor.application.services.repo_integrator_service")
        print("2. Start UI: cd src/repofactor/infrastructure/ui && reflex run")
    else:
        print("❌ Some tests failed. Check errors above.")
    
    print("="*60)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)