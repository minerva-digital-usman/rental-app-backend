from datetime import timedelta
from requests import Response
from rest_framework import viewsets
from api.booking.models import Booking
from api.booking.serializers import BookingSerializer
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.response import Response  # Correct import
from rest_framework import viewsets
from api.booking.models import Booking
from api.booking.serializers import BookingSerializer, ExtendBookingSerializer
from rest_framework.views import APIView
from rest_framework import status


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

    def post(self, request, hotel_id, car_id):
        try:
            booking = Booking.objects.get(hotel_id=hotel_id, vehicle_id=car_id)
            serializer = ExtendBookingSerializer(booking, data=request.data, partial=True)

            if serializer.is_valid():
                new_end_time = serializer.validated_data['new_end_time']
                
                # Check if new end time is after current end time
                if new_end_time <= booking.end_time:
                    return Response(
                        {"detail": "New end time must be after current end time"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Check for conflicts with other bookings
                effective_end = new_end_time
                if booking.buffer_time:
                    effective_end = new_end_time + timedelta(minutes=booking.buffer_time)
                
                overlapping_bookings = Booking.objects.filter(
                    vehicle_id=car_id,
                    end_time__gt=booking.start_time,
                    start_time__lt=effective_end
                ).exclude(id=booking.id)

                if overlapping_bookings.exists():
                    return Response(
                        {"detail": "This extension conflicts with existing bookings"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Update the booking
                booking.end_time = new_end_time
                booking.save()

                return Response(
                    BookingSerializer(booking).data,
                    status=status.HTTP_200_OK
                )
            else:
                return Response(
                    serializer.errors,
                    status=status.HTTP_400_BAD_REQUEST
                )

        except Booking.DoesNotExist:
            return Response(
                {"detail": "Booking not found"},
                status=status.HTTP_404_NOT_FOUND
            )
    


    def patch(self, request, booking_id):
        """
        Partially update a booking using booking ID (for time extension)
        """
        try:
            booking = Booking.objects.get(id=booking_id)
            serializer = ExtendBookingSerializer(booking, data=request.data, partial=True)

            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            if 'new_end_time' in serializer.validated_data:
                raw_new_end_time = serializer.validated_data['new_end_time']

                # Subtract buffer to get actual end time from stored end_time
                actual_end_time = booking.end_time - timedelta(minutes=booking.buffer_time)

                if raw_new_end_time <= actual_end_time:
                    return Response(
                        {"detail": "New end time must be after current end time"},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                # Add buffer to the new end time to store in DB
                buffered_new_end_time = raw_new_end_time + timedelta(minutes=booking.buffer_time)

                # Conflict check using buffered end time
                if Booking.objects.filter(
                    vehicle_id=booking.vehicle_id,
                    end_time__gt=booking.start_time,
                    start_time__lt=buffered_new_end_time
                ).exclude(id=booking.id).exists():
                    return Response(
                        {"detail": "Extension conflicts with existing bookings"},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                # Save buffered end time to DB
                booking.end_time = buffered_new_end_time
                booking.save()

            return Response(BookingSerializer(booking).data, status=status.HTTP_200_OK)

        except Booking.DoesNotExist:
            return Response(
                {"detail": "Booking not found"},
                status=status.HTTP_404_NOT_FOUND
            )