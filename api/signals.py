from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Hotel
from .utils import generate_qr_code

@receiver(post_save, sender=Hotel)
def generate_hotel_qr_code(sender, instance, created, **kwargs):
    if created and instance.guest_booking_url:
        # Generate the QR code
        qr_code_image = generate_qr_code(instance.guest_booking_url)
        
        # Save the generated QR code image to the Hotel instance
        instance.qr_code.save(f"{instance.name}_qr_code.png", qr_code_image, save=False)
        
        # Save the instance to ensure QR code is stored
        instance.save()
