import datetime
from app.config.mongodb import mongodb

class UserService:
    def __init__(self):
        if mongodb.db is None:
            raise Exception("MongoDB belum diinisialisasi!")
        self.users = mongodb.db["users"]

    async def upsert_user_stats(
        self,
        phone_number: str,
        last_message: str = None,
        last_transaction_date: str = None,
        increment_message: bool = True,
        increment_transaction: bool = False,
        notes: str = None
    ):
        now = datetime.datetime.utcnow()
        update = {
            "$setOnInsert": {"first_seen": now},
            "$set": {"last_active": now}
        }
        if last_message:
            update["$set"]["last_message"] = last_message
        if last_transaction_date:
            update["$set"]["last_transaction_date"] = last_transaction_date
        if notes:
            update["$set"]["notes"] = notes

        # Gabungkan $inc jika dua-duanya aktif
        inc_dict = {}
        if increment_message:
            inc_dict["total_messages"] = 1
        if increment_transaction:
            inc_dict["total_transactions"] = 1
        if inc_dict:
            update["$inc"] = inc_dict

        await self.users.update_one(
            {"phone_number": phone_number},
            update,
            upsert=True
        )