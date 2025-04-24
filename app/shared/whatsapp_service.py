import requests
import logging
import base64

class WhatsAppAPI:
    def __init__(self, api_url, session, endpoints):
        """Inisialisasi objek WhatsAppAPI dengan URL API dan session"""
        self.api_url = api_url
        self.session = session
        self.endpoints = endpoints
    
    def send_text_message(self, recipient, body, content_type="string"):
        """Mengirim pesan ke WhatsApp"""
        url = f"{self.api_url}{self.endpoints['send_message']}{self.session}"
        headers = {"Content-Type": "application/json"}
        payload = {
        "chatId": recipient, 
            "contentType": content_type, 
            "content": body
        }

        logging.info(f"Sending message to {recipient}: {body}")
        # Kirim request ke API WhatsApp
        response = requests.post(url, headers=headers, json=payload)
        
        # Kembalikan response dari request
        return response
    
    def download_media(self, chat_id, message_id, return_as_base64=False):
        """download media"""
        url = f"{self.api_url}/message/downloadMedia/{self.session}"
        headers = {"Content-Type": "application/json"}
        payload = {"chatId": chat_id, "messageId": message_id}
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        media_data = response.json().get("messageMedia", {}).get("data")
        if return_as_base64:
            return media_data
        return base64.b64decode(media_data)