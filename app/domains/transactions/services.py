import logging
import datetime
import json
import base64
from app.config.mongodb import mongodb
from app.domains.transactions.llm_service import OpenAIProcessor
from app.shared.cloudinary_service import CloudinaryService
from app.domains.transactions.ocr_service import OCRProcessor


class TransactionService:
    def __init__(self):
        self.openai = OpenAIProcessor()
        self.ocr = OCRProcessor(easyocr_langs=['en', 'id'])
        self.uploader = CloudinaryService()

    async def handle_image(self, image_base64, phone_number: str):
        try:
            # OCR processing
            logging.info(f"Processing image for phone number: {phone_number}")
            try:
                image_bytes = base64.b64decode(image_base64)
                text_result = self.ocr.easyocr_cleaned_lines(image_bytes)
            except Exception as e:
                logging.error(f"Error during OCR processing: {str(e)}")
                return {"error": "OCR processing failed"}
            logging.info(f"OCR Result: {text_result}")

            # Send to OpenAI
            result = self.openai.send_text(text_result)
            if isinstance(result, str):
                result = json.loads(result)

            result['phone_number'] = phone_number
            result['created_at'] = datetime.datetime.utcnow().isoformat()

            await self.save_message(phone_number, "user", result)

            # Save to MongoDB
            if mongodb.db is not None:
                transaction_collection = mongodb.db["transactions"]

                # Cek apakah record sudah ada
                query = {
                    "date": result.get("date"),
                    "time": result.get("time"),
                    "amount": result.get("amount")
                }
                existing = await transaction_collection.find_one(query)

                if existing:
                    logging.info(f"Transaction already exists: {existing['_id']}")
                    existing['_id'] = str(existing['_id'])
                    result = "Transaction already exists"
                    await self.save_message(phone_number, "bot", result)
                    return result
                else:
                    # Baru upload ke Cloudinary jika transaksi belum ada
                    image_data = "data:image/jpeg;base64," + image_base64
                    image_url = self.uploader.upload_image(image_data)
                    result['image_url'] = image_url

                    insert_result = await transaction_collection.insert_one(result)
                    logging.info(f"Inserted transaction with ID: {insert_result.inserted_id}")
                    result['_id'] = str(insert_result.inserted_id)
            else:
                raise Exception("MongoDB not connected")

            # Jawab ke user
            answer = self.openai.answer_with_db_resume(text_result)
            await self.save_message(phone_number, "bot", answer)
            return answer

        except Exception as e:
            logging.error(f"Error processing image: {str(e)}")
            return {"error": "Failed to process image"}

    def is_personal_chat(self, sender: str):
        # Implement your logic to check if the chat is personal
        return "g.us" not in sender

    def get_sender(self, data):
        return data.get("data", {}).get("message", {}).get("_data", {}).get("from", "Unknown sender")

    def get_mimetype(self, data):
        return data.get("data", {}).get("message", {}).get("_data", {}).get("mimetype")
    
    async def handle_text_message(self, message, sender):
        # save the message to the database
        await self.save_message(sender, "user", message)
        logging.info(f"Sender: {sender}, Message: {message}")
        history = await self.get_last_message(sender, 5)
        logging.info(f"History: {history}")
        history = list(reversed(history))
        history_message = "\n".join(
            f"{'User' if msg['role'] == 'user' else 'Bot'}: {msg['message']}"
            for msg in history
)
        result = await self.openai.handle_user_message(message, history_message, sender)

        await self.save_message(sender, "bot", result)
        return result
    
    @staticmethod
    async def save_message(phone_number, role, message):
        # Implement your logic to save the message to the database
        logging.info(mongodb.db is not None)
        if mongodb.db is not None:
            transaction_collection = mongodb.db["chats"]
            insert_result = await transaction_collection.insert_one({
                "phone_number": phone_number,
                "role": role,  # "user" atau "bot"
                "message": message,
                "timestamp": datetime.datetime.utcnow()
            })
            logging.info(f"Inserted message with ID: {insert_result.inserted_id}")
            return str(insert_result.inserted_id)
        else:
            raise Exception("MongoDB not connected")
        
    async def get_last_message(self, phone_number: str, limit: int = 5):
        if mongodb.db is not None:
            transaction_collection = mongodb.db["chats"]
            cursor = transaction_collection.find({"phone_number": phone_number}).sort("timestamp", -1).limit(limit)
            results = await cursor.to_list(length=limit)
            results = self.openai.convert_objectid_to_str(results)
            return results
        else:
            raise Exception("MongoDB not connected")