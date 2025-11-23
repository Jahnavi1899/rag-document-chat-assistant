from pydantic_settings import BaseSettings, SettingsConfigDict

# Pydantic will automatically load environment variables 
# matching these names.
# Note: Since we are running in Docker Compose, the env vars 
# are injected from the docker-compose.yml, which in turn 
# reads them from the .env file.

class Settings(BaseSettings):
    # Database Settings
    DATABASE_URL: str
    DB_USER: str
    DB_PASSWORD: str
    DB_NAME: str

    # Redis Settings (for caching and Celery broker/backend)
    REDIS_HOST: str
    REDIS_PORT: int = 6379 # Default Redis port
    CELERY_BROKER_URL: str
    CELERY_RESULT_BACKEND: str

    # LLM and RAG Settings
    OPENAI_API_KEY: str

    # AWS Settings
    S3_BUCKET: str
    CHROMA_PATH: str
    AWS_REGION: str 

    # Configuration for loading environment variables
    model_config = SettingsConfigDict(
        # Look for the .env file if running locally, though Docker Compose handles this
        env_file='.env',
        case_sensitive=True
    )

    def validate_settings(self):
        """Validate critical settings are present"""
        if not self.OPENAI_API_KEY.startswith('sk-'):
            raise ValueError("Invalid OPENAI_API_KEY format")
        return True

settings = Settings()

try:
    settings.validate_settings()
    print(f"✓ Configuration loaded successfully")
    print(f"  - Database: {settings.DB_NAME}")
    print(f"  - Redis: {settings.REDIS_HOST}:{settings.REDIS_PORT}")
    print(f"  - S3 Bucket: {settings.S3_BUCKET}")
except Exception as e:
    print(f"✗ Configuration error: {e}")
    raise