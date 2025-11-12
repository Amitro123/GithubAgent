# test_litai.py
"""
Test LitAI SDK directly to see what it returns
"""

import os
import asyncio
from dotenv import load_dotenv
load_dotenv()

from litai import LLM

async def test_litai():
    """Test LitAI directly"""
    
    print("🧪 Testing LitAI SDK directly...")
    
    # Initialize
    api_key = os.getenv("LIGHTNING_API_KEY")
    print(f"API Key: {api_key[:20]}...")
    
    model = "google/gemini-2.5-flash-lite-preview-06-17"
    print(f"Model: {model}")
    
    llm = LLM(model=model)
    
    # Simple prompt
    prompt = "Say 'hello world' in JSON format: {\"message\": \"hello world\"}"
    print(f"\nPrompt: {prompt}")
    
    # Call chat
    print("\n🔄 Calling llm.chat()...")
    
    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(
        None,
        llm.chat,
        prompt
    )
    
    # Debug output
    print(f"\n✅ Response received!")
    print(f"Type: {type(response)}")
    print(f"Repr: {repr(response)}")
    
    if hasattr(response, '__dict__'):
        print(f"Attributes: {response.__dict__}")
    
    if isinstance(response, dict):
        print(f"Keys: {response.keys()}")
        print(f"Values: {response}")
    
    if isinstance(response, str):
        print(f"String length: {len(response)}")
        print(f"Content: {response}")
    
    print(f"\n🎯 str(response): {str(response)}")
    print(f"🎯 len(str(response)): {len(str(response))}")

if __name__ == "__main__":
    asyncio.run(test_litai())
