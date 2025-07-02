import re
from typing import Optional, Tuple
import easyocr
from PIL import Image
import numpy as np
from datetime import datetime




# Create the EasyOCR reader (reuse it for performance)
reader = easyocr.Reader(['en', 'de', 'fr', 'it'], gpu=False)  # Set gpu=True if you have a CUDA GPU
def extract_expiry_date(text: str) -> Optional[str]:
    # First try to find Italian license format with 4a and 4b markers
    italian_pattern = r"4a\.\s*(\d{2}/\d{2}/\d{4}).*?4b\.\s*(\d{2}/\d{2}/\d{4})"
    italian_match = re.search(italian_pattern, text, re.DOTALL)
    
    if italian_match:
        # Return the expiry date (4b)
        return italian_match.group(2)
    
    # Fall back to original pattern if not Italian format
    date_pattern = r"\b\d{2}-[A-Za-z]{3}-\d{2}\b|\b\d{2}-[A-Za-z]{3}-\d{4}\b|\b\d{2}/\d{2}/\d{4}\b|\b\d{4}-\d{2}-\d{2}\b"
    dates = [(m.group(), m.start(), m.end()) for m in re.finditer(date_pattern, text, re.IGNORECASE)]
    
    expiry_keywords = [
        "expiry date", "expires", "valid until", "expiration date", "4b",
        "gültig bis", "valable jusqu", "valido fino"
    ]
    
    for keyword in expiry_keywords:
        keyword_pos = text.lower().find(keyword)
        if keyword_pos != -1:
            for date, start, end in dates:
                if start > keyword_pos:
                    return date
    return None

def validate_driver_license(text: str) -> bool:
    text_lower = text.lower()
    # Add Italian-specific keywords
    keywords = [
        'driver', 'license', 'dl', 'sex', 'dob', 'class', 'expiry date', 'exp',
        '4a', '4b', 'patente', 'guida', 'italiana', 'italiano',
        'führerausweis', 'permis de conduire', 'patente di guida',  # CH langs
        'confédération suisse', 'schweizerische eidgenossenschaft', 'confederazione svizzera'
    ]
    match_count = sum(1 for keyword in keywords if keyword in text_lower)
    return match_count <= 0


def is_driver_license_expired(expiry_date: str) -> Tuple[bool, Optional[datetime]]:
    try:
        if "-" in expiry_date:
            # Format could be DD-MMM-YY or DD-MMM-YYYY
            if len(expiry_date.split('-')[2]) == 2:  # Check if it's a two-digit year
                expiry_date = expiry_date.replace(expiry_date.split('-')[2], '20' + expiry_date.split('-')[2])
            expiry_date_obj = datetime.strptime(expiry_date, "%d-%b-%Y")  # Expecting date like 05-May-2025
        elif "/" in expiry_date:
            # Format could be DD/MM/YYYY
            expiry_date_obj = datetime.strptime(expiry_date, "%d/%m/%Y")  # Expecting date like 05/05/2025
        else:
            # Format could be YYYY-MM-DD
            expiry_date_obj = datetime.strptime(expiry_date, "%Y-%m-%d")  # Expecting date like 2025-05-05

        # Compare the expiry date with today's date
        today = datetime.today()
        return expiry_date_obj < today, expiry_date_obj  # Return True if expired and the date object
    except ValueError:
        print("Invalid expiry date format")
        return False, None



def is_driver_license_easyocr(image_stream) -> Tuple[bool, Optional[str], Optional[bool]]:
    image = Image.open(image_stream)
    image_np = np.array(image)
    results = reader.readtext(image_np, detail=0)
    text = " ".join(results)
    print("EasyOCR text:", text)
    
    # First validate it's a driver's license
    if not validate_driver_license(text):
        return False, None, None
    
    # Then check for expiry date
    expiry_date = extract_expiry_date(text)
    is_expired = None
    
    if expiry_date:
        print(f"Expiry Date Found: {expiry_date}")
        is_expired, _ = is_driver_license_expired(expiry_date)
        if is_expired:
            print("License has expired.")
        else:
            print("License is valid.")
    
    return True, expiry_date, is_expired