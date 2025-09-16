#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(__file__))

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

def test_api_key():
    """Test the GEMINI API key"""
    load_dotenv()

    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "your-api-key-here")

    print("🔍 Testing GEMINI API Key...")
    print(f"API Key found: {GEMINI_API_KEY is not None and GEMINI_API_KEY != 'your-api-key-here'}")
    print(f"API Key starts with 'AIza': {GEMINI_API_KEY.startswith('AIza') if GEMINI_API_KEY else False}")
    print(f"API Key length: {len(GEMINI_API_KEY) if GEMINI_API_KEY else 0}")
    print(f"API Key has whitespace: {GEMINI_API_KEY != GEMINI_API_KEY.strip() if GEMINI_API_KEY else False}")

    if not GEMINI_API_KEY or GEMINI_API_KEY == "your-api-key-here":
        print("❌ ERROR: GEMINI_API_KEY not configured properly")
        return False

    if GEMINI_API_KEY != GEMINI_API_KEY.strip():
        print("❌ ERROR: GEMINI_API_KEY contains leading/trailing whitespace")
        print("💡 Remove any spaces from the API key in your .env file")
        return False

    if not GEMINI_API_KEY.startswith("AIza"):
        print("❌ ERROR: GEMINI_API_KEY appears to be invalid (should start with 'AIza')")
        return False

    try:
        print("🔄 Testing LLM initialization...")
        llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=GEMINI_API_KEY)
        print("✅ LLM initialized successfully")

        print("🔄 Testing simple API call...")
        response = llm.invoke("Hello, can you respond with just 'API test successful'?")
        print(f"✅ API call successful: {response.content.strip()}")

        return True

    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        if "API_KEY_INVALID" in str(e):
            print("💡 This usually means the API key is invalid or expired")
        elif "PERMISSION_DENIED" in str(e):
            print("💡 This usually means the API key doesn't have the right permissions")
        elif "QUOTA_EXCEEDED" in str(e):
            print("💡 This usually means you've exceeded your API quota")
        return False

if __name__ == "__main__":
    success = test_api_key()
    if success:
        print("\n🎉 API Key test PASSED! Your GEMINI API key is working correctly.")
    else:
        print("\n❌ API Key test FAILED! Please check your GEMINI_API_KEY in the .env file.")
        print("\n🔧 To fix this:")
        print("1. Go to https://makersuite.google.com/app/apikey")
        print("2. Create or copy a valid API key")
        print("3. Update your .env file with: GEMINI_API_KEY=your_actual_key_here")