from io import BytesIO
from django.db import models
import uuid
from geopy.geocoders import Nominatim
from geopy.geocoders import Nominatim
from django.core.exceptions import ValidationError
import re
from django.core.files.base import ContentFile
from numpy import atan2, cos, radians, sin, sqrt
import qrcode
from api.rental_company.models import RentalCompany  # Adjust if needed
from django.db.models.signals import pre_delete
from django.dispatch import receiver
import os
from django.conf import settings

class HotelManager(models.Manager):
    
    def nearby_hotels(self, lat, lon, radius_km=10, max_results=20):
        """
        Find hotels within a given radius (in kilometers) of a point.
        Returns a list of dictionaries with hotel info and distance.
        
        Args:
            lat (float): Latitude of the center point
            lon (float): Longitude of the center point
            radius_km (float): Search radius in kilometers (default 10)
            max_results (int): Maximum number of results to return (default 20)
        """
        # Convert latitude and longitude from degrees to radians
        lat_rad = radians(float(lat))
        lon_rad = radians(float(lon))
        
        # Earth's radius in km
        R = 6371.0
        
        # First, filter hotels within a rough bounding box for performance
        # Calculate approximate degree distances (1 degree ≈ 111 km)
        degree_buffer = radius_km / 111
        min_lat = float(lat) - degree_buffer
        max_lat = float(lat) + degree_buffer
        min_lon = float(lon) - degree_buffer
        max_lon = float(lon) + degree_buffer
        
        # Get all hotels in the bounding box
        hotels_in_box = self.get_queryset().filter(
            latitude__gte=min_lat,
            latitude__lte=max_lat,
            longitude__gte=min_lon,
            longitude__lte=max_lon
        )
        
        nearby_hotels = []
        for hotel in hotels_in_box:
            # Convert hotel coordinates to radians
            hotel_lat = radians(float(hotel.latitude))
            hotel_lon = radians(float(hotel.longitude))
            
            # Haversine formula
            dlon = hotel_lon - lon_rad
            dlat = hotel_lat - lat_rad
            a = sin(dlat / 2)**2 + cos(lat_rad) * cos(hotel_lat) * sin(dlon / 2)**2
            c = 2 * atan2(sqrt(a), sqrt(1 - a))
            distance = R * c
            
            if distance <= radius_km:
                nearby_hotels.append({
                    'hotel': hotel,
                    'distance_km': distance
                })
        
        # Sort by distance and limit results
        nearby_hotels.sort(key=lambda x: x['distance_km'])
        return nearby_hotels[:max_results]

class Hotel(models.Model):
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
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    
    # Add the custom manager
    objects = HotelManager()
    def geocode_address(self):
        """
        Uses the OpenStreetMap Nominatim API to get latitude and longitude from the address.
        """
        geolocator = Nominatim(user_agent="hotel_booking")
        location = geolocator.geocode(self.location)

        if location:
            self.latitude = location.latitude
            self.longitude = location.longitude
        else:
            raise ValidationError(f"Could not geocode the address: {self.location}")

    def save(self, *args, **kwargs):
        # Automatically set latitude and longitude if the location changes
        if self.location and not self.latitude and not self.longitude:
            self.geocode_address()

        super().save(*args, **kwargs)

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
