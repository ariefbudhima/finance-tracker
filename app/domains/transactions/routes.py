from fastapi import APIRouter, Request, Depends, HTTPException
import logging
from app.domains.transactions.services import TransactionService
from app.shared.whatsapp_service import WhatsAppAPI
from app.domains.transactions.llm_service import OpenAIProcessor
from app.domains.users.service import UserService

logger = logging.getLogger(__name__)

router = APIRouter()
service = TransactionService()

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
                logger.info("lempar ke llm service, handle user message")
                message = await service.handle_text_message(user_message, sender)
                # Upsert user stats untuk pesan teks
                logger.info("upsert user stats")
                await user_service.upsert_user_stats(sender, last_message=user_message)
                logger.info("upsert user stats done")

            whatsapp_api.send_text_message(
                recipient=sender,
                body=message
            )
            return {"Status": "ok"}
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")