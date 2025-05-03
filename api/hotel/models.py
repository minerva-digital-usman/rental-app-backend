from io import BytesIO
from django.db import models
import uuid

import re
from django.core.files.base import ContentFile
import qrcode
from api.rental_company.models import RentalCompany  # Adjust if needed
from django.db.models.signals import pre_delete
from django.dispatch import receiver
import os
from django.conf import settings

class Hotel(models.Model):
    """
    Represents a hotel using the QR-based car rental platform.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    location = models.CharField(max_length=255)
    phone = models.CharField(max_length=15, unique=True)
    email = models.EmailField(unique=True)
    rental_company = models.ForeignKey(
        RentalCompany,
        on_delete=models.CASCADE,
        related_name='hotels'
    )

    guest_booking_url = models.URLField(
        unique=True,
        blank=True,
        help_text="URL encoded in hotel QR code to access car rental booking page"
    )
    qr_code = models.ImageField(upload_to='hotel_qr_codes/', blank=True, null=True)

    def generate_guest_booking_url(self):
        """
        Generates a unique booking URL for the hotel that includes the hotel ID.
        The URL will redirect the guest to the booking page.
        Format: http://localhost:5173/hotels/<hotel_id>
        """
          # Adjust this to your actual booking page URL
        return f"{settings.BASE_URL_FRONTEND}/hotels/{self.id}"  # hotel_id is embedded in the URL

    def generate_qr_code(self):
        """
        Generates a QR code for the guest_booking_url and stores it.
        """
        if not self.guest_booking_url:
            raise ValueError("Guest booking URL must be set before generating QR code.")

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(self.guest_booking_url)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format="PNG")

        safe_name = re.sub(r'\W+', '_', self.name.lower())
        file_name = f"{safe_name}_{self.id}_qr_code.png"

        self.qr_code.save(file_name, ContentFile(buffer.getvalue()), save=False)
        buffer.close()

    def save(self, *args, **kwargs):
        is_new = self._state.adding  # True if this is a new object
        old_name = None
        if not is_new:
            old_name = Hotel.objects.get(pk=self.pk).name

        if not self.guest_booking_url:
            self.guest_booking_url = self.generate_guest_booking_url()

        if is_new or not self.qr_code or (old_name and old_name != self.name):
            self.generate_qr_code()

        super().save(*args, **kwargs)

    # Signal to delete the QR code file when a hotel is deleted
    @receiver(pre_delete, sender='api.Hotel')  # Use the actual app name and model name
    def delete_qr_code(sender, instance, **kwargs):
        if instance.qr_code:
            # Get the file path and remove the file from storage
            file_path = instance.qr_code.path
            if os.path.isfile(file_path):
                os.remove(file_path)
                print(f"QR code for hotel {instance.id} deleted from storage.")

    def __str__(self):
        return f"{self.name} ({self.location})  - {self.email}  {self.phone}"
