from app.shared.azure_ocr_service import AzureOCRService

class OCRProcessor:
    def __init__(self):
        """
        Initialize the OCRProcessor class with Azure OCR service.
        """
        self.ocr_service = AzureOCRService()


    
    def azure_ocr_url(self, image_url: str):
        """
        Perform OCR using Azure OCR service.

        :param image_url: URL of the image.
        :return: Extracted text as a single string.
        """
        return self.ocr_service.read_text_from_url(image_url)
    
    def azure_ocr(self, image_bytes: bytes):
        """
        Perform OCR using Azure OCR service.

        :param image_bytes: Image in bytes format.
        :return: Extracted text as a single string.
        """
        return self.ocr_service.read_text_from_image_bytes(image_bytes)