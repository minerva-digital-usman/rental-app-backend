# from django.db import models
# import uuid


# # class RentalCompany(models.Model):
# #     """
# #     Represents a vehicle rental company integrated into the platform.
# #     """
# #     id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
# #     name = models.CharField(max_length=100)
# #     address = models.TextField()
# #     phone_number = models.CharField(max_length=15, unique=True)
# #     email = models.EmailField(unique=True)
# #     portal_url = models.URLField(
# #         blank=True,
# #         null=True,
# #         help_text="URL for the rental company's admin portal or reference"
# #     )

# #     def __str__(self):
# #         return self.name


# # class Hotel(models.Model):
# #     """
# #     Represents a hotel using the QR-based car rental platform.
# #     """
# #     id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
# #     name = models.CharField(max_length=100)
# #     location = models.CharField(max_length=255)
# #     phone = models.CharField(max_length=15, unique=True)
# #     email = models.EmailField(unique=True)
# #     rental_company = models.ForeignKey(
# #         RentalCompany,
# #         on_delete=models.CASCADE,
# #         related_name='hotels'
# #     )

# #     guest_booking_url = models.URLField(
# #         unique=True,
# #         help_text="URL encoded in hotel QR code to access car rental booking page"
# #     )

# #     def __str__(self):
# #         return self.name


# class Vehicle(models.Model):
#     """
#     Represents a rental vehicle managed by a rental company.
#     """
#     VEHICLE_STATUS_CHOICES = [
#         ("available", "Available"),
#         ("booked", "Booked"),
#         ("cleaning", "Cleaning"),
#         ("outofservice", "Out of Service"),
#     ]

#     id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
#     rental_company = models.ForeignKey(
#         RentalCompany,
#         on_delete=models.CASCADE,
#         related_name='vehicles'
#     )

#     vehicle_type = models.CharField(max_length=100)  # e.g., SUV, Sedan
#     model = models.CharField(max_length=100)
#     plate_number = models.CharField(max_length=50, unique=True)
#     description = models.TextField(blank=True, null=True)

#     status = models.CharField(
#         max_length=50,
#         choices=VEHICLE_STATUS_CHOICES,
#         default="available"
#     )

#     price_per_hour = models.FloatField(default=0.0)
#     max_price_per_day = models.FloatField(default=0.0)

#     in_car_extension_url = models.URLField(
#         unique=True,
#         help_text="URL encoded in car QR code for rental extension"
#     )

#     def __str__(self):
#         return f"{self.vehicle_type} - {self.model} ({self.plate_number})"
