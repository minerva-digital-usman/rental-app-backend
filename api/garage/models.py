import os
from django.db import models
import uuid

from django.forms import ValidationError
from api.rental_company.models import RentalCompany
from api.hotel.models import Hotel  # ✅ Import Hotel model


class Car(models.Model):
    """
    Represents a rental car without QR code functionality.
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
        related_name='cars'
    )

    vehicle_type = models.CharField(
        max_length=50,
        choices=VEHICLE_TYPE_CHOICES,
        default="Sedan"
    )

    model = models.CharField(max_length=100)
    plate_number = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True, null=True)
    photo = models.ImageField(
        upload_to='car_photos/',
        blank=True,
        null=True,
        help_text="Optional photo of the car."
    )
    status = models.CharField(
        max_length=50,
        choices=VEHICLE_STATUS_CHOICES,
        default="available"
    )

    price_per_hour = models.FloatField(default=0.0)
    max_price_per_day = models.FloatField(default=0.0)

    passengers = models.PositiveIntegerField(
        default=4,
        help_text="Number of passengers the car can accommodate."
    )
    doors = models.PositiveIntegerField(
        default=4,
        help_text="Number of doors on the car."
    )
    luggage = models.PositiveIntegerField(
        default=1,
        help_text="Approximate number of luggage bags the car can fit."
    )

    transmission = models.CharField(
        max_length=10,
        choices=TRANSMISSION_CHOICES,
        default="Automatic",
        help_text="Type of transmission."
    )

    air_conditioning = models.BooleanField(
        default=True,
        help_text="Whether the car has air conditioning."
    )

    fuel_type = models.CharField(
        max_length=10,
        choices=FUEL_TYPE_CHOICES,
        default="Petrol",
        help_text="Type of fuel the car uses."
    )
    def delete(self, *args, **kwargs):
        # Delete the photo file from the file system
        if self.photo and os.path.isfile(self.photo.path):
            os.remove(self.photo.path)
        super().delete(*args, **kwargs)
    def save(self, *args, **kwargs):
        try:
            # Check if updating existing photo
            this = Car.objects.get(id=self.id)
            if this.photo and this.photo != self.photo:
                if os.path.isfile(this.photo.path):
                    os.remove(this.photo.path)
        except Car.DoesNotExist:
            pass  # It's a new object, no file to remove

        super().save(*args, **kwargs)
        
    def clean(self):
        # Custom validation to ensure pricing is not negative
        if self.price_per_hour < 0:
            raise ValidationError("Price per hour cannot be negative.")
        if self.max_price_per_day < 0:
            raise ValidationError("Max price per day cannot be negative.")

    def __str__(self):
        return f"{self.model} ({self.plate_number})"
