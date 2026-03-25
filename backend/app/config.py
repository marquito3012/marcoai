from pydantic_settings import BaseSettings, SettingsConfigDict
from urllib.parse import urlencode

class Settings(BaseSettings):
    # App Settings
    PROJECT_NAME: str = "Marco AI"
    VERSION: str = "1.0.0"
    
    # Auth & Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7 # 7 days
    
    # Google OAuth
    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str
    FRONTEND_URL: str
    
    # Groq API
    GROQ_API_KEY: str
    OPENROUTER_API_KEY: str
    GOOGLE_API_KEY: str
    
    # DB
    DATABASE_URL: str = "sqlite:///./data/marcoai.db"
    
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
