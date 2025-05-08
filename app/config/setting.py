from pydantic_settings import BaseSettings
import os

class Settings(BaseSettings):
    app_name: str
    environment: str
    openai_api_key: str
    ocr_lang: str
    frontend_base_url: str
    whatsapp_api_url: str
    whatsapp_session: str
    allowed_origins: str
    
    @property
    def parsed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",")]
        
    # Cloudinary settings
    cloudinary_cloud_name: str
    cloudinary_api_key: str
    cloudinary_api_secret: str
    cloudinary_folder: str
    
    # MongoDB settings
    mongo_db_name: str
    mongo_uri: str
    
    # Azure OCR settings
    azure_ocr_endpoint: str
    azure_ocr_key: str

    class Config:
        env_file = "../../.env"
        case_sensitive = False

settings = Settings()
print("Loaded from .env →", os.getenv("MONGO_DB_NAME"))       # Langsung dari os
print("Loaded from settings →", settings.mongo_db_name)       # Dari Pydantic

