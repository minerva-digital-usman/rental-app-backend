from io import BytesIO
import os
import uuid
from django.db import models
from django.core.files.base import ContentFile
from django.dispatch import receiver
from django.db.models.signals import pre_delete
from django.forms import ValidationError
import qrcode

from api.rental_company.models import RentalCompany
from django.conf import settings
from api.hotel.models import Hotel  # ✅ Import Hotel model


class Vehicle(models.Model):
    """
    Represents a rental vehicle with a QR code linking to the extend URL.
    QR image saved as: 'qr_{model}_{plate}.png'
    """

    VEHICLE_STATUS_CHOICES = [
        ("available", "Available"),
        ("booked", "Booked"),
        ("cleaning", "Cleaning"),
        ("outofservice", "Out of Service"),
    ]

    VEHICLE_TYPE_CHOICES = [
        ("SUV", "SUV"),
        ("Sedan", "Sedan"),
        ("Hatchback", "Hatchback"),
        ("Convertible", "Convertible"),
        ("Van", "Van"),
    ]

    TRANSMISSION_CHOICES = [
        ("automatic", "Automatic"),
        ("manual", "Manual"),
    ]

    FUEL_TYPE_CHOICES = [
        ("petrol", "Petrol"),
        ("diesel", "Diesel"),
        ("hybrid", "Hybrid"),
        ("electric", "Electric"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    rental_company = models.ForeignKey(
        RentalCompany,
        on_delete=models.CASCADE,
        related_name='vehicles'
    )

    hotel = models.ForeignKey(  # ✅ Added hotel field
        Hotel,
        on_delete=models.CASCADE,
        related_name='vehicles',
        help_text="Hotel where the vehicle is available"
    )

    vehicle_type = models.CharField(
        max_length=50,
        choices=VEHICLE_TYPE_CHOICES,
        default="Sedan"
    )

    model = models.CharField(max_length=100)
    plate_number = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True, null=True)

    status = models.CharField(
        max_length=50,
        choices=VEHICLE_STATUS_CHOICES,
        default="available"
    )

    price_per_hour = models.FloatField(default=0.0)
    max_price_per_day = models.FloatField(default=0.0)

    in_car_extension_url = models.URLField(
        blank=True,
        null=True,
        unique=True,
        help_text="Auto-generated URL for rental extension"
    )
    qr_code = models.ImageField(upload_to='vehicle_qr_codes/', blank=True, null=True)

    passengers = models.PositiveIntegerField(
        default=4,
        help_text="Number of passengers the vehicle can accommodate."
    )
    doors = models.PositiveIntegerField(
        default=4,
        help_text="Number of doors on the vehicle."
    )
    luggage = models.PositiveIntegerField(
        default=1,
        help_text="Approximate number of luggage bags the vehicle can fit."
    )

    transmission = models.CharField(
        max_length=10,
        choices=TRANSMISSION_CHOICES,
        default="Automatic",
        help_text="Type of transmission."
    )

    air_conditioning = models.BooleanField(
        default=True,
        help_text="Whether the vehicle has air conditioning."
    )

    fuel_type = models.CharField(
        max_length=10,
        choices=FUEL_TYPE_CHOICES,
        default="Petrol",
        help_text="Type of fuel the vehicle uses."
    )

    def generate_in_car_extension_url(self):
        """Generates a clean extend URL using the vehicle's UUID."""
          # Replace with your domain
        return f"{settings.BASE_URL_BACKEND}/api/vehicles/{self.id}/"

    def generate_qr_code(self):
        """Generates a QR code with ONLY the extend URL (clean for scanning)."""
        if not self.in_car_extension_url:
            raise ValueError("in_car_extension_url must be set.")

        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(self.in_car_extension_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        buffer = BytesIO()
        img.save(buffer, format="PNG")
        filename = f"qr_{self.model}_{self.plate_number}.png".replace(" ", "_")
        self.qr_code.save(filename, ContentFile(buffer.getvalue()), save=False)
        buffer.close()

    @receiver(pre_delete, sender='api.Vehicle')  # Adjust sender if needed
    def delete_qr_code(sender, instance, **kwargs):
        if instance.qr_code:
            file_path = instance.qr_code.path
            if os.path.isfile(file_path):
                os.remove(file_path)
                print(f"QR code for vehicle {instance.id} deleted from storage.")




    def clean(self):
        if self.hotel:
            # Only count other vehicles (exclude self in update case)
            existing_vehicles = Vehicle.objects.filter(hotel=self.hotel).exclude(pk=self.pk)
            if existing_vehicles.count() >= 2:
                raise ValidationError("Each hotel can only have up to 2 vehicles.")

    def save(self, *args, **kwargs):
        self.full_clean()  # Ensures validation is enforced
        if not self.in_car_extension_url:
            self.in_car_extension_url = self.generate_in_car_extension_url()

        if not self.qr_code or self._url_changed():
            self.generate_qr_code()

        super().save(*args, **kwargs)


    def _url_changed(self):
        """Checks if URL was modified compared to the DB version."""
        if not self.pk:
            return False
        try:
            old = Vehicle.objects.get(pk=self.pk)
            return old.in_car_extension_url != self.in_car_extension_url
        except Vehicle.DoesNotExist:
            return False

    def __str__(self):
        return f"{self.model} ({self.plate_number})"
