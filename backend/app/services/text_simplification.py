"""
Text Simplification Service for UMARead "Crunch Text" feature
"""
import hashlib
import json
from typing import Optional
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, text
from datetime import datetime
import uuid
import os

from ..config.ai_models import QUESTION_GENERATION_MODEL
from ..models.reading import ReadingChunk, ReadingAssignment


class TextSimplificationCache(BaseModel):
    """Model for text simplification cache entries"""
    id: str
    assignment_id: str
    chunk_number: int
    content_hash: str
    original_grade_level: Optional[int]
    target_grade_level: int
    simplified_text: str
    created_at: datetime


def create_content_hash(text: str) -> str:
    """Create a hash of the text content for caching"""
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def get_simplification_prompt(original_text: str, original_grade_level: Optional[str], target_grade_level: int, content_type: str = "prose") -> str:
    """Generate the AI prompt for text simplification"""
    
    # Parse numeric grade level if it's a string
    if original_grade_level:
        try:
            import re
            grade_match = re.search(r'(\d+)', str(original_grade_level))
            numeric_original = int(grade_match.group(1)) if grade_match else 6
        except (ValueError, AttributeError):
            numeric_original = 6
    else:
        numeric_original = 6
    
    grade_reduction = max(2, numeric_original - target_grade_level)
    
    prompt = f"""You are an expert at rewriting text to make it easier to read while preserving all important information and educational value.

Your task is to rewrite the following text to be approximately {grade_reduction} grade levels easier to read.

ORIGINAL TEXT:
{original_text}

SIMPLIFICATION GUIDELINES:
1. PRESERVE ALL KEY INFORMATION - Don't remove any important facts, events, or concepts
2. MAINTAIN EDUCATIONAL VALUE - Keep terms students should learn, but add brief explanations if needed
3. SIMPLIFY SENTENCE STRUCTURE:
   - Break complex sentences into shorter, simpler ones
   - Use active voice instead of passive voice when possible
   - Reduce subordinate clauses and complex conjunctions
4. VOCABULARY SIMPLIFICATION:
   - Replace advanced vocabulary with more common alternatives
   - Keep educational terms but add context clues
   - Clarify pronoun references (replace "it" with the specific noun)
5. STRUCTURE IMPROVEMENTS:
   - Break up long paragraphs if needed
   - Use clearer transitions between ideas
   - Maintain chronological order for events
6. PRESERVE TONE AND STYLE:
   - Keep the same narrative voice for fiction
   - Maintain the informational tone for non-fiction
   - Preserve any dialogue or quotes exactly

IMPORTANT: The rewritten text should be roughly the same length as the original. Don't just shorten it - make it easier to understand while keeping all the content.

Please provide only the simplified text without any additional commentary or explanation."""

    return prompt


async def get_cached_simplification(
    db: AsyncSession,
    assignment_id: str,
    chunk_number: int,
    content_hash: str,
    target_grade_level: int
) -> Optional[str]:
    """Check if we have a cached simplification for this content"""
    
    try:
        # Execute raw SQL since we don't have SQLAlchemy model yet
        result = await db.execute(
            text("""
            SELECT simplified_text FROM text_simplification_cache
            WHERE assignment_id = :assignment_id 
            AND chunk_number = :chunk_number 
            AND content_hash = :content_hash 
            AND target_grade_level = :target_grade_level
            """),
            {
                "assignment_id": assignment_id,
                "chunk_number": chunk_number,
                "content_hash": content_hash,
                "target_grade_level": target_grade_level
            }
        )
        
        row = result.fetchone()
        return row[0] if row else None
    except Exception as e:
        print(f"Warning: Could not check cache (table may not exist): {e}")
        return None


async def cache_simplification(
    db: AsyncSession,
    assignment_id: str,
    chunk_number: int,
    content_hash: str,
    original_grade_level: Optional[str],
    target_grade_level: int,
    simplified_text: str
) -> None:
    """Cache the simplified text for future use"""
    
    try:
        await db.execute(
            text("""
            INSERT INTO text_simplification_cache 
            (id, assignment_id, chunk_number, content_hash, original_grade_level, target_grade_level, simplified_text, created_at)
            VALUES (:id, :assignment_id, :chunk_number, :content_hash, :original_grade_level, :target_grade_level, :simplified_text, :created_at)
            ON CONFLICT (assignment_id, chunk_number, content_hash, target_grade_level) DO NOTHING
            """),
            {
                "id": str(uuid.uuid4()),
                "assignment_id": assignment_id,
                "chunk_number": chunk_number,
                "content_hash": content_hash,
                "original_grade_level": original_grade_level,
                "target_grade_level": target_grade_level,
                "simplified_text": simplified_text,
                "created_at": datetime.utcnow()
            }
        )
        await db.commit()
    except Exception as e:
        print(f"Warning: Could not cache simplification (table may not exist): {e}")
        # Don't fail if we can't cache - just continue without caching


async def simplify_text_with_ai(
    original_text: str,
    original_grade_level: Optional[str],
    target_grade_level: int,
    content_type: str = "prose"
) -> str:
    """Use AI to simplify the text"""
    
    prompt = get_simplification_prompt(
        original_text, 
        original_grade_level, 
        target_grade_level, 
        content_type
    )
    
    try:
        # Use Google Generative AI directly (same pattern as question generation)
        import google.generativeai as genai
        
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        model = genai.GenerativeModel('gemini-2.0-flash')
        
        # Generate simplified text
        response = model.generate_content(prompt)
        return response.text.strip()
        
    except Exception as e:
        print(f"Error in AI text simplification: {e}")
        # Fallback: return original text with a note
        return f"[Simplified version temporarily unavailable]\n\n{original_text}"


async def simplify_chunk_text(
    db: AsyncSession,
    assignment_id: str,
    chunk_number: int
) -> str:
    """Main function to simplify chunk text with caching"""
    
    # Get the assignment and chunk
    assignment_result = await db.execute(
        select(ReadingAssignment).where(ReadingAssignment.id == assignment_id)
    )
    assignment = assignment_result.scalar_one_or_none()
    
    if not assignment:
        raise ValueError("Assignment not found")
    
    chunk_result = await db.execute(
        select(ReadingChunk).where(
            and_(
                ReadingChunk.assignment_id == assignment_id,
                ReadingChunk.chunk_order == chunk_number
            )
        )
    )
    chunk = chunk_result.scalar_one_or_none()
    
    if not chunk:
        raise ValueError(f"Chunk {chunk_number} not found")
    
    # Create content hash for caching
    content_hash = create_content_hash(chunk.content)
    
    # Calculate target grade level (2 levels easier)
    # Parse grade level from string (e.g., "6th Grade" -> 6)
    original_grade_level = assignment.grade_level
    try:
        # Extract numeric part from grade level string
        import re
        grade_match = re.search(r'(\d+)', str(original_grade_level) if original_grade_level else '6')
        numeric_grade = int(grade_match.group(1)) if grade_match else 6
    except (ValueError, AttributeError):
        numeric_grade = 6  # Default fallback
    
    target_grade_level = max(1, numeric_grade - 2)
    
    # Check cache first
    cached_result = await get_cached_simplification(
        db, assignment_id, chunk_number, content_hash, target_grade_level
    )
    
    if cached_result:
        return cached_result
    
    # Generate simplified text with AI
    simplified_text = await simplify_text_with_ai(
        chunk.content,
        original_grade_level,
        target_grade_level,
        assignment.literary_form or "prose"
    )
    
    # Cache the result
    await cache_simplification(
        db, assignment_id, chunk_number, content_hash,
        original_grade_level, target_grade_level, simplified_text
    )
    
    return simplified_text