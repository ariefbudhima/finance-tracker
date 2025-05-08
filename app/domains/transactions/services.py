import logging
import datetime
import json
import base64
from typing import Optional
from app.config.mongodb import mongodb
from app.domains.transactions.llm_service import OpenAIProcessor
from app.shared.cloudinary_service import CloudinaryService
from app.domains.transactions.ocr_service import OCRProcessor


class TransactionService:
    def __init__(self):
        self.openai = OpenAIProcessor()
        self.ocr = OCRProcessor()
        self.uploader = CloudinaryService()

    async def handle_image(self, image_base64, phone_number: str):
        try:
            # OCR processing
            logging.info(f"Processing image for phone number: {phone_number}")
            try:
                image_bytes = base64.b64decode(image_base64)
                text_result = self.ocr.azure_ocr(image_bytes)
            except Exception as e:
                logging.error(f"Error during OCR processing: {str(e)}")
                return {"OCR processing failed"}
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
                    # upload to cloudinary when not exists
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
        
        history = await self.get_last_message(sender, 5)
        history = list(reversed(history))

        history_message = "\n".join(
            f"{'User' if msg['role'] == 'user' else 'Bot'}: {msg['message']}"
            for msg in history
        )

        # Hasil dari OpenAI
        result = await self.openai.handle_user_message(message, history_message, sender)

        # Simpan sebagai balasan
        await self.save_message(sender, "bot", result)

        try:
            # Coba parse hasil jika itu string JSON (bisa diatur dari handle_user_message)
            if isinstance(result, str):
                parsed = json.loads(result)
            elif isinstance(result, dict):
                parsed = result
            else:
                parsed = None

            if parsed and all(k in parsed for k in ["date", "time", "amount", "type", "category"]):
                parsed["phone_number"] = sender
                parsed["created_at"] = datetime.datetime.utcnow().isoformat()

                if mongodb.db is not None:
                    transaction_collection = mongodb.db["transactions"]

                    # Cek apakah transaksi sudah ada
                    query = {
                        "date": parsed.get("date"),
                        "time": parsed.get("time"),
                        "amount": parsed.get("amount")
                    }
                    existing = await transaction_collection.find_one(query)

                    if existing:
                        logging.info(f"Transaction already exists: {existing['_id']}")
                    else:
                        insert_result = await transaction_collection.insert_one(parsed)
                        logging.info(f"Inserted transaction with ID: {insert_result.inserted_id}")
            else:
                logging.info("Result from OpenAI is not a transaction, skipping DB insert.")
        
        except Exception as e:
            logging.error(f"Error processing text transaction: {str(e)}")

        return result

    
    async def get_transactions(self, phone_number: str, month: Optional[int] = None, year: Optional[int] = None):
        if mongodb.db is None:
            raise Exception("MongoDB not connected")

        transaction_collection = mongodb.db["transactions"]
        query = {"phone_number": phone_number}

        # Tambahkan filter tanggal jika month dan year diberikan
        if month and year:
            # Buat rentang tanggal dari awal hingga akhir bulan
            start_date = datetime.datetime(year, month, 1)
            # Tangani pergantian bulan dan tahun
            if month == 12:
                end_date = datetime.datetime(year + 1, 1, 1)
            else:
                end_date = datetime.datetime(year, month + 1, 1)
            # Sesuaikan field "date" di database (asumsinya format ISO string seperti "2025-04-12")
            query["date"] = {
                "$gte": start_date.strftime("%Y-%m-%d"),
                "$lt": end_date.strftime("%Y-%m-%d"),
            }

        cursor = transaction_collection.find(query)
        results = await cursor.to_list(length=None)
        results = self.openai.convert_objectid_to_str(results)
        return results
    
    async def get_summary_stats(self, phone_number: str, month: Optional[int] = None, year: Optional[int] = None):
        if mongodb.db is None:
            raise Exception("MongoDB not connected")

        collection = mongodb.db["transactions"]
        match_stage = {"phone_number": phone_number}

        # Add date filtering if month and year are provided
        if month and year:
            start_date = datetime.datetime(year, month, 1)
            if month == 12:
                end_date = datetime.datetime(year + 1, 1, 1)
            else:
                end_date = datetime.datetime(year, month + 1, 1)
            
            match_stage["date"] = {
                "$gte": start_date.strftime("%Y-%m-%d"),
                "$lt": end_date.strftime("%Y-%m-%d")
            }

        pipeline = [
            {"$match": match_stage},
            {"$group": {
                "_id": "$type",
                "total": {"$sum": "$amount"}
            }}
        ]
        result = await collection.aggregate(pipeline).to_list(None)
        summary = {item["_id"]: item["total"] for item in result}
        return summary

    async def get_daily_stats(self, phone_number: str, month: int, year: int):
        if mongodb.db is None:
            raise Exception("MongoDB not connected")

        collection = mongodb.db["transactions"]

        # Tentukan range tanggal awal dan akhir bulan
        start_date = datetime.datetime(year, month, 1)
        if month == 12:
            end_date = datetime.datetime(year + 1, 1, 1)
        else:
            end_date = datetime.datetime(year, month + 1, 1)

        # Ubah tanggal ke format string sesuai format data di MongoDB (yyyy-mm-dd)
        start_date_str = start_date.strftime('%Y-%m-%d')
        end_date_str = end_date.strftime('%Y-%m-%d')

        pipeline = [
            {
                "$match": {
                    "phone_number": phone_number,
                    "date": {"$gte": start_date_str, "$lt": end_date_str}
                }
            },
            {
                "$group": {
                    "_id": "$date",
                    "total": {"$sum": "$amount"},
                    "transaction_count": {"$sum": 1},
                    "transactions": {
                        "$push": {
                            "_id": {"$toString": "$_id"},
                            "amount": "$amount",
                            "type": "$type",
                            "category": "$category",
                            "time": "$time",
                            "description": "$note",
                            "image_url": "$image_url"
                        }
                    },
                }
            },
            {
                "$addFields": {
                    "date": "$_id"
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "date": 1,
                    "total": 1,
                    "transaction_count": 1,
                    "transactions": 1,
                    "income": 1,
                    "expense": 1
                }
            },
            {
                "$sort": {"date": 1}
            }
        ]


        result = await collection.aggregate(pipeline).to_list(None)
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
    
    # async def get_monthly_summary(self, phone_number: str, month: int, year: int):
    #     if mongodb.db is None:
    #         raise Exception("MongoDB not connected")

    #     collection = mongodb.db["transactions"]

    #     # Set date range for the month
    #     start_date = datetime.datetime(year, month, 1)
    #     if month == 12:
    #         end_date = datetime.datetime(year + 1, 1, 1)
    #     else:
    #         end_date = datetime.datetime(year, month + 1, 1)

    #     start_date_str = start_date.strftime('%Y-%m-%d')
    #     end_date_str = end_date.strftime('%Y-%m-%d')

    #     pipeline = [
    #         {
    #             "$match": {
    #                 "phone_number": phone_number,
    #                 "date": {"$gte": start_date_str, "$lt": end_date_str}
    #             }
    #         },
    #         {
    #             "$group": {
    #                 "_id": None,
    #                 "total_transactions": {"$sum": 1},
    #                 "total_amount": {"$sum": "$amount"},
    #                 "income": {
    #                     "$sum": {"$cond": [{"$eq": ["$type", "income"]}, "$amount", 0]}
    #                 },
    #                 "expense": {
    #                     "$sum": {"$cond": [{"$eq": ["$type", "expense"]}, "$amount", 0]}
    #                 },
    #                 "categories": {
    #                     "$push": {
    #                         "category": "$category",
    #                         "amount": "$amount",
    #                         "type": "$type"
    #                     }
    #                 },
    #                 "transactions": {
    #                     "$push": {
    #                         "_id": {"$toString": "$_id"},
    #                         "date": "$date",
    #                         "amount": "$amount",
    #                         "type": "$type",
    #                         "category": "$category",
    #                         "description": "$description"
    #                     }
    #                 }
    #             }
    #         },
    #         {
    #             "$addFields": {
    #                 "net_income": {"$subtract": ["$income", "$expense"]},
    #                 "category_summary": {
    #                     "$reduce": {
    #                         "input": "$categories",
    #                         "initialValue": [],
    #                         "in": {
    #                             "$cond": [
    #                                 {"$in": ["$$this.category", "$$value.category"]},
    #                                 "$$value",
    #                                 {"$concatArrays": ["$$value", [{
    #                                     "category": "$$this.category",
    #                                     "total": {"$sum": ["$$this.amount"]},
    #                                     "count": 1,
    #                                     "type": "$$this.type"
    #                                 }]]}
    #                             ]
    #                         }
    #                     }
    #                 }
    #             }
    #         },
    #         {
    #             "$project": {
    #                 "_id": 0,
    #                 "total_transactions": 1,
    #                 "total_amount": 1,
    #                 "income": 1,
    #                 "expense": 1,
    #                 "net_income": 1,
    #                 "category_summary": 1,
    #                 "transactions": 1
    #             }
    #         }
    #     ]
    #     logging.info(f"Pipeline: {pipeline}")

    #     result = await collection.aggregate(pipeline).to_list(None)
    #     return result[0] if result else None

    async def get_category_stats(self, phone_number: str, month: int, year: int):
        if mongodb.db is None:
            raise Exception("MongoDB not connected")

        collection = mongodb.db["transactions"]

        # Tentukan range tanggal awal dan akhir bulan
        start_date = datetime.datetime(year, month, 1)
        if month == 12:
            end_date = datetime.datetime(year + 1, 1, 1)
        else:
            end_date = datetime.datetime(year, month + 1, 1)

        # Ubah tanggal ke format string sesuai format data di MongoDB (yyyy-mm-dd)
        start_date_str = start_date.strftime('%Y-%m-%d')
        end_date_str = end_date.strftime('%Y-%m-%d')

        logging.info("===============this is get category stats===============")
        logging.info(f"Start Date: {start_date_str}, End Date: {end_date_str}")
        
        pipeline = [
            {
                "$match": {
                    "phone_number": phone_number,
                    "date": {"$gte": start_date_str, "$lt": end_date_str}
                }
            },
            {
                "$group": {
                    "_id": "$category",
                    "type": {"$first": "$type"},
                    "total": {"$sum": "$amount"}
                }
            },
            {
                "$sort": {"total": -1}
            }
        ]

        logging.info(f"Pipeline: {pipeline}")
        result = await collection.aggregate(pipeline).to_list(None)
        return result
