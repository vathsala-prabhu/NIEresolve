import os
from typing import List
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "NIEresolve"
    TAGLINE: str = "Every Concern Deserves a Response."
    INSTITUTION: str = "The National Institute of Engineering (NIE), Mysuru"
    APP_ENV: str = "development"
    DEBUG: bool = True
    PORT: int = 8000
    HOST: str = "127.0.0.1"
    CORS_ORIGINS: List[str] = ["http://localhost:8000", "http://127.0.0.1:8000"]
    
    # Security
    SECRET_KEY: str = "nieresolve-secure-institutional-jwt-key-mysuru-2026-secret"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 720
    
    # Database
    DATABASE_URL: str = "sqlite:///./nieresolve.db"
    
    # Storage
    UPLOAD_DIR: str = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
    MAX_UPLOAD_SIZE_MB: int = 10
    
    # Escalation
    TIER1_ESCALATION_DAYS: int = 15
    TIER2_ESCALATION_DAYS: int = 15
    
    # ML & Duplicate Detection
    DUPLICATE_SIMILARITY_THRESHOLD: float = 0.40
    MODEL_STORAGE_PATH: str = os.path.join(os.path.dirname(__file__), "ml", "data", "priority_model.joblib")
    VECTORIZER_STORAGE_PATH: str = os.path.join(os.path.dirname(__file__), "ml", "data", "tfidf_vectorizer.joblib")
    
    # Chatbot
    LLM_PROVIDER: str = "institutional_rag"
    OPENAI_API_KEY: str = ""
    GEMINI_API_KEY: str = ""

    class Config:
        env_file = ".env"
        extra = "allow"

settings = Settings()

