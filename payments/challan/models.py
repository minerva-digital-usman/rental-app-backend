from django.core.mail import EmailMessage  # Make sure to import Django's EmailMessage
import uuid
from django.db import models
import stripe
from api.booking.models import Booking
from api.garage.models import Car
from api.booking.email_service import Email
from middleware_platform import settings
from payments.models import Payment


class TrafficFine(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name="traffic_fines")
    image = models.ImageField(upload_to='challans/')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    reason = models.CharField(max_length=255, default="Traffic violation")
    created_at = models.DateTimeField(auto_now_add=True)
    charged_payment = models.OneToOneField(Payment, null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return f"Fine for {self.booking} - €{self.amount}"
 
    
    def charge_fine(self):
        """
        Charge the fine to the customer's payment method on file
        """
        if self.charged_payment:
            raise ValueError("This fine has already been charged")
            
        # Find the most recent successful payment with payment method
        payment = Payment.objects.filter(
            booking=self.booking,
            stripe_payment_method_id__isnull=False,
            stripe_customer_id__isnull=False,
            status='succeeded'
        ).order_by('-created_at').first()
        
        if not payment:
            raise ValueError("No reusable payment method found for this booking")
        
        try:
            # Create SetupIntent to verify payment method can be used off-session
            setup_intent = stripe.SetupIntent.create(
                customer=payment.stripe_customer_id,
                payment_method=payment.stripe_payment_method_id,
                api_key=settings.STRIPE_SECRET_KEY
            )
            
            # Create and confirm PaymentIntent
            payment_intent = stripe.PaymentIntent.create(
                amount=int(float(self.amount) * 100),
                currency='chf',
                customer=payment.stripe_customer_id,
                payment_method=payment.stripe_payment_method_id,
                off_session=True,
                confirm=True,
                description=f"Traffic fine for booking {self.booking.id}",
                metadata={
                    'booking_id': str(self.booking.id),
                    'reason': self.reason,
                    'type': 'fine'
                },
                api_key=settings.STRIPE_SECRET_KEY
            )
            
            if payment_intent.status == 'requires_action':
                raise ValueError("Customer authentication is required - please ask customer to authenticate")
                
            if payment_intent.status != 'succeeded':
                raise ValueError(f"Payment processing failed with status: {payment_intent.status}")
            
            # Create Payment record
            fine_payment = Payment.objects.create(
                booking=self.booking,
                stripe_payment_intent_id=payment_intent.id,
                stripe_payment_method_id=payment.stripe_payment_method_id,
                stripe_customer_id=payment.stripe_customer_id,
                amount=float(self.amount),
                status=payment_intent.status,
                payment_type='fine',
                payment_method_type=payment.payment_method_type,
                payment_method_brand=payment.payment_method_brand,
                payment_method_last4=payment.payment_method_last4
            )
            
            self.charged_payment = fine_payment
            self.save()
            
            # Send notification
            self.send_fine_notification()
            
            return fine_payment
            
        except stripe.error.CardError as e:
            error_msg = f"Card error: {e.user_message}" if e.user_message else str(e)
            raise ValueError(error_msg)
        except stripe.error.StripeError as e:
            raise ValueError(f"Stripe error: {str(e)}")
        except Exception as e:
            raise ValueError(f"Error: {str(e)}")
        
        
        
    def send_fine_notification(self):
        """Send traffic fine notification using Brevo"""
        guest = self.booking.guest
        subject = f"Traffic Fine Notification for Booking {self.booking.id}"

        html_content = f"""
        <html>
            <body>
                <h2>Dear {guest.first_name} {guest.last_name},</h2>
                
                <p>We would like to inform you that a traffic fine has been charged to your payment method on file.</p>
                
                <h3>Fine Details:</h3>
                <ul>
                    <li><strong>Booking Reference:</strong> {self.booking.id}</li>
                    <li><strong>Amount:</strong> €{self.amount}</li>
                    <li><strong>Reason:</strong> {self.reason}</li>
                    <li><strong>Date Charged:</strong> {self.charged_payment.created_at.strftime('%Y-%m-%d %H:%M')}</li>
                </ul>
                
                <p>Please find the traffic violation documentation attached in your booking dashboard or contact support for further information.</p>
                
                <p>If you believe this is an error or have any questions, please contact our support team within 7 days.</p>
                
                <p>Best regards,<br><strong>The Car Rental Service Team</strong></p>
            </body>
        </html>
        """

        # Send the email using Brevo
        try:
            email_client = Email()
            email_client._send_email_via_brevo(
                subject=subject,
                html_content=html_content.strip(),
                recipient_list=[guest.email]
            )
        except Exception as e:
            raise ValueError(f"Error sending fine notification via Brevo: {str(e)}")