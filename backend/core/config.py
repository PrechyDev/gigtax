import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

# pydantic-settings reads .env into Settings' own fields but does NOT populate
# os.environ — libraries that read env vars directly (litellm/Gemini, google-auth)
# would silently see nothing without this. Load it into the real process
# environment too, once, here, so every entry point (uvicorn, pytest, scripts) gets it.
load_dotenv()

class Settings(BaseSettings):
    PROJECT_NAME: str = "GigTax"
    
    # AI Config
    CATEGORIZATION_MODEL: str = "gemini/gemini-3.5-flash"
    GEMINI_API_KEY: str | None = None

    # Database Config
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgrespassword"
    POSTGRES_DB: str = "gigtax"
    POSTGRES_PORT: str = "5432"

    # Auth
    JWT_SECRET_KEY: str = "dev-only-insecure-secret-change-me"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 10080  # 7 days

    # Google Drive BYOS
    GOOGLE_CLIENT_ID: str | None = None
    GOOGLE_CLIENT_SECRET: str | None = None
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/auth/google/callback"
    FERNET_SECRET_KEY: str | None = None

    # Frontend (for OAuth redirect-back)
    FRONTEND_URL: str = "http://localhost:5173"

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    model_config = SettingsConfigDict(env_file=".env", env_ignore_empty=True)

settings = Settings()
