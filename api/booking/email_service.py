  
from datetime import timedelta
from django.core.mail import send_mail

from middleware_platform import settings
  
  
class Email:
      
    def send_extension_email(self, booking, new_end_time):
        """Send email notification regarding the booking extension."""
        subject = f"Booking Extension Confirmation: {booking.vehicle.model}"

        message = f"""
    
    Dear {booking.guest.first_name} {booking.guest.last_name},

    We are pleased to confirm that your booking extension has been successfully processed with Our Premium Car Rental Service. 
    We are happy to continue providing you with our services.

    Extended Booking Summary:
    ============================================
    - Booking Reference: {booking.id}
    - New Vehicle Return:  {new_end_time.strftime('%B %d, %Y %H:%M')}
    ============================================

    We thank you for your continued trust in our services and wish you safe travels.

    Warm regards,  
    The Booking Team
        """.strip()

        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[booking.guest.email],
            fail_silently=False,
        )



    def send_pending_conflict_email(self, pending_booking, extending_booking, new_end_time):
        """Send plain text email notification regarding pending conflict status."""
        subject = f"Booking Status Update: {pending_booking.vehicle.model} - Pending Confirmation"
        pending_actual_end_time = pending_booking.end_time - timedelta(minutes=pending_booking.buffer_time)
        message = f"""
        Dear {pending_booking.guest.first_name} {pending_booking.guest.last_name},

        We would like to inform you that your booking for the {pending_booking.vehicle.model}, originally scheduled from 
        {pending_booking.start_time.strftime('%B %d, %Y %H:%M')} to 
        {pending_actual_end_time.strftime('%B %d, %Y %H:%M')}, is currently marked as *pending confirmation* due to a scheduling conflict.

        A higher-priority booking has been extended and is now scheduled to occupy the vehicle until 
        {new_end_time.strftime('%B %d, %Y %H:%M')}. As a result, we are reviewing availability and will update you as soon as possible.

        We sincerely apologize for any inconvenience this may cause. If you wish to modify your reservation or explore alternate options, please don’t hesitate to reach out.

        Thank you for your patience and understanding.

        Best regards,  
        The Booking Team
        """.strip()

        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[pending_booking.guest.email],
            fail_silently=False,
        )

    def send_plaintext_cancellation_email(self, canceled_booking, extending_booking, new_end_time):
        """Send plain text email notification regarding automatic cancellation."""
        subject = f"Booking Cancellation Notification: {canceled_booking.vehicle.model}"

        message = f"""
        Dear {canceled_booking.guest.first_name} {canceled_booking.guest.last_name},

        We regret to inform you that your booking for the {canceled_booking.vehicle.model}, originally scheduled from 
        {canceled_booking.start_time.strftime('%B %d, %Y %H:%M')} to 
        {canceled_booking.end_time.strftime('%B %d, %Y %H:%M')}, has been automatically canceled. This was necessary due to a priority extension of an existing booking.

        As a result, the vehicle will remain in use until {new_end_time.strftime('%B %d, %Y %H:%M')}.

        We sincerely apologize for any inconvenience this may cause and understand the impact this may have on your plans. Should you wish to book an alternative vehicle or reschedule your reservation, please feel free to contact us directly.

        We appreciate your understanding and look forward to assisting you further.

        Best regards,  
        The Booking Team
        """.strip()

        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[canceled_booking.guest.email],
            fail_silently=False,
        )
    def notify_admin_of_pending_conflict(self, pending_booking, extending_booking, new_end_time):
        """Send an email to admin when a booking is marked as pending_conflict."""
        subject = f"[Alert] Booking Conflict - {pending_booking.vehicle.model} marked as PENDING"

        message = f"""
        Admin,

        A booking conflict has been detected and the affected booking has been marked as *pending_conflict*.

        ▶ Affected Booking (now pending):
        - Booking ID: {pending_booking.id}
        - Guest: {pending_booking.guest.first_name} {pending_booking.guest.last_name}
        - Email: {pending_booking.guest.email}
        - Time: {pending_booking.start_time.strftime('%Y-%m-%d %H:%M')} to {pending_booking.end_time.strftime('%Y-%m-%d %H:%M')}

        ▶ Conflicting Extension:
        - Booking ID: {extending_booking.id}
        - Guest: {extending_booking.guest.first_name} {extending_booking.guest.last_name}
        - Vehicle: {extending_booking.vehicle.model}
        - New End Time: {new_end_time.strftime('%Y-%m-%d %H:%M')}

        Please review this conflict and take necessary action if needed.

        – Booking System
        """.strip()

        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[settings.ADMIN_EMAIL],  # Ensure this is set in your Django settings
            fail_silently=False,
        )

    def send_conflict_resolved_email(self, booking):
        guest = booking.guest
        hotel = booking.hotel
        car = booking.vehicle  # or booking.car if you call it differently

        subject = "Your Booking Conflict Has Been Resolved"
        message = (
            f"Dear {guest.first_name},\n\n"
            f"Good news! Your booking conflict has been resolved.\n\n"
            f"Your new hotel: {hotel.name}\n"
            f"Address: {hotel.location}\n"
            f"Car: {car.model} ({car.plate_number})\n"
            f"Booking time: {booking.start_time.strftime('%Y-%m-%d %H:%M')} "
            f"to {booking.end_time.strftime('%Y-%m-%d %H:%M')}\n\n"
            f"If you have any questions, please contact support.\n\n"
            f"Thank you,\nThe Support Team"
        )

        # Use Django's email backend
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [guest.email],
            fail_silently=False,
        )