from pydantic_settings import BaseSettings
from typing import Optional
import secrets

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379"
    
    # Security
    SECRET_KEY: str = secrets.token_urlsafe(32)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15  # Default to 15 minutes
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7  # Default to 7 days
    
    # Email
    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 1025
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    EMAIL_FROM: str = "noreply@umadex.local"
    
    # OTP
    OTP_EXPIRY_MINUTES: int = 10
    OTP_LENGTH: int = 6
    
    # Frontend
    FRONTEND_URL: str = "http://localhost:3000"
    
    # Environment
    ENVIRONMENT: str = "development"
    
    # AI/ML
    GEMINI_API_KEY: Optional[str] = None
    
    # Backend URL for internal requests
    BACKEND_URL: str = "http://localhost:8000"
    
    class Config:
        env_file = ".env"
        case_sensitive = True
    
    @property
    def computed_access_token_expire_minutes(self) -> int:
        """Get access token expiration based on environment"""
        if self.ENVIRONMENT == "development":
            return 15  # 15 minutes for development
        return 60  # 1 hour for production
    
    @property
    def computed_refresh_token_expire_days(self) -> int:
        """Get refresh token expiration based on environment"""
        if self.ENVIRONMENT == "development":
            return 7  # 7 days for development
        return 30  # 30 days for production

settings = Settings()