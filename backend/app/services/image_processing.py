from PIL import Image
import io
from typing import Dict, Any
import os
from pathlib import Path
from fastapi import UploadFile, HTTPException
from datetime import datetime
import secrets

class ImageProcessor:
    """Handle image processing, resizing, and thumbnail generation"""
    
    # Image constraints
    MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
    MAX_WIDTH = 2000  # pixels
    MAX_HEIGHT = 2000  # pixels
    MIN_WIDTH = 100  # pixels
    MIN_HEIGHT = 100  # pixels
    ALLOWED_FORMATS = {'JPEG', 'PNG', 'GIF', 'WEBP'}
    ALLOWED_MIME_TYPES = {'image/jpeg', 'image/png', 'image/gif', 'image/webp'}
    
    # Image version sizes
    ORIGINAL_MAX_SIZE = (2000, 2000)
    DISPLAY_MAX_SIZE = (800, 600)
    THUMBNAIL_MAX_SIZE = (200, 150)
    
    UPLOAD_DIR = Path("uploads")
    
    def __init__(self):
        self.UPLOAD_DIR.mkdir(exist_ok=True)
    
    async def validate_and_process_image(
        self, 
        file: UploadFile, 
        assignment_id: str, 
        image_number: int
    ) -> Dict[str, Any]:
        """Validate and process uploaded image, creating three versions."""
        # Validate file size
        if file.size > self.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400, 
                detail=f"Image must be smaller than 5MB (current: {(file.size / 1024 / 1024):.1f}MB)"
            )
        
        # Validate content type
        if file.content_type not in self.ALLOWED_MIME_TYPES:
            raise HTTPException(
                status_code=400, 
                detail="Please upload JPEG, PNG, GIF, or WebP images"
            )
        
        # Read file content
        content = await file.read()
        
        # Open image
        try:
            image = Image.open(io.BytesIO(content))
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid image file")
        
        # Check format
        if image.format not in self.ALLOWED_FORMATS:
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported format. Use: {', '.join(self.ALLOWED_FORMATS)}"
            )
        
        # Check dimensions
        width, height = image.size
        if width < self.MIN_WIDTH or height < self.MIN_HEIGHT:
            raise HTTPException(
                status_code=400, 
                detail=f"Image must be at least {self.MIN_WIDTH}x{self.MIN_HEIGHT} pixels"
            )
        
        # Convert to RGB if necessary (for PNG with transparency)
        if image.mode in ('RGBA', 'LA', 'P'):
            rgb_image = Image.new('RGB', image.size, (255, 255, 255))
            if image.mode == 'P':
                image = image.convert('RGBA')
            rgb_image.paste(image, mask=image.split()[-1] if image.mode in ('RGBA', 'LA') else None)
            image = rgb_image
        
        # Generate image tag and base filename
        image_tag = f"image-{image_number}"
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        base_key = f"{assignment_id}_{image_tag}_{timestamp}"
        format_ext = 'jpg'  # Always save as JPEG for consistency
        
        # Create assignment directory
        assignment_dir = self.UPLOAD_DIR / "assignments" / assignment_id
        assignment_dir.mkdir(parents=True, exist_ok=True)
        
        # Create three versions
        # 1. Original (max 2000x2000)
        original = image.copy()
        if original.width > self.ORIGINAL_MAX_SIZE[0] or original.height > self.ORIGINAL_MAX_SIZE[1]:
            original.thumbnail(self.ORIGINAL_MAX_SIZE, Image.Resampling.LANCZOS)
        
        original_filename = f"{base_key}_original.{format_ext}"
        original_path = assignment_dir / original_filename
        original.save(original_path, 'JPEG', quality=90, optimize=True)
        
        # 2. Display version (max 800x600)
        display = image.copy()
        display.thumbnail(self.DISPLAY_MAX_SIZE, Image.Resampling.LANCZOS)
        
        display_filename = f"{base_key}_display.{format_ext}"
        display_path = assignment_dir / display_filename
        display.save(display_path, 'JPEG', quality=85, optimize=True)
        
        # 3. Thumbnail (max 200x150)
        thumbnail = image.copy()
        thumbnail.thumbnail(self.THUMBNAIL_MAX_SIZE, Image.Resampling.LANCZOS)
        
        thumb_filename = f"{base_key}_thumb.{format_ext}"
        thumb_path = assignment_dir / thumb_filename
        thumbnail.save(thumb_path, 'JPEG', quality=80, optimize=True)
        
        return {
            "image_tag": image_tag,
            "image_key": base_key,  # Keep for backward compatibility
            "original_url": f"/uploads/assignments/{assignment_id}/{original_filename}",
            "display_url": f"/uploads/assignments/{assignment_id}/{display_filename}",
            "image_url": f"/uploads/assignments/{assignment_id}/{display_filename}",  # Alias for backward compatibility
            "thumbnail_url": f"/uploads/assignments/{assignment_id}/{thumb_filename}",
            "width": width,
            "height": height,
            "file_size": file.size,
            "mime_type": file.content_type,
            "file_name": file.filename
        }
    
    @staticmethod
    def cleanup_assignment_images(assignment_id: str):
        """Remove all images for an assignment"""
        upload_dir = Path("uploads/assignments") / assignment_id
        if upload_dir.exists():
            import shutil
            shutil.rmtree(upload_dir)