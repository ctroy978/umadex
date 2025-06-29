import asyncio
import os
import google.generativeai as genai

# Test Gemini API directly
async def test_gemini():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: GEMINI_API_KEY not set")
        return
    
    print(f"API Key: {api_key[:10]}...")
    
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.0-flash')
    
    try:
        response = model.generate_content("Say hello")
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}")

if __name__ == "__main__":
    asyncio.run(test_gemini())