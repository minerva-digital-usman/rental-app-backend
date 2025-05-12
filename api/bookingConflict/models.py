import uuid
from django.db import models
from api.booking.models import Booking

class BookingConflict(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_RESOLVED = 'resolved'
    STATUS_CANCELLED = 'cancelled'  

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_RESOLVED, 'Resolved'),
        (STATUS_CANCELLED, 'Cancelled'),  
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    original_booking = models.ForeignKey(Booking, related_name='initiated_conflicts', on_delete=models.CASCADE)
    conflicting_booking = models.ForeignKey(Booking, related_name='conflicts', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    admin_notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Conflict between {self.original_booking.id} and {self.conflicting_booking.id} ({self.status})"
