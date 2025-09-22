import re
from typing import Optional, Tuple
from paddleocr import PaddleOCR
from PIL import Image
import numpy as np
from datetime import datetime

# Initialize PaddleOCR (CPU mode, English)
ocr_reader = PaddleOCR(use_angle_cls=True, lang='en')  # CPU only

def extract_expiry_date(text: str) -> Optional[str]:
    italian_pattern = r"4a\.\s*(\d{2}/\d{2}/\d{4}).*?4b\.\s*(\d{2}/\d{2}/\d{4})"
    italian_match = re.search(italian_pattern, text, re.DOTALL)
    if italian_match:
        return italian_match.group(2)
    
    date_pattern = r"\b\d{2}-[A-Za-z]{3}-\d{2}\b|\b\d{2}-[A-Za-z]{3}-\d{4}\b|\b\d{2}/\d{2}/\d{4}\b|\b\d{4}-\d{2}-\d{2}\b"
    dates = [(m.group(), m.start(), m.end()) for m in re.finditer(date_pattern, text, re.IGNORECASE)]
    
    expiry_keywords = ["expiry date", "expires", "valid until", "expiration date", "4b",
                       "gültig bis", "valable jusqu", "valido fino"]
    
    for keyword in expiry_keywords:
        keyword_pos = text.lower().find(keyword)
        if keyword_pos != -1:
            for date, start, end in dates:
                if start > keyword_pos:
                    return date
    return None

def validate_driver_license(text: str) -> bool:
    text_lower = text.lower()
    keywords = [
        'driver', 'license', 'dl', 'sex', 'dob', 'class', 'expiry date', 'exp',
        '4a', '4b', 'patente', 'guida', 'italiana', 'italiano',
        'führerausweis', 'permis de conduire', 'patente di guida',  
        'confédération suisse', 'schweizerische eidgenossenschaft', 'confederazione svizzera'
    ]
    match_count = sum(1 for keyword in keywords if keyword in text_lower)
    return match_count >= 2

def is_driver_license_expired(expiry_date: str) -> Tuple[bool, Optional[datetime]]:
    try:
        if "-" in expiry_date:
            if len(expiry_date.split('-')[2]) == 2:
                expiry_date = expiry_date.replace(expiry_date.split('-')[2], '20' + expiry_date.split('-')[2])
            expiry_date_obj = datetime.strptime(expiry_date, "%d-%b-%Y")
        elif "/" in expiry_date:
            expiry_date_obj = datetime.strptime(expiry_date, "%d/%m/%Y")
        else:
            expiry_date_obj = datetime.strptime(expiry_date, "%Y-%m-%d")
        today = datetime.today()
        return expiry_date_obj < today, expiry_date_obj
    except ValueError:
        return False, None

def is_driver_license_paddleocr(image_stream) -> Tuple[bool, Optional[str], Optional[bool]]:
    try:
        image = Image.open(image_stream)
        image_np = np.array(image)
    except Exception as e:
        print("Image open error:", e)
        return False, None, None

    try:
        # NEW: Remove `cls` keyword, just call ocr()
        result = ocr_reader.ocr(image_np)
        # PaddleOCR returns a list of lines per page
        lines = []
        for line in result[0]:  # page 0
            lines.append(line[1][0])  # line[1][0] is the recognized text
        text = " ".join(lines)
        print("PaddleOCR text:", text)
    except Exception as e:
        print("OCR error:", e)
        return False, None, None

    if not validate_driver_license(text):
        return False, None, None

    expiry_date = extract_expiry_date(text)
    is_expired = None
    if expiry_date:
        is_expired, _ = is_driver_license_expired(expiry_date)
    
    return True, expiry_date, is_expired
