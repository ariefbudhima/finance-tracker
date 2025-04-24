from PIL import Image
import pytesseract
import numpy as np
from io import BytesIO
import cv2
import easyocr

class OCRProcessor:
    def __init__(self, easyocr_langs=['en']):
        self.easyocr_reader = easyocr.Reader(easyocr_langs)

    def process_image_tesseract(self, image_bytes: bytes) -> str:
        img = Image.open(BytesIO(image_bytes)).convert('L')
        grayscale_image = img.convert("L")
        img_np = np.array(grayscale_image)

        # Resize
        img_np = cv2.resize(img_np, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)

        # Perkuat kontras
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        img_np = clahe.apply(img_np)

        # Bersihin noise
        img_np = cv2.GaussianBlur(img_np, (3, 3), 0)

        # Adaptive thresholding
        img_np = cv2.adaptiveThreshold(
            img_np, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 11, 2
        )

        processed_img = Image.fromarray(img_np)

        custom_config = r'--psm 6 -c tessedit_char_whitelist="0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ:/.,"'
        extracted_text = pytesseract.image_to_string(processed_img, config=custom_config)

        return extracted_text

    @staticmethod
    def group_text_by_line(result, y_threshold=10):
        # Group result into lines using Y coordinate
        lines = []
        result = sorted(result, key=lambda r: r[0][0][1])  # Sort by Y

        current_line = []
        current_y = None

        for box, text, conf in result:
            y = box[0][1]  # Top-left Y

            if current_y is None:
                current_y = y
                current_line.append((box, text))
            elif abs(y - current_y) < y_threshold:
                current_line.append((box, text))
            else:
                # Sort line by X
                current_line = sorted(current_line, key=lambda r: r[0][0][0])  # sort by X
                lines.append(" ".join([text for _, text in current_line]))
                current_line = [(box, text)]
                current_y = y

        if current_line:
            current_line = sorted(current_line, key=lambda r: r[0][0][0])
            lines.append(" ".join([text for _, text in current_line]))

        return lines

    def easyocr_cleaned_lines(self, image_bytes: bytes):
        np_img = np.frombuffer(image_bytes, np.uint8)
        img_cv = cv2.imdecode(np_img, cv2.IMREAD_COLOR)

        result = self.easyocr_reader.readtext(img_cv)
        lines = self.group_text_by_line(result)
        return "\n".join(lines)