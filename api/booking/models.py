import uuid
from django.db import models
from django.core.exceptions import ValidationError
from api.hotel.models import Hotel
from api.guest.models import Guest  # Ensure correct import path

from datetime import timedelta

from api.garage.models import Car

class Booking(models.Model):
    STATUS_ACTIVE = 'active'
    STATUS_CANCELLED = 'cancelled'
    STATUS_PENDING_CONFLICT = 'pending_conflict'

    STATUS_CHOICES = [
        (STATUS_ACTIVE, 'Active'),
        (STATUS_CANCELLED, 'Cancelled'),
        (STATUS_PENDING_CONFLICT, 'Pending Conflict'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    vehicle = models.ForeignKey(Car, on_delete=models.CASCADE, related_name="bookings")  # Adjusted to Car model
    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE, related_name="bookings")
    guest = models.ForeignKey(Guest, on_delete=models.CASCADE, related_name="bookings")

    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    buffer_time = models.IntegerField(default=30)  # Store buffer time in minutes
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_ACTIVE
    )
  # Store buffer time in minutes

    def __str__(self):
        return (
            f"Booking for {self.guest.first_name} {self.guest.last_name} - "
            f"{self.vehicle.model} ({self.vehicle.plate_number}) "
            f"from {self.start_time.strftime('%Y-%m-%d %H:%M')} "
            f"to {self.end_time.strftime('%Y-%m-%d %H:%M')} (Buffer: {self.buffer_time} minutes)"
        )

    def clean(self):
        # Skip validation if the status is 'cancelled' or 'pending_conflict'
        if self.status in [self.STATUS_CANCELLED, self.STATUS_PENDING_CONFLICT]:
            return  # Skip validation

        if self.start_time >= self.end_time:
            raise ValidationError("End time must be after start time.")

        # Calculate effective end time (with buffer)
        effective_end = self.end_time
        if not self.pk:  # New booking
            if self.buffer_time:
                effective_end = self.end_time + timedelta(minutes=self.buffer_time)
        else:  # Existing booking
            try:
                original = Booking.objects.get(pk=self.pk)
                if original.buffer_time != self.buffer_time:
                    original_duration = original.end_time - original.start_time - timedelta(minutes=original.buffer_time)
                    effective_end = self.start_time + original_duration + timedelta(minutes=self.buffer_time)
            except Booking.DoesNotExist:
                if self.buffer_time:
                    effective_end = self.end_time + timedelta(minutes=self.buffer_time)

        # Check overlaps
        overlapping_bookings = Booking.objects.filter(
            vehicle=self.vehicle,
            end_time__gt=self.start_time,
            start_time__lt=self.end_time
        ).exclude(id=self.id).exclude(status__in=[self.STATUS_CANCELLED, self.STATUS_PENDING_CONFLICT])

        if overlapping_bookings.exists():
            raise ValidationError("This vehicle is already booked for the selected time.")


    def save(self, *args, **kwargs):
        # For new bookings (creation)
        if not self.pk:
            if self.buffer_time:
                self.end_time = self.end_time + timedelta(minutes=self.buffer_time)
        else:
            try:
                # For existing bookings (update)
                original = Booking.objects.get(pk=self.pk)
                if original.buffer_time != self.buffer_time:
                    # Calculate the original duration without buffer
                    original_duration = original.end_time - original.start_time - timedelta(minutes=original.buffer_time)
                    # Set new end time based on original duration + new buffer
                    self.end_time = self.start_time + original_duration + timedelta(minutes=self.buffer_time)
            except Booking.DoesNotExist:
                # If original booking was deleted, treat as new booking
                if self.buffer_time:
                    self.end_time = self.end_time + timedelta(minutes=self.buffer_time)
        
        # Always call clean() for validation
        self.clean()
        
        super().save(*args, **kwargs)
    
