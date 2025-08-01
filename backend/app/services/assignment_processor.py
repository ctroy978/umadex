from app.services.image_analyzer import ImageAnalyzer
from app.core.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.models.reading import ReadingAssignment, ReadingChunk, AssignmentImage
import asyncio
import logging
import tempfile
import httpx
import os
from datetime import datetime
import json

logger = logging.getLogger(__name__)

class AssignmentImageProcessor:
    def __init__(self):
        self.analyzer = ImageAnalyzer()
    
    async def process_assignment_images(self, assignment_id: str):
        """Process all images for an assignment after submission"""
        
        async for db in get_db():
            try:
                # Get assignment details
                result = await db.execute(
                    select(ReadingAssignment).where(ReadingAssignment.id == assignment_id)
                )
                assignment = result.scalar_one_or_none()
                
                if not assignment:
                    logger.error(f"Assignment {assignment_id} not found")
                    return
                
                # Get all chunks to find image context
                chunks_result = await db.execute(
                    select(ReadingChunk)
                    .where(ReadingChunk.assignment_id == assignment_id)
                    .order_by(ReadingChunk.chunk_order)
                )
                chunks = chunks_result.scalars().all()
                
                # Get all images
                images_result = await db.execute(
                    select(AssignmentImage)
                    .where(AssignmentImage.assignment_id == assignment_id)
                )
                images = images_result.scalars().all()
                
                # Process each image
                for image in images:
                    # Find chunks containing this image
                    relevant_chunks = [
                        chunk.content 
                        for chunk in chunks 
                        if f"<image>{image.image_tag}</image>" in chunk.content
                    ]
                    
                    # Use the display URL directly (it's now a public Supabase URL)
                    image_url = image.display_url
                    
                    # If the URL is relative (legacy images), build full URL
                    if image_url.startswith('/'):
                        base_url = os.getenv("BACKEND_URL", "http://localhost:8000")
                        image_url = f"{base_url}{image_url}"
                    
                    # Download image from URL to temp file
                    async with httpx.AsyncClient() as client:
                        response = await client.get(image_url)
                        response.raise_for_status()
                        
                        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
                            tmp.write(response.content)
                            tmp_path = tmp.name
                    
                    try:
                        # Analyze image
                        analysis = await self.analyzer.analyze_image(
                            tmp_path,
                            relevant_chunks,
                            {
                                'grade_level': assignment.grade_level,
                                'subject': assignment.subject,
                                'work_type': assignment.work_type
                            }
                        )
                        
                        # Log the AI analysis results
                        logger.info("=" * 80)
                        logger.info(f"AI ANALYSIS RESULTS FOR IMAGE: {image.image_tag}")
                        logger.info("=" * 80)
                        logger.info(f"Image Type: {analysis.image_type.value}")
                        logger.info(f"Description: {analysis.description}")
                        logger.info(f"Key Learning Points: {analysis.key_learning_points}")
                        logger.info(f"Potential Misconceptions: {analysis.potential_misconceptions}")
                        
                        if analysis.data_extracted:
                            logger.info("Data Extracted:")
                            data_dict = analysis.data_extracted.model_dump()
                            for key, value in data_dict.items():
                                if value:
                                    logger.info(f"  - {key}: {value}")
                        
                        logger.info("=" * 80)
                        
                        # Create comprehensive description including all analysis data
                        full_description = {
                            "description": analysis.description,
                            "image_type": analysis.image_type.value,
                            "key_learning_points": analysis.key_learning_points,
                            "potential_misconceptions": analysis.potential_misconceptions,
                            "data_extracted": analysis.data_extracted.model_dump() if analysis.data_extracted else None
                        }
                        
                        # Store analysis
                        await db.execute(
                            update(AssignmentImage)
                            .where(AssignmentImage.id == image.id)
                            .values(
                                ai_description=json.dumps(full_description),
                                description_generated_at=datetime.utcnow()
                            )
                        )
                        await db.commit()
                        
                        logger.info(f"Processed image {image.image_tag} for assignment {assignment_id}")
                        
                    except Exception as e:
                        logger.error(f"Error processing image {image.image_tag}: {str(e)}")
                        # Continue with other images even if one fails
                        continue
                    finally:
                        # Clean up temp file
                        if os.path.exists(tmp_path):
                            os.unlink(tmp_path)
                
                # Mark assignment as processed
                await db.execute(
                    update(ReadingAssignment)
                    .where(ReadingAssignment.id == assignment_id)
                    .values(images_processed=True)
                )
                await db.commit()
                
                logger.info(f"Completed processing all images for assignment {assignment_id}")
                
            except Exception as e:
                logger.error(f"Error processing assignment {assignment_id}: {str(e)}")
                raise
            finally:
                await db.close()