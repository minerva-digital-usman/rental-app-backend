from django.db import models
import uuid
from django.core.exceptions import ValidationError
from api.rental_company.models import RentalCompany
from api.hotel.models import Hotel
from api.garage.models import Car
from io import BytesIO
import os
import qrcode
from django.core.files.base import ContentFile
from django.conf import settings

class CarHotelLink(models.Model):
    """
    A link between a car and a hotel with QR code functionality.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    car = models.OneToOneField(
        Car,
        on_delete=models.CASCADE,
        related_name='hotel_link',
    )
    
    hotel = models.ForeignKey(
        Hotel,
        on_delete=models.CASCADE,
        related_name='linked_cars',
    )
    
    in_car_extension_url = models.URLField(
        blank=True,
        null=True,
        unique=True,
        help_text="Auto-generated URL for rental extension"
    )
    qr_code = models.ImageField(upload_to='car_qr_codes/', blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('car', 'hotel')
    
    def generate_in_car_extension_url(self):
        """Generates a URL that includes both car and hotel IDs."""
        return f"{settings.BASE_URL_FRONTEND}/extend-booking/{self.hotel.id}/{self.car.id}/"

    
    def generate_qr_code(self):
        """Generates a QR code with the extend URL."""
        if not self.in_car_extension_url:
            self.in_car_extension_url = self.generate_in_car_extension_url()

        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(self.in_car_extension_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        buffer = BytesIO()
        img.save(buffer, format="PNG")
        filename = f"qr_{self.car.model}_{self.car.plate_number}.png".replace(" ", "_")
        self.qr_code.save(filename, ContentFile(buffer.getvalue()), save=False)
        buffer.close()
    
    def clean(self):
        if CarHotelLink.objects.filter(car=self.car).exclude(id=self.id).exists():
            raise ValidationError('This car is already linked to another hotel.')
    
    def save(self, *args, **kwargs):
        self.full_clean()
        if not self.in_car_extension_url:
            self.in_car_extension_url = self.generate_in_car_extension_url()
        
        super().save(*args, **kwargs)
        # Generate QR code after save to ensure we have an ID
        if not self.qr_code:
            self.generate_qr_code()
            super().save(update_fields=['qr_code'])
    
    def delete(self, *args, **kwargs):
        """Delete the QR code file when the link is deleted."""
        if self.qr_code:
            if os.path.isfile(self.qr_code.path):
                os.remove(self.qr_code.path)
        super().delete(*args, **kwargs)
    
    def __str__(self):
        return f"Car {self.car} linked to Hotel {self.hotel}"