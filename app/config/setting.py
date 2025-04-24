from pydantic import BaseSettings

class Settings(BaseSettings):
    app_name: str = "Finance Tracker"
    environment: str = "development"
    openai_api_key: str
    ocr_lang: str = "en"

    class Config:
        env_file = ".env"

settings = Settings()
