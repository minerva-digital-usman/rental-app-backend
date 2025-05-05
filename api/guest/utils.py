import easyocr
from PIL import Image
import io

# Create the EasyOCR reader (reuse it for performance)
reader = easyocr.Reader(['en'], gpu=False)  # Set gpu=True if you have a CUDA GPU

def is_driver_license_easyocr(image_stream):
    from PIL import Image
    import numpy as np

    image = Image.open(image_stream)
    image_np = np.array(image)
    results = reader.readtext(image_np, detail=0)
    text = " ".join(results).lower()
    print("EasyOCR text:", text)

    keywords = ['driver', 'license', 'dl', 'sex', 'dob', 'class', 'expiry date']
    match_count = sum(1 for keyword in keywords if keyword in text)

    return match_count >= 2

