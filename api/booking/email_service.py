from datetime import timedelta
from pyexpat.errors import messages
from django.conf import settings
from middleware_platform.settings import BREVO_API_KEY, DEFAULT_FROM_EMAIL, DEFAULT_FROM_NAME, ADMIN_EMAIL
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException

from api.rental_company.utils.email_config import get_admin_email
from api.rental_company.models import RentalCompany
rental_company = RentalCompany.objects.first()

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
    
    def send_admin_booking_cancellation_email(self, metadata):
        """Notify admin team of a cancelled booking via Brevo"""

        subject = f"Admin Notification: Booking Cancelled – Ref #{metadata.get('booking_id', '')}"

        html_content = f"""
        <html>
            <body>
                <p>Dear {metadata.get('company_name')},</p>

                <p>This is to inform you that the following reservation has been <strong>cancelled</strong> by the customer.</p>

                <h3>Cancelled Booking Details</h3>
                <table style="border-collapse: collapse; width: 100%;">
                    <tr><td><strong>Booking Reference:</strong></td><td>{metadata.get('booking_id', 'N/A')}</td></tr>
                    <tr><td><strong>Customer:</strong></td><td>{metadata.get('guest_first_name', '')} {metadata.get('guest_last_name', '')}</td></tr>
                    <tr><td><strong>Email:</strong></td><td>{metadata.get('guest_email', 'N/A')}</td></tr>
                    <tr><td><strong>Phone:</strong></td><td>{metadata.get('guest_phone', 'N/A')}</td></tr>
                    <tr><td><strong>Address:</strong></td><td>{metadata.get('guest_address', '')}</td></tr>
                    <tr><td><strong>Hotel:</strong></td><td>{metadata.get('hotel_location', 'N/A')}</td></tr>
                    <tr><td><strong>Vehicle:</strong></td><td>{metadata.get('car_model', 'N/A')}</td></tr>
                    <tr><td><strong>Pickup:</strong></td><td>{metadata.get('pickup_date', '')} at {metadata.get('pickup_time', '')}</td></tr>
                    <tr><td><strong>Return:</strong></td><td>{metadata.get('return_date', '')} at {metadata.get('return_time', '')}</td></tr>
                    <tr><td><strong>Total Amount:</strong></td><td>CHF {metadata.get('amount_paid', 'N/A')}</td></tr>
                </table>


                <p>Please ensure all associated systems are updated accordingly.</p>

                <p>Best regards,<br>
                <strong>{metadata.get('company_name', 'Cora Mobility')}</strong></p>
                <p>Phone: {metadata.get('company_phone', '')}<br>
                E-mail: {metadata.get('company_email', '')}</p>
            </body>
        </html>
        """

        admin_email = metadata.get('company_email')
        if admin_email:
            return self._send_email_via_brevo(
                subject=subject,
                html_content=html_content.strip(),
                recipient_list=[admin_email]
            )

    def send_booking_cancellation_email(self, metadata):
        """Send booking cancellation confirmation email via Brevo"""

        subject = f"Booking Cancellation Confirmation – Reference #{metadata.get('booking_id', '')}"

        html_content = f"""
        <html>
            <body>
                <p>Dear {metadata.get('guest_first_name', 'Valued Customer')} {metadata.get('guest_last_name', '')},</p>

                <p>We confirm that your reservation with <strong>{metadata.get('company_name', 'Cora Mobility')}</strong> has been successfully cancelled.</p>

                <p>We regret that we won’t have the opportunity to welcome you on board this time, but we hope to assist you again soon.</p>

                <h3>Cancelled Booking Details</h3>
                <table style="border-collapse: collapse; width: 100%;">
                    <tr><td><strong>Booking Reference:</strong></td><td>{metadata.get('booking_id', 'N/A')}</td></tr>
                    <tr><td><strong>Driver:</strong></td><td>{metadata.get('guest_first_name', '')} {metadata.get('guest_last_name', '')}, {metadata.get('guest_address', '')}</td></tr>
                    <tr><td><strong>Vehicle:</strong></td><td>{metadata.get('car_model', 'N/A')}</td></tr>
                    <tr><td><strong>Original Pickup:</strong></td><td>{metadata.get('pickup_date', '')} at {metadata.get('pickup_time', '')} – {metadata.get('hotel_location', '')}</td></tr>
                    <tr><td><strong>Original Return:</strong></td><td>{metadata.get('return_date', '')} at {metadata.get('return_time', '')} – {metadata.get('hotel_location', '')}</td></tr>
                    <tr><td><strong>Total Amount:</strong></td><td>CHF {metadata.get('amount_paid', 'N/A')}</td></tr>
                </table>

                <p>As acknowledged in the General Terms and Conditions at booking, you may cancel your reservation any time before the rental start. Refunds will be issued based on the timing of your cancellation:</p>
                
                <ul>
                    <li>More than 96 hours before rental start: Full refund.</li>
                    <li>Between 48 and 96 hours before rental start: 50% refund.</li>
                    <li>Less than 48 hours before rental start or in case of no-show: No refund.</li>
                </ul>

                <p>Please note that refunds may take up to 5 business days to process, depending on your payment provider.</p>

                <p>We thank you for choosing <strong>{metadata.get('company_name', 'Cora Mobility')}</strong> and remain at your disposal for any future requests.</p>

                <p>We look forward to serving you again.</p>

                <p>Warm regards,<br>
                <strong>{metadata.get('company_name', '')}</strong><br>
                Phone: {metadata.get('company_phone', '')}<br>
                
                E-mail: {metadata.get('company_email', '')}<br>
                </p>
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
            
            
            
    def send_hotel_notification_on_booking_cancellation_email(self, metadata):
        """Send hotel a notification email when a guest's car booking is cancelled"""

        subject = f"Notification: Guest Car Booking Cancellation – Ref #{metadata.get('booking_id', '')}"

        html_content = f"""
        <html>
            <body>
                <p>Dear Team at {metadata.get('hotel_name', 'N/A')},</p>

                <p>We would like to inform you that the following car booking, originally made by a guest staying at your property, has been <strong>cancelled</strong>.</p>

                <h3>Cancelled Booking Details</h3>
                <table style="border-collapse: collapse; width: 100%;">
                    <tr><td><strong>Booking Reference:</strong></td><td>{metadata.get('booking_id', 'N/A')}</td></tr>
                    <tr><td><strong>Guest Name:</strong></td><td>{metadata.get('guest_first_name', '')} {metadata.get('guest_last_name', '')}</td></tr>
                    <tr><td><strong>Guest Address:</strong></td><td>{metadata.get('guest_address', 'N/A')}</td></tr>
                    <tr><td><strong>Vehicle:</strong></td><td>{metadata.get('car_model', 'N/A')}</td></tr>
                    <tr><td><strong>Original Pickup:</strong></td><td>{metadata.get('pickup_date', '')} at {metadata.get('pickup_time', '')}</td></tr>
                    <tr><td><strong>Original Return:</strong></td><td>{metadata.get('return_date', '')} at {metadata.get('return_time', '')}</td></tr>
                    <tr><td><strong>Total Amount:</strong></td><td>CHF {metadata.get('amount_paid', 'N/A')}</td></tr>
                </table>

                <p>This is for your records only. No further action is required on your part.</p>

                <p>We appreciate your continued collaboration and look forward to serving your guests in the future.</p>

                <p>Best regards,<br>
                <strong>{metadata.get('company_name', 'Cora Mobility')}</strong><br>
                Phone: {metadata.get('company_phone', '')}<br>
                E-mail: {metadata.get('company_email', '')}<br>
                </p>
            </body>
        </html>
        """

        hotel_email = metadata.get('hotel_email')
        if hotel_email:
            return self._send_email_via_brevo(
                subject=subject,
                html_content=html_content.strip(),
                recipient_list=[hotel_email]
            )

    
    def send_booking_confirmation_email_to_hotel(self, metadata):
        """Send booking confirmation email to hotel via Brevo"""

        subject = f"Guest Car Booking Confirmation - Reference #{metadata.get('booking_id', '')}"

        html_content = f"""
        <html>
            <body>
                <p>Dear Hotel Staff,</p>

                <p>We are pleased to inform you that the guest <strong>{metadata.get('guest_first_name', '')} {metadata.get('guest_last_name', '')}</strong> has booked a vehicle through <strong>{metadata.get('company_name', 'Cora Mobility')}</strong>'s exclusive car sharing service.</p>

                <p>Please kindly hand over the car keys at the hotel desk upon presentation of this confirmation.</p>

                <p><em>This message also serves as part of the rental agreement between the guest and {metadata.get('company_name', '')}.</em></p>

                <h3>Rental Agreement Details</h3>
                <table style="border-collapse: collapse; width: 100%;">
                    <tr><td><strong>Booking Reference:</strong></td><td>{metadata.get('booking_id', 'N/A')}</td></tr>
                    <tr><td><strong>Guest Name:</strong></td><td>{metadata.get('guest_first_name', '')} {metadata.get('guest_last_name', '')}</td></tr>
                    <tr><td><strong>Guest Address:</strong></td><td>{metadata.get('guest_street_address', '')}</td></tr>
                    <tr><td><strong>Vehicle:</strong></td><td>{metadata.get('car_model', 'N/A')}</td></tr>
                    <tr><td><strong>Pickup:</strong></td><td>{metadata.get('pickup_date', '')} at {metadata.get('pickup_time', '')} – {metadata.get('hotel_location', '')}</td></tr>
                    <tr><td><strong>Return:</strong></td><td>{metadata.get('return_date', '')} at {metadata.get('return_time', '')} – {metadata.get('hotel_location', '')}</td></tr>
                    <tr><td><strong>Total Amount (Guest Paid):</strong></td><td>CHF {metadata.get('amount', 'N/A')}</td></tr>
                </table>

               
                <p>General rental terms and conditions apply: 
                <a href="{metadata.get('terms_url', '#')}">View Terms and Conditions</a></p>

                <p>We thank you for choosing <strong>{metadata.get('company_name', 'Cora Mobility')}</strong> and wish you a good day.</p>

                <p>Warm regards,<br>
                <strong>{metadata.get('company_name', '')}</strong><br>
                Phone: {metadata.get('company_phone', '')}<br>
                
                E-mail: {metadata.get('company_email', '')}<br>
                </p>
            </body>
        </html>
        """

        hotel_email = metadata.get('hotel_email')
        if hotel_email:
            return self._send_email_via_brevo(
                subject=subject,
                html_content=html_content.strip(),
                recipient_list=[hotel_email]
            )

    
    
    
    
    
    
    
    def send_booking_confirmation_email(self, metadata):
        """Send booking confirmation email via Brevo"""

        subject = f"Booking Confirmation: {metadata.get('company_name', 'Cora Mobility')} - Reference #{metadata.get('booking_id', '')}"

        html_content = f"""
        <html>
            <body>
                <p>Dear {metadata.get('guest_first_name', 'Valued Customer')} {metadata.get('guest_last_name', '')},</p>
                
                <p>Welcome to the exclusive car sharing service of <strong>{metadata.get('company_name', 'Cora Mobility')}</strong>. We are pleased to confirm your booking and provide you with a convenient and elegant way to explore our region.</p>
                
                <p>You will find and receive your car keys comfortably at the hotel desk by showing this confirmation.</p>
                
                <p><em>This message constitutes your rental agreement. By making use of the vehicle, you agree to the applicable rental conditions.</em></p>
                
                <h3>Rental Agreement Details</h3>
                <table style="border-collapse: collapse; width: 100%;">
                    <tr><td><strong>Booking Reference:</strong></td><td>{metadata.get('booking_id', 'N/A')}</td></tr>
                    <tr><td><strong>Driver:</strong></td><td>{metadata.get('guest_first_name', '')} {metadata.get('guest_last_name', '')}, {metadata.get('guest_street_address', '')}</td></tr>
                    <tr><td><strong>Vehicle:</strong></td><td>{metadata.get('car_model', 'N/A')}</td></tr>
                    <tr><td><strong>Pickup:</strong></td><td>{metadata.get('pickup_date', '')} at {metadata.get('pickup_time', '')} – {metadata.get('hotel_location', '')}</td></tr>
                    <tr><td><strong>Return:</strong></td><td>{metadata.get('return_date', '')} at {metadata.get('return_time', '')} – {metadata.get('hotel_location', '')}</td></tr>
                    <tr><td><strong>Total Amount:</strong></td><td>CHF {metadata.get('amount', 'N/A')}</td></tr>
                </table>

                <p>Should you wish to extend or delete your booking, you can do so easily here: 
                <a href="{metadata.get('extension_link', '#')}">Booking Details</a>.</p>

                <p>General rental terms and conditions apply: 
                <a href="{metadata.get('terms_url', '#')}">View Terms and Conditions</a></p>

                <p>We thank you for choosing <strong>{metadata.get('company_name', 'Cora Mobility')}</strong> and wish you a smooth and pleasant journey.</p>

                <p>Warm regards,<br>
                <strong>{metadata.get('company_name', '')}</strong><br>
                Phone: {metadata.get('company_phone', '')}<br>
                
                E-mail: {metadata.get('company_email', '')}<br>
                </p>

                <hr>
                <p><small>
                *As acknowledged in the General Terms and Conditions at booking, you may cancel your reservation any time before the rental start. Refunds will be issued based on the timing of your cancellation:<br><br>
                • More than 96 hours before rental start: Full refund.<br>
                • Between 48 and 96 hours before rental start: 50% refund.<br>
                • Less than 48 hours before rental start or in case of no-show: No refund.<br><br>
                Please note that refunds may take up to 5 business days to process, depending on your payment provider.
                </small></p>
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


    from django.conf import settings

    def send_booking_notification_to_admin(self, metadata):
        """Send booking confirmation notification email to admin via Brevo"""

        subject = f"New Guest Booking – Reference #{metadata.get('booking_id', '')}"

        html_content = f"""
        <html>
            <body>
                <p>Dear Admin,</p>

                <p>A new car booking has been confirmed through <strong>{metadata.get('company_name', 'Cora Mobility')}</strong>.</p>

                <h3>Rental Agreement Details</h3>
                <table style="border-collapse: collapse; width: 100%;">
                    <tr><td><strong>Booking Reference:</strong></td><td>{metadata.get('booking_id', 'N/A')}</td></tr>
                    <tr><td><strong>Guest Name:</strong></td><td>{metadata.get('guest_first_name', '')} {metadata.get('guest_last_name', '')}</td></tr>
                    <tr><td><strong>Guest Address:</strong></td><td>{metadata.get('guest_street_address', 'N/A')}</td></tr>
                    <tr><td><strong>Guest Email:</strong></td><td>{metadata.get('guest_email', 'N/A')}</td></tr>
                    <tr><td><strong>Vehicle:</strong></td><td>{metadata.get('car_model', 'N/A')}</td></tr>
                    <tr><td><strong>Pickup:</strong></td><td>{metadata.get('pickup_date', '')} at {metadata.get('pickup_time', '')} – {metadata.get('hotel_location', '')}</td></tr>
                    <tr><td><strong>Return:</strong></td><td>{metadata.get('return_date', '')} at {metadata.get('return_time', '')} – {metadata.get('hotel_location', '')}</td></tr>
                    <tr><td><strong>Total Amount:</strong></td><td>CHF {metadata.get('amount', 'N/A')}</td></tr>
                </table>

                <p>Rental terms: <a href="{metadata.get('terms_url', '#')}">View Terms and Conditions</a></p>

                <p>Warm regards,<br>
                <strong>{metadata.get('company_name', 'Cora Mobility')}</strong><br>
                Phone: {metadata.get('company_phone', '')}<br>
                Email: {metadata.get('company_email', '')}<br>
                </p>
            </body>
        </html>
        """

        admin_email = get_admin_email()
       

        recipient_list = [admin_email]

        return self._send_email_via_brevo(
            subject=subject,
            html_content=html_content.strip(),
            recipient_list=recipient_list
        )
        
        
        
        
        
        
        
    def send_extension_email(self, metadata, new_end_time):
        """Send booking extension confirmation email via Brevo"""

        subject = f"Booking Extension Confirmation: {metadata.get('company_name', 'Cora Mobility')} - Reference #{metadata.get('booking_id', '')}"

        html_content = f"""
        <html>
            <body>
                <p>Dear {metadata.get('guest_first_name', 'Valued Customer')} {metadata.get('guest_last_name', '')},</p>

                <p>We are pleased to confirm your booking extension with <strong>{metadata.get('company_name', 'Cora Mobility')}</strong>. Thank you for continuing to trust us for your mobility needs.</p>

                <p>Your updated booking details are as follows:</p>

                <h3>Updated Rental Agreement Details</h3>
                <table style="border-collapse: collapse; width: 100%;">
                    <tr><td><strong>Booking Reference:</strong></td><td>{metadata.get('booking_id', 'N/A')}</td></tr>
                    <tr><td><strong>Driver:</strong></td><td>{metadata.get('guest_first_name', '')} {metadata.get('guest_last_name', '')}, {metadata.get('guest_street_address', '')}</td></tr>
                    <tr><td><strong>Vehicle:</strong></td><td>{metadata.get('car_model', 'N/A')}</td></tr>
                    <tr><td><strong>Original Return:</strong></td><td>{metadata.get('original_return_date', '')} at {metadata.get('original_return_time', '')} – {metadata.get('hotel_location', '')}</td></tr>
                    <tr><td><strong>New Return:</strong></td><td>{new_end_time.strftime('%B %d, %Y at %H:%M')}</td></tr>
                    <tr><td><strong>Total Amount:</strong></td><td>CHF {metadata.get('amount', 'N/A')}</td></tr>
                </table>

                <p>You can review your updated booking or make further changes here: 
                <a href="{metadata.get('extension_link', '#')}">Booking Details</a>.</p>

                <p>For your reference, the general rental terms and conditions remain applicable: 
                <a href="{metadata.get('terms_url', '#')}">View Terms and Conditions</a></p>

                <p>Thank you once again for choosing <strong>{metadata.get('company_name', 'Cora Mobility')}</strong>. We wish you safe and pleasant travels.</p>

                <p>Warm regards,<br>
                <strong>{metadata.get('company_name', '')}</strong><br>
                Phone: {metadata.get('company_phone', '')}<br>
                E-mail: {metadata.get('company_email', '')}<br>
                </p>

                <hr>
                <p><small>
                *As acknowledged in the General Terms and Conditions at booking, you may cancel your reservation any time before the rental start. Refunds will be issued based on the timing of your cancellation:<br><br>
                • More than 96 hours before rental start: Full refund.<br>
                • Between 48 and 96 hours before rental start: 50% refund.<br>
                • Less than 48 hours before rental start or in case of no-show: No refund.<br><br>
                Please note that refunds may take up to 5 business days to process, depending on your payment provider.
                </small></p>
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
            
    def send_extension_email_to_hotel(self, metadata, new_end_time):
        """Send booking extension notification email to the hotel via Brevo"""

        subject = f"Booking Extension Notification: Guest #{metadata.get('guest_first_name', '')} {metadata.get('guest_last_name', '')} – Ref #{metadata.get('booking_id', '')}"

        html_content = f"""
        <html>
            <body>
                <p>Dear {metadata.get('hotel_name')} ({metadata.get('hotel_location', 'Hotel')}),</p>

                <p>This is to inform you that a guest associated with your hotel has extended their vehicle booking.</p>

                <h3>Guest Booking Extension Details</h3>
                <table style="border-collapse: collapse; width: 100%;">
                    <tr><td><strong>Booking Reference:</strong></td><td>{metadata.get('booking_id', 'N/A')}</td></tr>
                    <tr><td><strong>Guest:</strong></td><td>{metadata.get('guest_first_name', '')} {metadata.get('guest_last_name', '')}</td></tr>
                    <tr><td><strong>Guest Contact:</strong></td><td>Email: {metadata.get('guest_email', 'N/A')} | Phone: {metadata.get('guest_phone', 'N/A')}</td></tr>
                    <tr><td><strong>Vehicle:</strong></td><td>{metadata.get('car_model', 'N/A')}</td></tr>
                    <tr><td><strong>Original Return:</strong></td><td>{metadata.get('original_return_date', '')} at {metadata.get('original_return_time', '')}</td></tr>
                    <tr><td><strong>New Return:</strong></td><td>{new_end_time.strftime('%B %d, %Y at %H:%M')}</td></tr>
                    <tr><td><strong>Total Amount Charged:</strong></td><td>CHF {metadata.get('amount', 'N/A')}</td></tr>
                </table>

                <p>Please ensure your team is informed of the updated return time and date. Thank you for your continued partnership.</p>

                <p>Best regards,<br>
                <strong>{metadata.get('company_name', 'Cora Mobility')}</strong><br>
                Phone: {metadata.get('company_phone', '')}<br>
                Email: {metadata.get('company_email', '')}</p>

                <hr>
                <p><small>This is an automated notification. Please do not reply to this email.</small></p>
            </body>
        </html>
        """

        hotel_email = metadata.get('hotel_email')
        if hotel_email:
            return self._send_email_via_brevo(
                subject=subject,
                html_content=html_content.strip(),
                recipient_list=[hotel_email]
            )

    def send_extension_email_to_admin(self, metadata, new_end_time):
        """Send booking extension notification email to admin via Brevo"""

        subject = f"[ADMIN NOTICE] Booking Extension – Ref #{metadata.get('booking_id', '')} – Guest {metadata.get('guest_first_name', '')} {metadata.get('guest_last_name', '')}"

        html_content = f"""
        <html>
            <body>
                <p>Dear Admin,</p>

                <p>A guest has extended their booking. Please find the full details below for your records.</p>

                <h3>Extended Booking Summary</h3>
                <table style="border-collapse: collapse; width: 100%;">
                    <tr><td><strong>Booking Reference:</strong></td><td>{metadata.get('booking_id', 'N/A')}</td></tr>
                    <tr><td><strong>Hotel:</strong></td><td>{metadata.get('hotel_location', '')}</td></tr>
                    <tr><td><strong>Hotel Email:</strong></td><td>{metadata.get('hotel_email', 'N/A')}</td></tr>
                    <tr><td><strong>Vehicle:</strong></td><td>{metadata.get('car_model', 'N/A')}</td></tr>
                    <tr><td><strong>Guest Name:</strong></td><td>{metadata.get('guest_first_name', '')} {metadata.get('guest_last_name', '')}</td></tr>
                    <tr><td><strong>Guest Contact:</strong></td><td>Email: {metadata.get('guest_email', 'N/A')} | Phone: {metadata.get('guest_phone', 'N/A')}</td></tr>
                    <tr><td><strong>Guest Address:</strong></td><td>{metadata.get('guest_street_address', '')}, {metadata.get('guest_postal_code', '')} {metadata.get('guest_city', '')}</td></tr>
                    <tr><td><strong>Original Return:</strong></td><td>{metadata.get('original_return_date', '')} at {metadata.get('original_return_time', '')}</td></tr>
                    <tr><td><strong>New Return:</strong></td><td>{new_end_time.strftime('%B %d, %Y at %H:%M')}</td></tr>
                      <tr><td><strong>Total Charged:</strong></td><td>CHF {metadata.get('amount', 'N/A')}</td></tr>
                </table>

                <p>You can review the booking details or forward this to the hotel partner if needed.</p>

                <p>For reference, the guest agreed to our rental terms and conditions: 
                <a href="{metadata.get('terms_url', '#')}">View Terms and Conditions</a></p>

                <p>Regards,<br>
                <strong>{metadata.get('company_name', 'Cora Mobility')} Operations</strong><br>
                Email: {metadata.get('company_email', '')}<br>
                Phone: {metadata.get('company_phone', '')}</p>

                <hr>
                <p><small>This is an internal administrative alert. No user action is required unless otherwise indicated.</small></p>
            </body>
        </html>
        """

        admin_email = get_admin_email()  # You can hardcode or fetch from config
        if admin_email:
            return self._send_email_via_brevo(
                subject=subject,
                html_content=html_content.strip(),
                recipient_list=[admin_email]
            )



    def send_extension_notification_to_admin_and_hotel(self, meta):
        """Send booking extension notification email to admin and hotel using metadata."""

        subject = f"Booking Extension Alert: Reference #{meta.get('booking_id')}"

        new_return_time_str = f"{meta.get('return_date')} {meta.get('return_time')}"  # String format

        html_content = f"""
        <html>
            <body>
                <h2>Booking Extension Notification</h2>

                <p>A booking has been extended on <strong>Vehicle ID: {meta.get('vehicle_id')}</strong>.</p>

                <h3>Extension Details:</h3>
                <table style="border-collapse: collapse; width: 100%;">
                    <tr><td><strong>Booking Reference:</strong></td><td>{meta.get('booking_id')}</td></tr>
                    <tr><td><strong>Guest Name:</strong></td><td>{meta.get('guest_first_name')} {meta.get('guest_last_name')}</td></tr>
                    <tr><td><strong>Guest Email:</strong></td><td>{meta.get('guest_email')}</td></tr>
                    <tr><td><strong>New Return Time:</strong></td><td>{new_return_time_str}</td></tr>
                    <tr><td><strong>Vehicle ID:</strong></td><td>{meta.get('vehicle_id')}</td></tr>
                </table>

                <p>Please review and update your records accordingly.</p>

                <p>Best regards,<br><strong>Booking System</strong></p>
            </body>
        </html>
        """

        recipient_list = []

        admin_email = get_admin_email()
        if admin_email:
            recipient_list.append(admin_email)

        hotel_email = meta.get('hotel_email')
        if hotel_email:
            recipient_list.append(hotel_email)

        return self._send_email_via_brevo(
            subject=subject,
            html_content=html_content.strip(),
            recipient_list=recipient_list
        )



    # def send_extension_email(self, booking, new_end_time):
    #     """Send email notification regarding the booking extension."""
    #     subject = f"Booking Extension Confirmation: {booking.vehicle.model}"

    #     html_content = f"""
    #     <html>
    #         <body>
    #             <h1>Dear {booking.guest.first_name} {booking.guest.last_name},</h1>
                
    #             <p>We are pleased to confirm that your booking extension has been successfully processed with Our Premium Car Rental Service.</p>
    #             <p>We are happy to continue providing you with our services.</p>
                
    #             <h3>Extended Booking Summary:</h3>
    #             <hr>
    #             <ul>
    #                 <li><strong>Booking Reference:</strong> {booking.id}</li>
    #                 <li><strong>New Vehicle Return:</strong> {new_end_time.strftime('%B %d, %Y %H:%M')}</li>
    #             </ul>
    #             <hr>
                
    #             <p>We thank you for your continued trust in our services and wish you safe travels.</p>
                
    #             <p>Warm regards,<br>The Booking Team</p>
    #         </body>
    #     </html>
    #     """

    #     return self._send_email_via_brevo(
    #         subject=subject,
    #         html_content=html_content,
    #         recipient_list=[booking.guest.email]
    #     )

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
        
                <p>Best regards,<br>
                <strong>{rental_company.name}</strong><br>
                Phone: {rental_company.phone_number}<br>
                Email: {rental_company.email}</p>
                </p>
            </body>
        </html>
        """

        return self._send_email_via_brevo(
            subject=subject,
            html_content=html_content,
            recipient_list=[pending_booking.guest.email]
        )

    def notify_admin_of_pending_conflict(self, pending_booking, extending_booking, new_end_time):
        """Send an email to admin when a booking is marked as pending_conflict."""
        pending_actual_end_time = pending_booking.end_time - timedelta(minutes=pending_booking.buffer_time)
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
                    <li><strong>Time:</strong> {pending_booking.start_time.strftime('%Y-%m-%d %H:%M')} to {pending_actual_end_time.strftime('%Y-%m-%d %H:%M')}</li>
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
        end = booking.end_time - timedelta(minutes=booking.buffer_time)
        
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
                    <li><strong>Booking time:</strong> {booking.start_time.strftime('%Y-%m-%d %H:%M')} to {end.strftime('%Y-%m-%d %H:%M')}</li>
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
        
    def send_cancellation_notification_to_admin_and_hotel(self, canceled_booking):
        """Send cancellation notification to admin and hotel."""
        subject = f"Booking Cancelled: Vehicle {canceled_booking.vehicle.model} Booking ID {canceled_booking.id}"
        
        html_content = f"""
        <html>
            <body>
                <h1>Booking Cancellation Alert</h1>
                
                <p>The booking with ID {canceled_booking.id} for vehicle {canceled_booking.vehicle.model} has been cancelled.</p>
                 
                <p>Please take any necessary action on your end.</p>
                
                <p>Regards,<br>The Booking System</p>
            </body>
        </html>
        """
        recipient_list = []
    
        admin_email = get_admin_email()
        if admin_email:
            recipient_list.append(admin_email)

        hotel_email = canceled_booking.hotel.email if hasattr(canceled_booking, 'hotel') else None
        if hotel_email:
            recipient_list.append(hotel_email)

        return self._send_email_via_brevo(
            subject=subject,
            html_content=html_content.strip(),
            recipient_list=recipient_list
        )
        
        
    def send_cancellation_notification_guest(self, canceled_booking):
        """Send cancellation notification to guest."""
        subject = f"Booking Cancelled: Vehicle {canceled_booking.vehicle.model} Booking ID {canceled_booking.id}"
        
        html_content = f"""
        <html>
            <body>
                <h1>Booking Cancellation Alert</h1>
                
                <p>Your booking with ID {canceled_booking.id} for vehicle {canceled_booking.vehicle.model} has been cancelled.</p>
                 
                <p>Thank you for using our services. Your payment will refunded soon.</p>
                
                <p>Regards,<br>The Booking System</p>
            </body>
        </html>
        """
        recipient_list = []
        guest_email = canceled_booking.guest.email if hasattr(canceled_booking, 'guest') else None
        if guest_email:
            recipient_list.append(guest_email)

        return self._send_email_via_brevo(
            subject=subject,
            html_content=html_content.strip(),
            recipient_list=recipient_list
        )


    def send_plaintext_cancellation_email(self, canceled_booking, extending_booking, new_end_time):
        """Send email notification regarding automatic cancellation."""
        subject = f"Booking Cancellation Notification: {canceled_booking.vehicle.model}"
        
        html_content = f"""
        <html>
            <body>
                <h1>Dear {canceled_booking.guest.first_name} {canceled_booking.guest.last_name},</h1>
                
                <p>We regret to inform you that your booking for the {canceled_booking.vehicle.model}, originally scheduled from 
                {canceled_booking.start_time.strftime('%B %d, %Y %H:%M')} to 
                {canceled_booking.end_time.strftime('%B %d, %Y %H:%M') }, has been canceled. This was necessary due to a priority extension of an existing booking.</p>
                
                <p>As a result, the vehicle will remain in use until {new_end_time.strftime('%B %d, %Y %H:%M')}.</p>
                
                <p>We sincerely apologize for any inconvenience this may cause and understand the impact this may have on your plans. Should you wish to book an alternative vehicle or reschedule your reservation, please feel free to contact us directly.</p>
                
                <p>We appreciate your understanding and look forward to assisting you further.</p>
                
                <p>Best regards,<br>The Booking Team</p>
            </body>
        </html>
        """

        return self._send_email_via_brevo(
            subject=subject,
            html_content=html_content,
            recipient_list=[canceled_booking.guest.email]
        )
