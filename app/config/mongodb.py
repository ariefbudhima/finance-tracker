from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import os

load_dotenv()

class MongoDB:
    def __init__(self, uri: str):
        self.uri = uri
        self.client = None
        self.db = None

    async def init_db(self):
        # Create connection to MongoDB using the connection string
        self.client = AsyncIOMotorClient(self.uri)
        # Extracting database name from URI
        db_name = os.getenv("MONGO_DB_NAME")
        self.db = self.client[db_name]

    def get_db(self):
        return self.db

    def close(self):
        self.client.close()

# Inisialisasi MongoDB dengan connection string
mongodb = MongoDB(uri=os.getenv("MONGO_URI"))
