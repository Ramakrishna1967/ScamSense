"""
Direct Gemini API Test Script
Run this to verify the Gemini API is working correctly.
"""
import asyncio
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

async def test_gemini():
    print("=" * 60)
    print("SCAMSHIELD GEMINI API DIAGNOSTIC TEST")
    print("=" * 60)
    
    # Step 1: Check environment
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("[ERROR] GEMINI_API_KEY not found in environment")
        return
    print(f"[OK] API Key found: {api_key[:10]}...")
    
    # Step 2: Test LangChain import
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
        from langchain_core.messages import HumanMessage, SystemMessage
        print("[OK] LangChain imports successful")
    except ImportError as e:
        print(f"[ERROR] LangChain import failed: {e}")
        print("   Run: pip install langchain-google-genai")
        return
    
    # Step 3: Initialize LLM (WITHOUT safety settings that might cause import issues)
    model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    print(f"[INFO] Using model: {model}")
    
    try:
        llm = ChatGoogleGenerativeAI(
            model=model,
            google_api_key=api_key,
            temperature=0.1,
            max_output_tokens=1000
        )
        print("[OK] LLM initialized successfully")
    except Exception as e:
        print(f"[ERROR] LLM initialization failed: {type(e).__name__}: {e}")
        return
    
    # Step 4: Test a simple scam analysis
    system_prompt = """You are a scam detection AI. Analyze the message and respond ONLY in JSON:
{"risk_score": <0-100>, "detected_tactics": ["list"], "explanation": "brief reason"}"""
    
    user_message = "URGENT: Your bank account has been suspended. Click http://bit.ly/verify-now to restore access or you will be arrested."
    
    print(f"\n[INFO] Sending test message...")
    print(f"   Message: {user_message[:50]}...")
    
    try:
        response = await llm.ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Analyze this: {user_message}")
        ])
        
        print(f"\n[SUCCESS] GEMINI RESPONSE RECEIVED:")
        print("-" * 40)
        print(response.content)
        print("-" * 40)
        
        # Try to parse it
        import json
        import re
        
        text = response.content.strip()
        # Handle markdown code blocks
        if "```" in text:
            match = re.search(r'```(?:json)?\n?(.*?)```', text, re.DOTALL)
            if match:
                text = match.group(1).strip()
        
        # Find JSON object
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            text = json_match.group(0)
        
        parsed = json.loads(text)
        print(f"\n[OK] PARSING SUCCESSFUL:")
        print(f"   Risk Score: {parsed.get('risk_score', 'N/A')}")
        print(f"   Tactics: {parsed.get('detected_tactics', [])}")
        print(f"   Explanation: {parsed.get('explanation', 'N/A')}")
        
    except Exception as e:
        import traceback
        print(f"\n[ERROR] API CALL FAILED:")

        print(f"   Error Type: {type(e).__name__}")
        print(f"   Error Message: {str(e)}")
        print("\n   Full Traceback:")
        traceback.print_exc()

if __name__ == "__main__":
    print("\nStarting diagnostic test...\n")
    asyncio.run(test_gemini())
    print("\n" + "=" * 60)
    print("Test complete. Check output above for errors.")
    print("=" * 60)
