from pydantic import BaseModel
from typing import Optional, List
from enum import Enum

class ImageType(str, Enum):
    QUANTITATIVE = "Quantitative"
    DIAGRAM = "Diagram"
    PHOTOGRAPH = "Photograph"
    ILLUSTRATION = "Illustration"

class ExtractedData(BaseModel):
    axis_labels: Optional[dict] = None
    data_points: Optional[List[dict]] = None
    values: Optional[List[str]] = None
    labels: Optional[List[str]] = None
    
class ImageAnalysis(BaseModel):
    image_type: ImageType
    data_extracted: Optional[ExtractedData] = None
    description: str
    key_learning_points: List[str]
    potential_misconceptions: List[str]