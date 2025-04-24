import random
import time
from app.shared.whatsapp_service import WhatsAppAPI

class OTPService:
    def __init__(self, whatsapp_service: WhatsAppAPI, expiry_seconds: int = 300):
        """
        Initialize OTP Service.

        Args:
            whatsapp_service (WhatsAppService): An instance of WhatsAppService to send messages.
            expiry_seconds (int): OTP validity duration in seconds. Default is 5 minutes.
        """
        self.whatsapp_service = whatsapp_service
        self.otp_storage = {}  # key: phone_number, value: (otp, expiry_time)
        self.expiry_seconds = expiry_seconds

    def generate_otp(self, phone_number: str) -> str:
        """
        Generate a 6-digit OTP and store it with an expiry time.

        Args:
            phone_number (str): The user's phone number to bind the OTP.

        Returns:
            str: The generated OTP.
        """
        otp = str(random.randint(100000, 999999))
        expiry_time = time.time() + self.expiry_seconds
        self.otp_storage[phone_number] = (otp, expiry_time)
        return otp

    def send_otp(self, phone_number: str) -> dict:
        """
        Generate and send OTP via WhatsApp.

        Args:
            phone_number (str): The user's phone number.

        Returns:
            dict: Response from WhatsApp API.
        """
        otp = self.generate_otp(phone_number)
        message = f"Your OTP code is: *{otp}*\nIt is valid for {self.expiry_seconds // 60} minutes."
        return self.whatsapp_service.send_text_message(phone_number, message)

    def verify_otp(self, phone_number: str, otp_input: str) -> bool:
        """
        Verify the provided OTP against the stored one.

        Args:
            phone_number (str): The user's phone number.
            otp_input (str): The OTP input provided by the user.

        Returns:
            bool: True if OTP is valid, False otherwise.
        """
        data = self.otp_storage.get(phone_number)
        if not data:
            return False

        otp_stored, expiry_time = data
        if time.time() > expiry_time:
            del self.otp_storage[phone_number]
            return False

        if otp_input == otp_stored:
            del self.otp_storage[phone_number]
            return True

        return False
