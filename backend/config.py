import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

class Settings:
    PROJECT_NAME: str = "Offline GPT — Kid-Safe Educational AI Platform"
    VERSION: str = "1.1.0"
    
    # Educational & Kid-Safety Locks
    KIDS_EDUCATIONAL_MODE: bool = os.getenv("KIDS_EDUCATIONAL_MODE", "true").lower() == "true"
    SERVER_SIDE_KB_ONLY: bool = os.getenv("SERVER_SIDE_KB_ONLY", "true").lower() == "true"
    PROFANITY_SAFETY_FILTER: bool = os.getenv("PROFANITY_SAFETY_FILTER", "true").lower() == "true"
    
    # AI Engine Mode
    LLM_MODE: str = os.getenv("LLM_MODE", "auto").lower()
    
    # API Keys
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "").strip()
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "").strip()
    HF_API_KEY: str = os.getenv("HF_API_KEY", "").strip()
    
    # Local Ollama Engine
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").strip()
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3.2").strip()
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR}/database/app.db")
    
    # Auth & JWT
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "offline_gpt_secret_key_2026")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))
    
    # Security Rate Limiting
    RATE_LIMIT_PROMPTS: int = int(os.getenv("RATE_LIMIT_PROMPTS", "10"))
    RATE_LIMIT_WINDOW_SECONDS: int = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "300"))
    
    # RAG Settings
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "500"))
    CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "50"))
    MAX_SEARCH_RESULTS: int = int(os.getenv("MAX_SEARCH_RESULTS", "4"))
    
    # Paths
    DATABASE_DIR = BASE_DIR / "database"
    UPLOADS_DIR = BASE_DIR / "uploads"
    EDUCATIONAL_KB_DIR = BASE_DIR / "educational_kb"
    VECTOR_STORE_DIR = BASE_DIR / "vector_store"
    FRONTEND_DIR = BASE_DIR / "frontend"

settings = Settings()

# Ensure directories exist
settings.DATABASE_DIR.mkdir(parents=True, exist_ok=True)
settings.UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
settings.EDUCATIONAL_KB_DIR.mkdir(parents=True, exist_ok=True)
settings.VECTOR_STORE_DIR.mkdir(parents=True, exist_ok=True)
