import getpass
import os
import json
import logging
from bson import ObjectId
from dotenv import load_dotenv
from langchain_community.llms import OpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain.chat_models import init_chat_model
from datetime import datetime
from app.config.mongodb import mongodb

load_dotenv()

if not os.environ.get("OPENAI_API_KEY"):
  os.environ["OPENAI_API_KEY"] = getpass.getpass("Enter API key for OpenAI: ")

class OpenAIProcessor:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.llm = init_chat_model("gpt-4.1-nano", model_provider="openai")
        
        # Prompt for send_text (financial transaction parser)
        self.send_text_prompt = PromptTemplate(
            input_variables=["text"],
            template="""You are a financial transaction parser assistant.

        Your task is to extract structured information from OCR results or free-text messages about financial transactions, and return it as a valid JSON object (no explanation, no markdown, no text before or after the JSON).

        Rules:
        - Only return a valid JSON object (no explanations, no markdown)
        - If a value is missing (like date or source), infer from context or use null
        - Normalize currency into integer IDR (e.g. "Rp25.000" becomes 25000)
        - Use the field names and format below exactly
        - Assume input is in Bahasa Indonesia
        - Do NOT include the original input text in the output

        Type rules (IMPORTANT):
        - Use "type": "expense" for all spending, including transfer keluar (transfer to other people, payment, or transfer to external accounts).
        - Use "type": "income" for all incoming money, including transfer masuk (receiving money from others or external accounts).
        - Use "type": "transfer" only for transfer antar rekening milik sendiri (internal transfer between user’s own accounts).

        Expected JSON format:
        {{
        "type": "expense" | "income" | "transfer",
        "amount": 25000,
        "date": "2025-04-14",  // yyyy-mm-dd
        "time": "10:43",       // optional, hh:mm
        "category": "groceries",
        "note": "transfer to RECEPIENT NAME | groceries at Alfamart", // optional if any, fill it with something meaningful
        "source": "Alfamart",
        "full_address": "Jl. Raya No. 123, Jakarta", //contain "jalan" or "JL" or "street" or "st" or "street name" or "address" or "address name"
        "items": [
            {{
                "name": "INDOMIE KPDS76G",
                "price": 13900,
                "quantity": 1
            }},
            {{
                "name": "DLMNT BBQ 250G",
                "price": 8600,
                "quantity": 1,
                "discount": 2600
            }}
        ]
        }}

        Additional Rules:
        - If the source includes 'Alfamart', 'Indomaret', or 'supermarket', set category to 'groceries'
        - If the text includes 'transfer' or is from a bank, categorize as 'transfer' (kecuali jika transfer keluar/masuk, ikuti rules di atas)
        - If includes 'listrik', 'internet', etc., categorize as 'bills'
        - If unclear, default category to 'others'
        - If it's a transfer keluar (to other people or payment), set the note to "transfer to RECEPIENT NAME" (only recipient name) | look the text, before or after text contain "recepient" or "payment to" like SAMBARA PROV JABAR

        Example inputs you may receive:
        - Shopping receipts from Alfamart / Indomaret
        - Bank transfer proof (BCA, Mandiri, DANA, etc)
        - Manual text like: “keluar 25rb buat makan siang”
        - Abbreviations like “mkn”, “lstrk”, “byr”, etc

        ONLY RETURN the JSON object. Nothing else.

        User input:
        {text}
        """
        )
        self.send_text_chain = LLMChain(
            llm=self.llm,
            prompt=self.send_text_prompt
        )

        # Prompt for send_chat
        self.send_chat_prompt = PromptTemplate(
            input_variables=["text", "history"],
            template=(
                "You are a financial assistant.\n"
                "Answer the user's question below in a single, concise response.\n"
                "If the user does not ask any question, offer a suggestion about financial recording, such as \"My expenses this month are for monthly shopping\", etc.\n"
                "Use the same language as the user.\n"
                "Do not include any label, prefix, or explanation.\n"
                "Only return the answer.\n"
                "Do not repeat or rephrase your answer.\n"
                "\n"

                "History Chat: \n"
                "{history}\n"

                "User input:\n"
                "{text}"
            )
        )

        self.send_chat_chain = LLMChain(
                        llm=self.llm,
                        prompt=self.send_chat_prompt
                    )
        # Prompt for detect_query
        self.detect_query_prompt = PromptTemplate(
            input_variables=["user_message", "now"],
            template="""
                Today is {now}.
                You are an assistant that helps generate MongoDB queries for a finance app.

                Your task:
                - If the user's message requires retrieving or summarizing data from the database (such as questions about expenses, income, balance, or transaction history), generate a MongoDB query in JSON format.
                - If the user's message is a greeting, a general statement, or does not require any data lookup, reply with "NO_QUERY".
                - Do not ask the user for more information. Assume all necessary information is already provided.

                Database Example:
                {{
                    "_id": {{
                        "$oid": "6807d37c8f4eb69453994f61"
                    }},
                    "type": "transfer",
                    "amount": 25000,
                    "date": "2025-04-12",
                    "time": "16:16",
                    "category": "transfer",
                    "note": "transfer to Noer Syamsiah Atmah",
                    "source": "Superbank Tabungan Utama",
                    "full_address": null,
                    "items": [],
                    "phone_number": "6282218343490@c.us",
                    "image_url": "https://res.cloudinary.com/dawglh8na/image/upload/v1745343348/finance-tracker/q88uzf1jaotulcf59qh1.jpg",
                    "created_at": "2025-04-22T17:35:56.224231"
                }}

                Examples:
                User: Tampilkan pengeluaran saya bulan ini
                Query: {{"type": "expense", "date": {{"$gte": "2025-04-01", "$lte": "2025-04-30"}}}}

                User: Berapa total pemasukan minggu ini?
                Query: {{"type": "income", "date": {{"$gte": "2025-04-15", "$lte": "2025-04-21"}}}}

                User: Halo
                Query: NO_QUERY

                User: Saya ingin tahu saldo saya
                Query: {{"type": "balance"}}

                User: Terima kasih
                Query: NO_QUERY

                User: {user_message}
                Query:
            """
        )

        self.detect_query_chain = LLMChain(
            llm=self.llm,
            prompt=self.detect_query_prompt
        )

        # Prompt for answer_with_db
        self.answer_with_db_prompt = PromptTemplate(
            input_variables=["user_message", "db_result"],
            template=(
                "The user asked: \"{user_message}\"\n"
                "Database query result: {db_result}\n"
                "Please answer the user's question clearly and politely based on the data above."
            )
        )
        self.answer_with_db_chain = LLMChain(
            llm=self.llm,
            prompt=self.answer_with_db_prompt
        )

        self.resume_db = PromptTemplate(
            input_variables=["db_result"],
            template=(
                "Resume the database query result in a single, concise response.\n"
                "Database query result: {db_result}\n"
            )
        )
        self.resume_db_chain = LLMChain(
            llm=self.llm,
            prompt=self.resume_db
        )

    def send_text(self, text: str):
        result = self.send_text_chain.invoke({"text": text})
        return result["text"].strip()

    def send_chat(self, text: str, history_message: str, sender: str = None):
        result = self.send_chat_chain.invoke({"text": text, "history": history_message}
                                             )
        return result["text"].strip()

    def detect_query(self, user_message: str) -> str:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        result = self.detect_query_chain.invoke({"user_message": user_message, "now": now_str})
        return result["text"].strip()

    def answer_with_db(self, user_message: str, db_result) -> str:
        db_result_str = json.dumps(db_result, ensure_ascii=False)
        logging.info(f"db_result_str: {db_result_str}")
        result = self.answer_with_db_chain.invoke({
            "user_message": user_message,
            "db_result": db_result_str
        })
        return result["text"].strip()
    
    def answer_with_db_resume(self, db_result) -> str:
        db_result_str = json.dumps(db_result, ensure_ascii=False)
        result = self.resume_db_chain.invoke({
            "db_result": db_result_str
        })
        return result["text"].strip()
    
    async def handle_user_message(self, user_message: str, history_message: str, sender: str = None):
        query_str = self.detect_query(user_message)
        logging.info(query_str.strip().upper() == "NO_QUERY")
        if query_str.strip().upper() == "NO_QUERY":
            return self.send_chat(user_message, history_message, sender)
        else:
            try:
                # query_dict = json.loads(query_str)
                logging.info("harusnya masuk ke sini ga sih?")
                query_dict = json.loads(query_str)
                query_dict["phone_number"] = sender
                logging.info(f"Query: {query_dict}")
            except Exception as e:
                logging.error(f"Error parsing query: {str(e)}")
                # return self.send_chat(user_message, sender)
            db_result = await self.run_db_query(query_dict)
            return self.answer_with_db(user_message, db_result)
        
    async def run_db_query(self, query_dict):
        if mongodb.db is not None:
            transaction_collection = mongodb.db["transactions"]
            cursor = transaction_collection.find(query_dict)
            results = await cursor.to_list(length=100)
            results = self.convert_objectid_to_str(results)
            return results
        else:
            raise Exception("MongoDB not connected")
        
    
        
    @staticmethod
    def convert_objectid_to_str(doc):
        if isinstance(doc, list):
            return [OpenAIProcessor.convert_objectid_to_str(d) for d in doc]
        if isinstance(doc, dict):
            return {k: (str(v) if isinstance(v, ObjectId) else OpenAIProcessor.convert_objectid_to_str(v)) for k, v in doc.items()}
        return doc