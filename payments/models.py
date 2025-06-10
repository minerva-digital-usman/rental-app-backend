# api/payment/models.py

import uuid
from django.db import models
from api.booking.models import Booking

class Payment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='payments')
    stripe_session_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    stripe_customer_id = models.CharField(max_length=255, null=True, blank=True)
    stripe_payment_intent_id = models.CharField(max_length=255, null=True, blank=True)
    stripe_setup_intent_id = models.CharField(max_length=255, null=True, blank=True)
    stripe_payment_method_id = models.CharField(max_length=255, null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default='CHF')
    status = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)
    payment_type = models.CharField(max_length=20, choices=[
        ('initial', 'Initial Payment'),
        ('extension', 'Extension Payment'),
        ('fine', 'Traffic Fine')
    ], default='initial')
    
    # Additional fields for payment method details
    payment_method_type = models.CharField(max_length=50, null=True, blank=True)
    payment_method_brand = models.CharField(max_length=50, null=True, blank=True)
    payment_method_last4 = models.CharField(max_length=4, null=True, blank=True)

    def __str__(self):
        return f"Payment {self.id} for booking {self.booking.id} - {self.amount} {self.currency}"
    
    @property
    def can_be_used_for_fines(self):
        """Check if this payment can be used for future charges (like fines)"""
        return bool(self.stripe_payment_method_id) and self.status == 'succeeded'