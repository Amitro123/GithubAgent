"""
Simple test to verify Lightning AI works
"""

import asyncio
import os
from dotenv import load_dotenv
load_dotenv()

from repofactor.application.services.lightning_ai_service import LightningAIClient


async def test_simple_prompt():
    """Test with super simple prompt"""
    
    client = LightningAIClient()
    
    # ✅ Very simple prompt
    simple_prompt = """You are a helpful assistant. 

Respond with ONLY this JSON (no other text):
{
  "message": "hello",
  "status": "ok"
}
"""
    
    print("🧪 Testing Lightning AI with simple prompt...")
    print(f"Prompt: {simple_prompt}")
    print()
    
    try:
        response = await client.generate(
            prompt=simple_prompt,
            max_tokens=100,
            temperature=0.1
        )
        
        print(f"✅ Response received!")
        print(f"   Type: {type(response.text)}")
        print(f"   Length: {len(response.text)}")
        print(f"   Content: {response.text}")
        
        if response.text:
            print("\n✅ SUCCESS - Lightning AI works!")
        else:
            print("\n❌ FAILED - Empty response even with simple prompt")
            print("   This suggests an API or configuration issue")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
    
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(test_simple_prompt())
