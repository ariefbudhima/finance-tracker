from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from app.config.setting import settings
import logging
import os

load_dotenv()

class MongoDB:
    def __init__(self, uri: str, db_name: str):
        self.uri = uri
        self.client = None
        self.db = None
        self.db_name = db_name

    async def init_db(self):
        # Create connection to MongoDB using the connection string
        self.client = AsyncIOMotorClient(self.uri)
        # Extracting database name from URI and sanitize it
        db_name = self.db_name
        self.db = self.client[db_name]

        logging.info(db_name)
        logging.info(self.uri)
        
    def get_db(self):
        return self.db

    def close(self):
        self.client.close()

# Inisialisasi MongoDB dengan connection string
mongodb = MongoDB(uri=settings.mongo_uri, db_name=settings.mongo_db_name)
