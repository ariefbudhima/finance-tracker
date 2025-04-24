from dotenv import load_dotenv
import os
import cloudinary
import cloudinary.uploader

class CloudinaryService:
    def __init__(self):
        load_dotenv()

        self.cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME")
        self.api_key = os.getenv("CLOUDINARY_API_KEY")
        self.api_secret = os.getenv("CLOUDINARY_API_SECRET")
        self.folder = os.getenv("CLOUDINARY_FOLDER")

    def upload_image(self, image_bytes, filename=None):
        result = cloudinary.uploader.upload(
            image_bytes,
            public_id=filename,  # Optional
            resource_type="image",
            folder=self.folder
        )
        return result["secure_url"]
    
