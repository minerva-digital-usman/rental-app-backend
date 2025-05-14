from datetime import timedelta
from pyexpat.errors import messages
from django.conf import settings
from middleware_platform.settings import BREVO_API_KEY, DEFAULT_FROM_EMAIL, DEFAULT_FROM_NAME, ADMIN_EMAIL
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException

class Email:
    def __init__(self):
        # Configure API key
        self.configuration = sib_api_v3_sdk.Configuration()
        self.configuration.api_key['api-key'] = BREVO_API_KEY
    
    def _send_email_via_brevo(self, subject, html_content, recipient_list, sender_name=None, sender_email=None):
        """
        Internal method to send email using Brevo API
        """
        api_instance = sib_api_v3_sdk.TransactionalEmailsApi(
            sib_api_v3_sdk.ApiClient(self.configuration)
        )
        
        sender_name = sender_name or DEFAULT_FROM_NAME
        sender_email = sender_email or DEFAULT_FROM_EMAIL
        
        sender = {"name": sender_name, "email": sender_email}
        to = [{"email": email} for email in recipient_list]
        
        send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
            sender=sender,
            to=to,
            html_content=html_content,
            subject=subject
        )
        
        try:
            api_response = api_instance.send_transac_email(send_smtp_email)
            return api_response
        except ApiException as e:
            print(f"Exception when calling SMTPApi->send_transac_email: {e}\n")
            return None
        
    def send_booking_confirmation_email(self, metadata):
        """Send booking confirmation email via Brevo"""
        subject = f"Booking Confirmation: {metadata.get('company_name', 'Our Car Rental Service')} - Reference #{metadata.get('booking_id', '')}"

        html_content = f"""
        <html>
            <body>
                <h2>Dear {metadata.get('guest_first_name', 'Valued Customer')} {metadata.get('guest_last_name', '')},</h2>
                
                <p>We are delighted to confirm your reservation with <strong>{metadata.get('company_name', 'Our Premium Car Rental Service')}</strong>.</p>
                <p>Your booking has been successfully processed, and we look forward to serving you.</p>
                
                <h3>Booking Summary:</h3>
                <table style="border-collapse: collapse; width: 100%;">
                    <tr><td><strong>Booking Reference:</strong></td><td>{metadata.get('booking_id', 'N/A')}</td></tr>
                    <tr><td><strong>Vehicle Pickup:</strong></td><td>{metadata.get('pickup_date', '')} at {metadata.get('pickup_time', '')}</td></tr>
                    <tr><td><strong>Vehicle Return:</strong></td><td>{metadata.get('return_date', '')} at {metadata.get('return_time', '')}</td></tr>
                    <tr><td><strong>Total Amount:</strong></td><td>€{metadata.get('amount', 'N/A')}</td></tr>
                </table>

                <p>We appreciate your trust in our services and wish you pleasant travels.</p>

                <p>Warm regards,<br><strong>{metadata.get('company_name', 'The Car Rental Service')}</strong> Team</p>
            </body>
        </html>
        """

        recipient = metadata.get('guest_email')

        if recipient:
            return self._send_email_via_brevo(
                subject=subject,
                html_content=html_content.strip(),
                recipient_list=[recipient]
            )

    def send_extension_email(self, booking, new_end_time):
        """Send email notification regarding the booking extension."""
        subject = f"Booking Extension Confirmation: {booking.vehicle.model}"

        html_content = f"""
        <html>
            <body>
                <h1>Dear {booking.guest.first_name} {booking.guest.last_name},</h1>
                
                <p>We are pleased to confirm that your booking extension has been successfully processed with Our Premium Car Rental Service.</p>
                <p>We are happy to continue providing you with our services.</p>
                
                <h3>Extended Booking Summary:</h3>
                <hr>
                <ul>
                    <li><strong>Booking Reference:</strong> {booking.id}</li>
                    <li><strong>New Vehicle Return:</strong> {new_end_time.strftime('%B %d, %Y %H:%M')}</li>
                </ul>
                <hr>
                
                <p>We thank you for your continued trust in our services and wish you safe travels.</p>
                
                <p>Warm regards,<br>The Booking Team</p>
            </body>
        </html>
        """

        return self._send_email_via_brevo(
            subject=subject,
            html_content=html_content,
            recipient_list=[booking.guest.email]
        )

    def send_pending_conflict_email(self, pending_booking, extending_booking, new_end_time):
        """Send email notification regarding pending conflict status."""
        subject = f"Booking Status Update: {pending_booking.vehicle.model} - Pending Confirmation"
        pending_actual_end_time = pending_booking.end_time - timedelta(minutes=pending_booking.buffer_time)
        
        html_content = f"""
        <html>
            <body>
                <h1>Dear {pending_booking.guest.first_name} {pending_booking.guest.last_name},</h1>
                
                <p>We would like to inform you that your booking for the {pending_booking.vehicle.model}, originally scheduled from 
                {pending_booking.start_time.strftime('%B %d, %Y %H:%M')} to 
                {pending_actual_end_time.strftime('%B %d, %Y %H:%M')}, is currently marked as <strong>pending confirmation</strong> due to a scheduling conflict.</p>
                
                <p>A higher-priority booking has been extended and is now scheduled to occupy the vehicle until 
                {new_end_time.strftime('%B %d, %Y %H:%M')}. As a result, we are reviewing availability and will update you as soon as possible.</p>
                
                <p>We sincerely apologize for any inconvenience this may cause. If you wish to modify your reservation or explore alternate options, please don't hesitate to reach out.</p>
                
                <p>Thank you for your patience and understanding.</p>
                
                <p>Best regards,<br>The Booking Team</p>
            </body>
        </html>
        """

        return self._send_email_via_brevo(
            subject=subject,
            html_content=html_content,
            recipient_list=[pending_booking.guest.email]
        )

    
    def send_cancellation_email(self, request, booking, new_end_time=None):
        """Send cancellation email using Brevo when booking is cancelled."""
        try:
            booking.refresh_from_db()

            subject = f"Booking Cancellation Notification: {booking.vehicle.model}"

            html_content = f"""
            <html>
                <body>
                    <h1>Dear {booking.guest.first_name} {booking.guest.last_name},</h1>

                    <p>We regret to inform you that your booking for the <strong>{booking.vehicle.model}</strong>, originally scheduled from 
                    {booking.start_time.strftime('%B %d, %Y %H:%M')} to 
                    {booking.end_time.strftime('%B %d, %Y %H:%M')}, has been cancelled due to a conflict resolution.</p>
                    
                    {"<p>The vehicle will now remain in use until " + new_end_time.strftime('%B %d, %Y %H:%M') + ".</p>" if new_end_time else ""}
                    
                    <p>Please note that your payment will be refunded within 7 business days.</p>

                    <p>If you have any questions or need assistance with rebooking, feel free to reach out to us.</p>

                    <p>We sincerely apologize for the inconvenience and appreciate your understanding.</p>

                    <p>Best regards,<br>The Booking Team</p>
                </body>
            </html>
            """

            # Send using Brevo
            email_response = self._send_email_via_brevo(
                subject=subject,
                html_content=html_content.strip(),
                recipient_list=[booking.guest.email]
            )

            # Django Admin success message
            self.message_user(
                request,
                f"Booking {booking.id} cancelled and email sent to {booking.guest.email}"
            )
            return email_response

        except Exception as e:
            # Django Admin error message
            self.message_user(
                request,
                f"Failed to send email for booking {booking.id}: {str(e)}",
                level=messages.ERROR
            )
            return None

    def notify_admin_of_pending_conflict(self, pending_booking, extending_booking, new_end_time):
        """Send an email to admin when a booking is marked as pending_conflict."""
        subject = f"[Alert] Booking Conflict - {pending_booking.vehicle.model} marked as PENDING"
        
        html_content = f"""
        <html>
            <body>
                <h1>Admin Alert</h1>
                
                <p>A booking conflict has been detected and the affected booking has been marked as <strong>pending_conflict</strong>.</p>
                
                <h3>▶ Affected Booking (now pending):</h3>
                <ul>
                    <li><strong>Booking ID:</strong> {pending_booking.id}</li>
                    <li><strong>Guest:</strong> {pending_booking.guest.first_name} {pending_booking.guest.last_name}</li>
                    <li><strong>Email:</strong> {pending_booking.guest.email}</li>
                    <li><strong>Time:</strong> {pending_booking.start_time.strftime('%Y-%m-%d %H:%M')} to {pending_booking.end_time.strftime('%Y-%m-%d %H:%M')}</li>
                </ul>
                
                <h3>▶ Conflicting Extension:</h3>
                <ul>
                    <li><strong>Booking ID:</strong> {extending_booking.id}</li>
                    <li><strong>Guest:</strong> {extending_booking.guest.first_name} {extending_booking.guest.last_name}</li>
                    <li><strong>Vehicle:</strong> {extending_booking.vehicle.model}</li>
                    <li><strong>New End Time:</strong> {new_end_time.strftime('%Y-%m-%d %H:%M')}</li>
                </ul>
                
                <p>Please review this conflict and take necessary action if needed.</p>
                
                <p>– Booking System</p>
            </body>
        </html>
        """

        return self._send_email_via_brevo(
            subject=subject,
            html_content=html_content,
            recipient_list=[ADMIN_EMAIL]
        )

    def send_conflict_resolved_email(self, booking):
        """Send email when a booking conflict has been resolved."""
        subject = "Your Booking Conflict Has Been Resolved"
        
        html_content = f"""
        <html>
            <body>
                <h1>Dear {booking.guest.first_name},</h1>
                
                <p>Good news! Your booking conflict has been resolved.</p>
                
                <h3>Booking Details:</h3>
                <ul>
                    <li><strong>Hotel:</strong> {booking.hotel.name}</li>
                    <li><strong>Address:</strong> {booking.hotel.location}</li>
                    <li><strong>Car:</strong> {booking.vehicle.model} ({booking.vehicle.plate_number})</li>
                    <li><strong>Booking time:</strong> {booking.start_time.strftime('%Y-%m-%d %H:%M')} to {booking.end_time.strftime('%Y-%m-%d %H:%M')}</li>
                </ul>
                
                <p>If you have any questions, please contact support.</p>
                
                <p>Thank you,<br>The Support Team</p>
            </body>
        </html>
        """

        return self._send_email_via_brevo(
            subject=subject,
            html_content=html_content,
            recipient_list=[booking.guest.email]
        )