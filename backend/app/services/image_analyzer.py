import google.generativeai as genai
from typing import List, Optional
import os
from app.models.image_analysis import ImageAnalysis
from app.config.ai_models import IMAGE_ANALYSIS_MODEL
from app.config.ai_config import get_gemini_config
import logging
from PIL import Image
import json

logger = logging.getLogger(__name__)

class ImageAnalyzer:
    def __init__(self):
        # Get configuration
        config = get_gemini_config()
        
        # Configure Gemini API
        genai.configure(api_key=config.api_key)
        
        # Use configured model
        self.model = genai.GenerativeModel(IMAGE_ANALYSIS_MODEL)
        
        logger.info(f"ImageAnalyzer initialized with model: {IMAGE_ANALYSIS_MODEL}")
    
    def _get_system_prompt(self) -> str:
        return """You are analyzing an educational image that appears within a reading assignment. Your task is to create a detailed description that will be used to generate comprehension questions and evaluate student answers about this image.

STEP 1 - IDENTIFY IMAGE TYPE:
First, identify what type of image this is:
- Quantitative: chart, graph, table, data visualization, timeline with dates/numbers
- Diagram: labeled diagram, flowchart, map, scientific illustration  
- Photograph/Illustration: photo, artistic illustration, cartoon, realistic drawing

STEP 2 - EXTRACT ALL DATA (if applicable):
If the image contains ANY numbers, data, or labels, extract EVERYTHING:
- For graphs: List all axis labels, ranges, intervals, and EVERY data point value
- For charts: List all categories, percentages, values, and totals
- For tables: List all column headers, row labels, and cell values
- For diagrams: List all labels, measurements, and annotations
- For maps: List all location names, distances, scales, and legends

STEP 3 - COMPREHENSIVE DESCRIPTION:
Provide a 200-300 word description that includes:
1. What the image shows (be specific and objective)
2. How it relates to the surrounding text passage
3. Educational significance and key learning points
4. Specific details students should notice
5. Potential misconceptions to address

CRITICAL: If numbers exist, extract EVERY SINGLE ONE - be precise with values."""

    async def analyze_image(
        self, 
        image_path: str, 
        surrounding_text: List[str],
        assignment_metadata: dict
    ) -> ImageAnalysis:
        """Analyze an image in educational context"""
        
        # Build context for the prompt
        context = f"""
CONTEXT OF THE IMAGE:
The image appears in the following text passage(s):
---
{chr(10).join(surrounding_text)}
---

Assignment metadata:
- Grade Level: {assignment_metadata.get('grade_level')}
- Subject: {assignment_metadata.get('subject')}
- Work Type: {assignment_metadata.get('work_type')}
"""
        
        try:
            # Upload image to Gemini
            logger.info(f"Uploading image from path: {image_path}")
            uploaded_file = genai.upload_file(image_path)
            logger.info(f"Image uploaded successfully: {uploaded_file.name}")
            
            # Create the full prompt
            full_prompt = f"""{self._get_system_prompt()}

{context}

Based on the actual image provided and the educational context, provide your analysis in the following JSON format:
{{
    "image_type": "Quantitative|Diagram|Photograph",
    "description": "200-300 word comprehensive description",
    "key_learning_points": ["point1", "point2", ...],
    "potential_misconceptions": ["misconception1", "misconception2", ...],
    "data_extracted": {{
        "labels": ["label1", "label2", ...],
        "values": ["value1", "value2", ...],
        "units": ["unit1", "unit2", ...],
        "axes_labels": {{"x": "x_label", "y": "y_label"}},
        "title": "chart/graph title if present"
    }}
}}

For data_extracted: Only include if the image contains quantitative data (charts, graphs, tables). Otherwise, set to null.
IMPORTANT: Return ONLY valid JSON, no additional text."""
            
            # Generate content with the image
            logger.info("Sending image to Gemini for analysis...")
            response = self.model.generate_content([full_prompt, uploaded_file])
            
            # Log the raw response
            logger.info(f"Gemini response received, length: {len(response.text)}")
            logger.debug(f"Raw response: {response.text[:500]}...")  # Log first 500 chars
            
            # Parse the JSON response
            try:
                # Extract JSON from the response (in case there's extra text)
                json_start = response.text.find('{')
                json_end = response.text.rfind('}') + 1
                
                if json_start == -1 or json_end == 0:
                    raise ValueError("No JSON found in response")
                
                json_text = response.text[json_start:json_end]
                result_data = json.loads(json_text)
                
                # Log successful parsing
                logger.info(f"Successfully parsed JSON response with image_type: {result_data.get('image_type')}")
                
                # Convert to ImageAnalysis model
                return ImageAnalysis(**result_data)
                
            except (json.JSONDecodeError, ValueError) as e:
                logger.error(f"Failed to parse JSON response: {e}")
                logger.error(f"Raw response: {response.text}")
                raise ValueError(f"Invalid JSON response from Gemini: {e}")
            
        except Exception as e:
            logger.error(f"Error analyzing image with Gemini: {str(e)}")
            raise
        finally:
            # Clean up uploaded file
            try:
                if 'uploaded_file' in locals():
                    genai.delete_file(uploaded_file.name)
                    logger.info("Cleaned up uploaded file")
            except Exception as cleanup_error:
                logger.warning(f"Failed to clean up uploaded file: {cleanup_error}")