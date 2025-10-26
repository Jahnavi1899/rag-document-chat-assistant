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

    # Configuration for loading environment variables
    model_config = SettingsConfigDict(
        # Look for the .env file if running locally, though Docker Compose handles this
        env_file='.env',
        # Case insensitive matching (e.g., 'database_url' matches 'DATABASE_URL')
        case_sensitive=True
    )

settings = Settings()

# Check: Print a piece of config to ensure it loaded correctly
print(f"DB User: {settings.DB_USER}") 
# You can run this file directly in the Codespace terminal to test the loading.