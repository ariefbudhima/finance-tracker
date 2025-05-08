from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.domains.transactions.routes import router as transaction_router
from app.domains.otp.routes import router as otp_router
from app.shared.whatsapp_service import WhatsAppAPI  # Pastikan ini diimpor dengan benar
from app.domains.otp.otp_service import OTPService
from app.config.mongodb import mongodb
from app.domains.users.service import UserService
from app.config.setting import settings
import logging
import os
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s"
)

app = FastAPI()

# origins = settings.allowed_origins.split(",")

# # Allow CORS for the specified origins
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=origins,
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

print("Allowed origins:", settings.parsed_origins)


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.parsed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    # Inisialisasi WhatsAppAPI di sini untuk menghindari circular import
    api_url = settings.whatsapp_api_url
    session = settings.whatsapp_session
    ENDPOINTS = {
        "send_message": "/client/sendMessage/",
        "status_typing": "/chat/sendStateTyping/",
        "status_recording": "/chat/sendStateRecording/",
        "download_media": "/message/downloadMedia/",
    }
    whatsapp_api = WhatsAppAPI(api_url, session, ENDPOINTS)
    app.state.whatsapp_api = whatsapp_api  # Simpan objek ke state FastAPI

    # Initialize MongoDB connection
    try:
        await mongodb.init_db()
        collection = mongodb.db.transactions
        count = await collection.count_documents({})
        logging.info(f"MongoDB connected. Found {count} documents in 'transactions' collection.")
    except Exception as e:
        logging.error(f"MongoDB connection failed: {str(e)}")
        raise
        
    app.state.user_service = UserService()
    app.state.otp_service = OTPService(whatsapp_api)

@app.on_event("shutdown")
def shutdown_db():
    mongodb.close()


app.include_router(transaction_router, prefix="/api", tags=["Transaction"])
app.include_router(otp_router, prefix="/otp", tags=["OTP"])

