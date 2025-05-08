from fastapi import APIRouter, Request, Depends, HTTPException, Query
import logging
from typing import Optional
from app.domains.transactions.services import TransactionService
from app.shared.whatsapp_service import WhatsAppAPI
from app.domains.transactions.llm_service import OpenAIProcessor
from app.domains.users.service import UserService
from app.domains.auth.middleware import JWTAuthMiddleware
from app.config.setting import settings

logger = logging.getLogger(__name__)

router = APIRouter()
service = TransactionService()
jwt_auth = JWTAuthMiddleware()

def get_user_service(request: Request) -> UserService:
    return request.app.state.user_service

# Dependency to get whatsapp_api from app.state
def get_whatsapp_api(request: Request) -> WhatsAppAPI:
    return request.app.state.whatsapp_api

@router.post("/webhook", response_model=None)
async def webhook(
    request: Request,
    whatsapp_api: WhatsAppAPI = Depends(get_whatsapp_api),
    user_service: UserService = Depends(get_user_service)
):
    try:
        data = await request.json()
        data_type = data.get("dataType", "Unknown")
        logger.info(f"Webhook received data type: {data_type}")
        if data_type == "message":
            sender = service.get_sender(data)
            if not service.is_personal_chat(sender):
                return {"Status": "ignored"}  # Ignore messages from group chats

            mimetype = service.get_mimetype(data)
            logger.info(f"Sender: {sender}, Mimetype: {mimetype}")

            if mimetype and "image/jpeg" in mimetype:
                message_id = data.get("data", {}).get("message", {}).get("_data", {}).get("id", {}).get("id")
                content_base64 = whatsapp_api.download_media(sender, message_id, return_as_base64=True)
                message = await service.handle_image(content_base64, sender)
                # Upsert user stats untuk pesan gambar
                await user_service.upsert_user_stats(sender, last_message="[image]")
            else:
                user_message = data.get("data", {}).get("message", {}).get("_data", {}).get("body")
                if not user_message:
                    logger.warning("No user message found in payload.")
                    return {"Status": "no_message"}
                
                # Check if user is requesting dashboard access
                if user_message.lower().strip() in ["dashboard", "view dashboard", "show dashboard"]:
                    logger.info("===============================")
                    logger.info("User requested dashboard access")
                    # Generate JWT token for the sender
                    access_token = jwt_auth.jwt_service.create_access_token(sender)
                    # Construct dashboard URL with token
                    dashboard_url = f"{settings.frontend_base_url}/dashboard?token={access_token}"
                    message = f"Here's your secure dashboard link (valid for 24 hours):\n{dashboard_url}"
                else:
                    # Handle regular text messages
                    logger.info("Processing user message with LLM service")
                    message = await service.handle_text_message(user_message, sender)
                    # Upsert user stats for text messages
                    logger.info("Updating user stats")
                    await user_service.upsert_user_stats(sender, last_message=user_message)
                    logger.info("User stats updated successfully")

            whatsapp_api.send_text_message(
                recipient=sender,
                body=message
            )
            return {"Status": "ok"}
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
    
@router.get("/transactions")
async def get_transactions(
    phone_number: str,
    month: Optional[int] = None,
    year: Optional[int] = None,
    authorized_phone: str = Depends(jwt_auth)
):
    try:
        transactions = await service.get_transactions(phone_number, month=month, year=year)
        return {"transactions": transactions}
    except Exception as e:
        logger.error(f"Error fetching transactions: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.get("/stats/summary")
async def get_summary_stats(
    phone_number: str,
    month: Optional[int] = None,
    year: Optional[int] = None,
    authorized_phone: str = Depends(jwt_auth)
):
    try:
        summary = await service.get_summary_stats(phone_number, month, year)
        return {"summary": summary}
    except Exception as e:
        logger.error(f"Error fetching summary stats: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
    
@router.get("/stats/daily")
async def get_daily_stats(
    phone_number: str,
    month: int,
    year: int,
    authorized_phone: str = Depends(jwt_auth)
):
    try:
        stats = await service.get_daily_stats(phone_number, month, year)
        return {"daily_stats": stats}
    except Exception as e:
        logger.error(f"Error fetching daily stats: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.get("/stats/category")
async def get_category_stats(
    phone_number: str,
    month: int,
    year: int,
    authorized_phone: str = Depends(jwt_auth)
):
    try:
        stats = await service.get_category_stats(phone_number, month, year)
        return {"category_stats": stats}
    except Exception as e:
        logger.error(f"Error fetching category stats: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

# @router.get("/stats/monthly_summary")
# async def get_monthly_stats(
#     phone_number: str,
#     month: int,
#     year: int,
#     authorized_phone: str = Depends(jwt_auth)
# ):
#     logger.info(f"Fetching monthly stats for phone_number: {phone_number}, month: {month}, year: {year}")
#     try:
#         stats = await service.get_monthly_summary(phone_number, month, year)
#         return {"monthly_stats": stats}
#     except Exception as e:
#         logger.error(f"Error fetching monthly stats: {e}")
#         raise HTTPException(status_code=500, detail="Internal Server Error")
