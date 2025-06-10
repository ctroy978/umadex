"""
Pronunciation service for fetching audio URLs and phonetic text from Free Dictionary API
"""
import aiohttp
import logging
from typing import Optional, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.models.vocabulary import VocabularyWord

logger = logging.getLogger(__name__)

class PronunciationService:
    """Service for fetching pronunciation data from Free Dictionary API"""
    
    BASE_URL = "https://api.dictionaryapi.dev/api/v2/entries/en"
    
    @staticmethod
    async def fetch_pronunciation_data(word: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Fetch pronunciation data from Free Dictionary API
        
        Args:
            word: The word to get pronunciation for
            
        Returns:
            Tuple of (audio_url, phonetic_text) or (None, None) if not found
        """
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{PronunciationService.BASE_URL}/{word.lower()}"
                
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status != 200:
                        logger.debug(f"No pronunciation data found for word: {word}")
                        return None, None
                    
                    data = await response.json()
                    
                    if not data or not isinstance(data, list) or len(data) == 0:
                        return None, None
                    
                    # Get the first entry
                    entry = data[0]
                    
                    # Extract phonetic text
                    phonetic_text = entry.get('phonetic')
                    
                    # Extract audio URL from phonetics array
                    audio_url = None
                    phonetics = entry.get('phonetics', [])
                    
                    for phonetic in phonetics:
                        if isinstance(phonetic, dict):
                            audio = phonetic.get('audio')
                            if audio:
                                # Add https: prefix if URL starts with //
                                if audio.startswith('//'):
                                    audio_url = f"https:{audio}"
                                elif audio.startswith('http'):
                                    audio_url = audio
                                break
                            
                            # If no phonetic_text yet, try to get it from this entry
                            if not phonetic_text:
                                phonetic_text = phonetic.get('text')
                    
                    logger.info(f"Found pronunciation for '{word}': audio={bool(audio_url)}, phonetic={bool(phonetic_text)}")
                    return audio_url, phonetic_text
                    
        except aiohttp.ClientError as e:
            logger.warning(f"Network error fetching pronunciation for '{word}': {e}")
            return None, None
        except Exception as e:
            logger.error(f"Unexpected error fetching pronunciation for '{word}': {e}")
            return None, None
    
    @staticmethod
    async def update_word_pronunciation(
        db: AsyncSession, 
        word_id: str, 
        audio_url: Optional[str], 
        phonetic_text: Optional[str]
    ) -> bool:
        """
        Update a vocabulary word with pronunciation data
        
        Args:
            db: Database session
            word_id: UUID of the vocabulary word
            audio_url: Audio URL to store
            phonetic_text: Phonetic text to store
            
        Returns:
            True if update successful, False otherwise
        """
        try:
            await db.execute(
                update(VocabularyWord)
                .where(VocabularyWord.id == word_id)
                .values(
                    audio_url=audio_url,
                    phonetic_text=phonetic_text
                )
            )
            await db.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating pronunciation for word {word_id}: {e}")
            await db.rollback()
            return False
    
    @staticmethod
    async def batch_update_pronunciations(db: AsyncSession, vocabulary_list_id: str) -> int:
        """
        Update pronunciation data for all words in a vocabulary list
        
        Args:
            db: Database session
            vocabulary_list_id: UUID of the vocabulary list
            
        Returns:
            Number of words updated with pronunciation data
        """
        try:
            # Get all words in the list that don't have pronunciation data
            result = await db.execute(
                select(VocabularyWord)
                .where(
                    VocabularyWord.list_id == vocabulary_list_id,
                    VocabularyWord.audio_url.is_(None),
                    VocabularyWord.phonetic_text.is_(None)
                )
                .order_by(VocabularyWord.position)
            )
            words = result.scalars().all()
            
            updated_count = 0
            
            for word in words:
                audio_url, phonetic_text = await PronunciationService.fetch_pronunciation_data(word.word)
                
                if audio_url or phonetic_text:
                    success = await PronunciationService.update_word_pronunciation(
                        db, word.id, audio_url, phonetic_text
                    )
                    if success:
                        updated_count += 1
                        logger.info(f"Updated pronunciation for word: {word.word}")
                
                # Small delay to be respectful to the API
                import asyncio
                await asyncio.sleep(0.1)
            
            logger.info(f"Updated pronunciation for {updated_count} words in vocabulary list {vocabulary_list_id}")
            return updated_count
            
        except Exception as e:
            logger.error(f"Error in batch pronunciation update: {e}")
            return 0