from datetime import timedelta
from requests import Response
from rest_framework import viewsets
from api.booking.models import Booking
from api.booking.serializers import BookingSerializer, PriceCalculationSerializer
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.response import Response 
from rest_framework import viewsets
from api.booking.models import Booking
from api.booking.serializers import BookingSerializer, ExtendBookingSerializer
from rest_framework.views import APIView
from rest_framework import status
from api.bookingConflict.models import BookingConflict


from api.booking.email_service import Email
from api.garage.models import Car
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
                email_service = Email()  # Instantiate the Email class
                email_service.send_extension_email(booking, buffered_new_end_time)

                # Find conflicting bookings
                conflicting_bookings = Booking.objects.filter(
                    vehicle_id=booking.vehicle_id,
                    end_time__gt=booking.start_time,
                    start_time__lt=buffered_new_end_time
                ).exclude(id=booking.id)

                canceled_details = []
                if conflicting_bookings.exists():
                    for conflicting_booking in conflicting_bookings:
                        canceled_details.append({
                            'id': str(conflicting_booking.id),
                            'guest_email': conflicting_booking.guest.email,
                            'start_time': conflicting_booking.start_time,
                            'end_time': conflicting_booking.end_time
                        })

                        # Send plain text notification
                        email_service.send_pending_conflict_email(conflicting_booking, booking, buffered_new_end_time)

                        # Mark as pending_conflict instead of deleting
                        conflicting_booking.status = Booking.STATUS_PENDING_CONFLICT
                        conflicting_booking.save()

                        # ✅ Log conflict in BookingConflict table
                        BookingConflict.objects.create(
                            original_booking=booking,
                            conflicting_booking=conflicting_booking,
                            status=BookingConflict.STATUS_PENDING
                        )

                        # Send notifications
                        email_service.notify_admin_of_pending_conflict(conflicting_booking, booking, buffered_new_end_time)


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
            

class PriceCalculationView(APIView):

    def post(self, request, *args, **kwargs):
        # Deserialize the request data
        serializer = PriceCalculationSerializer(data=request.data)

        if serializer.is_valid():
            # Extract relevant data from the validated input
            vehicle_id = serializer.validated_data['vehicle']
            start_time = serializer.validated_data['start_time']
            end_time = serializer.validated_data['end_time']

            # Fetch the car object
            try:
                car = Car.objects.get(id=vehicle_id)
            except Car.DoesNotExist:
                return Response({"error": "Car not found."}, status=status.HTTP_404_NOT_FOUND)

            # Apply buffer time to the end time
            # total_end_time = end_time + timedelta(minutes=buffer_time)

            # Calculate the duration of the booking
            duration = (end_time - start_time).total_seconds() / 3600  # in hours

            # Calculate price
            total_price = 0.0
            if duration <= 24:
                total_price = duration * car.price_per_hour
            else:
                total_price = (duration // 24) * car.max_price_per_day + (duration % 24) * car.price_per_hour

            # Return the calculated price
            return Response({
                'total_price': total_price,
                'duration_hours': duration,
                'vehicle': car.model,
                'vehicle_plate': car.plate_number,
            }, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)   