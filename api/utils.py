import qrcode
from io import BytesIO
from django.core.files.base import ContentFile

def generate_qr_code(data):
    """
    Generates a QR code image for the given data.
    Returns the image file to be saved in a model field.
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return ContentFile(buffer.getvalue())
