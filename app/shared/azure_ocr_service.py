import io
from azure.cognitiveservices.vision.computervision import ComputerVisionClient
from msrest.authentication import CognitiveServicesCredentials
import os
import time

class AzureOCRService:
    def __init__(self):
        """
        Initialize the Azure OCR service.
        """
        # Get endpoint and key from environment variables
        self.endpoint = os.getenv("AZURE_OCR_ENDPOINT")
        self.key = os.getenv("AZURE_OCR_KEY")

        # Create a client
        self.client = ComputerVisionClient(self.endpoint, CognitiveServicesCredentials(self.key))

    def read_text_from_url(self, image_url):
        """
        Read text from an image URL using Azure OCR.

        :param image_url: URL of the image.
        :return: Extracted text as a single string.
        """
        # Call the batch_read_file API (asynchronous)
        raw_response = self.client.batch_read_file(image_url, raw=True)

        # Extract the operation ID from the response headers
        operation_location = raw_response.headers["Operation-Location"]
        operation_id = operation_location.split("/")[-1]

        # Poll the operation status until it is completed
        while True:
            # Use get_read_result instead of get_read_operation_result
            result = self.client.get_read_result(operation_id)
            if result.status not in ['notStarted', 'running']:
                break
            time.sleep(1)

        # If the operation succeeded, extract the text
        if result.status == "succeeded":
            extracted_text = []
            for text_result in result.analyze_result.read_results:
                for line in text_result.lines:
                    extracted_text.append(line.text)

            # Join all lines into a single string
            return "\n".join(extracted_text)

        # If the operation failed, return an empty string or raise an error
        return ""

    def read_text_from_image_bytes(self, image_bytes):
        """
        Read text from an image using Azure OCR with image bytes.

        :param image_bytes: Image in bytes format.
        :return: Extracted text as a single string.
        """
        # Convert bytes to a file-like object
        image_stream = io.BytesIO(image_bytes)

        # Call the read_in_stream API (asynchronous)
        raw_response = self.client.read_in_stream(image_stream, raw=True)

        # Extract the operation ID from the response headers
        operation_location = raw_response.headers["Operation-Location"]
        operation_id = operation_location.split("/")[-1]

        # Poll the operation status until it is completed
        while True:
            # Use get_read_result instead of get_read_operation_result
            result = self.client.get_read_result(operation_id)
            if result.status not in ['notStarted', 'running']:
                break
            time.sleep(1)

        # If the operation succeeded, extract the text
        if result.status == "succeeded":
            extracted_text = []
            for text_result in result.analyze_result.read_results:
                for line in text_result.lines:
                    extracted_text.append(line.text)

            # Join all lines into a single string
            return "\n".join(extracted_text)

        # If the operation failed, return an empty string or raise an error
        return ""