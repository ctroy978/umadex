"""
AI Helper for debate responses using Google Gemini
"""
import google.generativeai as genai
from typing import Optional
import logging
import asyncio
from app.config.ai_config import get_gemini_config

logger = logging.getLogger(__name__)

# Initialize Gemini
config = get_gemini_config()
genai.configure(api_key=config.api_key)
model = genai.GenerativeModel('gemini-2.0-flash')

async def get_ai_response(prompt: str, max_tokens: int = 300) -> str:
    """
    Generate AI response using Google Gemini.
    """
    try:
        # Configure generation settings
        generation_config = {
            "temperature": config.temperature,
            "max_output_tokens": max_tokens,
            "top_p": 0.95,
        }
        
        # Generate response in a thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: model.generate_content(
                prompt,
                generation_config=generation_config
            )
        )
        
        # Extract text from response
        if response.text:
            return response.text.strip()
        else:
            logger.error("No text in Gemini response")
            return "I apologize, but I'm unable to generate a response at this moment."
            
    except Exception as e:
        logger.error(f"Error generating Gemini response: {str(e)}")
        # Return a fallback response
        return "I apologize, but I'm experiencing technical difficulties. Please try again."