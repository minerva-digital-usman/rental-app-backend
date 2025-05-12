# payments/utils.py

import stripe
from django.conf import settings
from payments.models import Payment

stripe.api_key = settings.STRIPE_SECRET_KEY

def refund_payment_for_booking(booking):
    """
    Refunds the most recent successful payment for a given booking.
    Returns True if refund successful, False otherwise.
    """
    try:
        payment = Payment.objects.filter(
            booking=booking, status='succeeded'
        ).order_by('-created_at').first()

        if not payment:
            return False, "No successful payment found for this booking."

        if not payment.stripe_payment_intent_id:
            return False, "Missing Stripe PaymentIntent ID."

        # Perform refund
        stripe.Refund.create(
            payment_intent=payment.stripe_payment_intent_id,
            reason="requested_by_customer"  # Optional
        )

        # Update payment status
        payment.status = 'refunded'
        payment.save()

        return True, "Refund successful."
    except stripe.error.StripeError as e:
        return False, f"Stripe error: {str(e)}"
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"
