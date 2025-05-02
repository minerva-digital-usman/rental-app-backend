# api/payment/models.py

import uuid
from django.db import models
from api.booking.models import Booking

# api/payment/models.py

class Payment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='payments')  # Changed to ForeignKey
    stripe_session_id = models.CharField(max_length=255, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default='EUR')
    status = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)
    payment_type = models.CharField(max_length=20, choices=[
        ('initial', 'Initial Payment'),
        ('extension', 'Extension Payment'),
        ('fine', 'Traffic Fine')  # Add this new type
    ], default='initial')

    def __str__(self):
        return f"Payment {self.id} for booking {self.booking.id} - {self.amount} {self.currency}"
    
class CustomerPaymentMethod(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='payment_methods')
    stripe_payment_method_id = models.CharField(max_length=255, unique=True)
    card_brand = models.CharField(max_length=50)
    card_last4 = models.CharField(max_length=4)
    created_at = models.DateTimeField(auto_now_add=True)
    is_default = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.card_brand} ending in {self.card_last4}"