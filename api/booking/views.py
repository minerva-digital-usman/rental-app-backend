from datetime import timedelta
from requests import Response
from rest_framework import viewsets
from api.booking.models import Booking
from api.booking.serializers import BookingSerializer
from rest_framework.views import APIView
from rest_framework import status
from django.core.mail import send_mail
from rest_framework.response import Response  # Correct import
from rest_framework import viewsets
from api.booking.models import Booking
from api.booking.serializers import BookingSerializer, ExtendBookingSerializer
from rest_framework.views import APIView
from rest_framework import status

from middleware_platform import settings


class BookingViewSet(viewsets.ModelViewSet):
    queryset = Booking.objects.all()
    serializer_class = BookingSerializer

class ExtendBookingView(APIView):
    def get(self, request, hotel_id, car_id):
        try:
            booking = Booking.objects.get(hotel_id=hotel_id, vehicle_id=car_id)
            serializer = BookingSerializer(booking)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Booking.DoesNotExist:
            return Response(
                {"detail": "Booking not found"},
                status=status.HTTP_404_NOT_FOUND
            )

    def patch(self, request, booking_id):
        """
        Partially update a booking using booking ID (for time extension)
        - If extension conflicts with other bookings, cancel those bookings
        - Original booking gets priority
        - Send plain text cancellation emails to affected bookings
        """
        try:
            booking = Booking.objects.get(id=booking_id)
            serializer = ExtendBookingSerializer(booking, data=request.data, partial=True)

            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            if 'new_end_time' in serializer.validated_data:
                raw_new_end_time = serializer.validated_data['new_end_time']
                actual_end_time = booking.end_time - timedelta(minutes=booking.buffer_time)

                # Validate new end time is after current end time
                if raw_new_end_time <= actual_end_time:
                    return Response(
                        {"detail": "New end time must be after current end time"},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                # Calculate buffered new end time for storage
                buffered_new_end_time = raw_new_end_time + timedelta(minutes=booking.buffer_time)

                # Send the extension email first before canceling conflicting bookings
                self.send_extension_email(booking, buffered_new_end_time)

                # Find conflicting bookings
                conflicting_bookings = Booking.objects.filter(
                    vehicle_id=booking.vehicle_id,
                    end_time__gt=booking.start_time,
                    start_time__lt=buffered_new_end_time
                ).exclude(id=booking.id)

                canceled_details = []
                if conflicting_bookings.exists():
                    for conflicting_booking in conflicting_bookings:
                        # Store details before deletion
                        canceled_details.append({
                            'id': str(conflicting_booking.id),
                            'guest_email': conflicting_booking.guest.email,
                            'start_time': conflicting_booking.start_time,
                            'end_time': conflicting_booking.end_time
                        })
                        
                        # Send plain text cancellation email
                        self.send_plaintext_cancellation_email(conflicting_booking, booking, buffered_new_end_time)
                        
                        # Delete the conflicting booking
                        conflicting_booking.delete()

                    # Update the original booking after cancellations
                    booking.end_time = buffered_new_end_time
                    booking.save()

                    return Response({
                        "message": f"Booking extended successfully. {len(canceled_details)} conflicting bookings were canceled.",
                        "canceled_bookings": canceled_details,
                        "booking": BookingSerializer(booking).data
                    }, status=status.HTTP_200_OK)

                # No conflicts - just update normally
                booking.end_time = buffered_new_end_time
                booking.save()
                return Response(BookingSerializer(booking).data, status=status.HTTP_200_OK)

        except Booking.DoesNotExist:
            return Response(
                {"detail": "Booking not found"},
                status=status.HTTP_404_NOT_FOUND
            )
            
    def send_extension_email(self, booking, new_end_time):
        """Send email notification regarding the booking extension."""
        subject = f"Booking Extension Confirmation: {booking.vehicle.model}"

        message = f"""
    Dear {booking.guest.first_name} {booking.guest.last_name},

    We are pleased to inform you that your booking for the {booking.vehicle.model}, originally scheduled from 
    {booking.start_time.strftime('%B %d, %Y %H:%M')} to 
    {booking.end_time.strftime('%B %d, %Y %H:%M')}, has been successfully extended. The new end time for your booking is now 
    {new_end_time.strftime('%B %d, %Y %H:%M')}.

    We trust this extension will accommodate your needs, and we remain at your service for any further assistance.

    Should you have any questions or require additional information, please do not hesitate to contact us.

    Thank you for choosing our service. We look forward to continuing to serve you.

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
