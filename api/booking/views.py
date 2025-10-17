from datetime import timedelta
from requests import Response
from rest_framework import viewsets
from api.booking.models import Booking
from api.booking.serializers import BookingSerializer, CancelBookingSerializer, PriceCalculationSerializer
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.response import Response 
from rest_framework import viewsets
from api.booking.models import Booking
from api.booking.serializers import BookingSerializer, ExtendBookingSerializer
from rest_framework.views import APIView
from rest_framework import status
from api.bookingConflict.models import BookingConflict
from decimal import Decimal
from django.utils import timezone
import stripe
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.db import transaction
from api.booking.models import Booking
from api.booking.serializers import CancelBookingSerializer  # Assuming you have this serializer


from api.booking.email_service import Email
from api.garage.models import Car
from middleware_platform import settings
from payments.models import Payment
from api.rental_company.models import RentalCompany


class BookingViewSet(viewsets.ModelViewSet):
    queryset = Booking.objects.all()
    serializer_class = BookingSerializer

class ExtendBookingView(APIView):
    def get(self, request, *args, **kwargs):
        # Handle both URL patterns
        booking_id = kwargs.get('booking_id')
        hotel_id = kwargs.get('hotel_id')
        car_id = kwargs.get('car_id')
        
        try:
            if booking_id:
                booking = Booking.objects.get(id=booking_id)
            elif hotel_id and car_id:
                booking = Booking.objects.get(hotel_id=hotel_id, vehicle_id=car_id)
            else:
                return Response(
                    {"detail": "Invalid parameters"},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            serializer = BookingSerializer(booking)
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except Booking.DoesNotExist:
            return Response(
                {"detail": "Booking not found"},
                status=status.HTTP_404_NOT_FOUND
            )
    
    def patch(self, request, booking_id):
        """
        Partially update a booking using booking ID (for time extension or start time change)
        - If extension/conflict conflicts with other bookings, cancel those bookings
        - Original booking gets priority
        - Send plain text cancellation emails to affected bookings
        """
        try:
            booking = Booking.objects.get(id=booking_id)
            serializer = ExtendBookingSerializer(booking, data=request.data, partial=True)

            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            email_service = Email()  # Instantiate the Email class

            # --------------------
            # HANDLE END TIME CHANGE
            # --------------------
            if 'new_end_time' in serializer.validated_data:
                raw_new_end_time = serializer.validated_data['new_end_time']
                actual_end_time = booking.end_time - timedelta(minutes=booking.buffer_time)

                # Validate new end time is after current end time
               

                # Calculate buffered new end time for storage
                buffered_new_end_time = raw_new_end_time + timedelta(minutes=booking.buffer_time)

            else:
                buffered_new_end_time = booking.end_time

            # --------------------
            # HANDLE START TIME CHANGE
            # --------------------
            if 'new_start_time' in serializer.validated_data:
                raw_new_start_time = serializer.validated_data['new_start_time']

                # Validate new start time is before current end time
                if raw_new_start_time >= booking.end_time:
                    return Response(
                        {"detail": "New start time must be before current end time"},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                booking.start_time = raw_new_start_time

            # --------------------
            # FIND CONFLICTING BOOKINGS
            # --------------------
            conflicting_bookings = Booking.objects.filter(
                vehicle_id=booking.vehicle_id,
                end_time__gt=booking.start_time,
                start_time__lt=buffered_new_end_time
            ).exclude(id=booking.id)

            canceled_details = []
            if conflicting_bookings.exists():
                for conflicting_booking in conflicting_bookings:
                    if conflicting_booking.status == Booking.STATUS_CANCELLED:
                        continue

                    canceled_details.append({
                        'id': str(conflicting_booking.id),
                        'guest_email': conflicting_booking.guest.email,
                        'start_time': conflicting_booking.start_time,
                        'end_time': conflicting_booking.end_time
                    })

                    # Send plain text notification
                    email_service.send_pending_conflict_email(conflicting_booking, booking, buffered_new_end_time)

                    # Mark as pending_conflict
                    conflicting_booking.status = Booking.STATUS_PENDING_CONFLICT
                    conflicting_booking.save()

                    # Log conflict
                    BookingConflict.objects.create(
                        original_booking=booking,
                        conflicting_booking=conflicting_booking,
                        status=BookingConflict.STATUS_PENDING
                    )

                    # Notify admin
                    email_service.notify_admin_of_pending_conflict(conflicting_booking, booking, buffered_new_end_time)

            # --------------------
            # UPDATE ORIGINAL BOOKING
            # --------------------
            if 'new_end_time' in serializer.validated_data:
                booking.end_time = buffered_new_end_time
            booking.save()

            if canceled_details:
                return Response({
                    "message": f"Booking updated successfully. {len(canceled_details)} conflicting bookings were canceled.",
                    "canceled_bookings": canceled_details,
                    "booking": BookingSerializer(booking).data
                }, status=status.HTTP_200_OK)

            return Response(BookingSerializer(booking).data, status=status.HTTP_200_OK)

        except Booking.DoesNotExist:
            return Response(
                {"detail": "Booking not found"},
                status=status.HTTP_404_NOT_FOUND
            )


            



class PriceCalculationView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = PriceCalculationSerializer(data=request.data)

        if serializer.is_valid():
            vehicle_id = serializer.validated_data['vehicle']
            new_start_time = serializer.validated_data['start_time']
            new_end_time = serializer.validated_data['end_time']
            original_end_time = serializer.validated_data.get('original_end_time')
            original_start_time = serializer.validated_data.get('original_start_time')

            try:
                car = Car.objects.get(id=vehicle_id)
            except Car.DoesNotExist:
                return Response({"error": "Car not found."}, status=status.HTTP_404_NOT_FOUND)

            # Determine calculation start
            if original_start_time and original_end_time:
                if new_start_time == original_start_time and new_end_time > original_end_time:
                    # Extension only
                    calculation_start = original_end_time
                    is_extension = True
                else:
                    # Start time changed, calculate full new period
                    calculation_start = new_start_time
                    is_extension = False
            else:
                calculation_start = new_start_time
                is_extension = False

            total_price = 0.0
            current_time = calculation_start

            while current_time < new_end_time:
                block_end_time = min(current_time + timedelta(hours=24), new_end_time)
                hours_in_block = (block_end_time - current_time).total_seconds() / 3600

                block_price = hours_in_block * car.price_per_hour
                block_price = min(block_price, car.max_price_per_day)
                total_price += block_price
                current_time = block_end_time

            duration = (new_end_time - calculation_start).total_seconds() / 3600

            return Response({
                'total_price': round(total_price, 2),
                'duration_hours': round(duration, 2),
                'is_extension': is_extension,
            }, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


from pytz import timezone as pytz_timezone

# class CancelBookingAPIView(APIView):
#     def post(self, request):
#         serializer = CancelBookingSerializer(data=request.data)
#         if not serializer.is_valid():
#             return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

#         booking_id = serializer.validated_data['booking_id']
#         booking = get_object_or_404(Booking, id=booking_id)

#         rome_tz = pytz_timezone('Europe/Rome')


#         start_time = booking.start_time

#         # Remove timezone info (make it naive)
#         start_time_naive = start_time.replace(tzinfo=None)

#         # Localize naive datetime as Rome time WITHOUT changing the time
#         start_time_rome = rome_tz.localize(start_time_naive)

#         now = timezone.now().astimezone(rome_tz)
        
        
#         if now >= start_time_rome:
#             return Response({"detail": "Cannot cancel a booking that has already started."}, status=status.HTTP_400_BAD_REQUEST)
        
#         time_until_start = start_time - now

#         # Determine refund policy
#         if time_until_start > timedelta(hours=96):
#             refund_percentage = Decimal('1.0')
#         elif timedelta(hours=48) < time_until_start <= timedelta(hours=96):
#             refund_percentage = Decimal('0.5')
#         else:
#             refund_percentage = Decimal('0.0')

#         with transaction.atomic():
#             booking.status = Booking.STATUS_CANCELLED
#             booking.save()

#             try:
#                 payment = Payment.objects.filter(
#                     booking_id=booking.id,
#                     status='succeeded',
#                     payment_type='initial'
#                 ).order_by('-created_at').first()

#                 if not payment:
#                     return Response({"detail": "No successful payment found for booking."}, status=status.HTTP_400_BAD_REQUEST)

#                 if Payment.objects.filter(
#                     stripe_payment_intent_id=payment.stripe_payment_intent_id
#                 ).exclude(booking_id=booking.id).exists():
#                     return Response({"detail": "Payment intent is shared by other bookings; aborting refund."}, status=status.HTTP_400_BAD_REQUEST)

#                 if refund_percentage > 0:
#                     refund_amount_cents = int(payment.amount * refund_percentage * 100)  # Convert to cents
#                     stripe.Refund.create(
#                         payment_intent=payment.stripe_payment_intent_id,
#                         amount=refund_amount_cents,
#                         reason='requested_by_customer'
#                     )
#                     payment.status = 'refunded'
#                     payment.save()

#                 # # Notifications
#                 email_service = Email()
#                 metadata = serializer.validated_data.get("metadata", {})
#                 email_service.send_booking_cancellation_email(metadata)
#                 email_service.send_hotel_notification_on_booking_cancellation_email(metadata)
#                 email_service.send_admin_booking_cancellation_email(metadata)

#             except stripe.error.StripeError as e:
#                 return Response({"detail": f"Stripe error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
#             except Exception as e:
#                 return Response({"detail": f"Unexpected error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

#         if refund_percentage == Decimal('1.0'):
#             message = "Booking cancelled. Full refund issued."
#         elif refund_percentage == Decimal('0.5'):
#             message = "Booking cancelled. 50% refund issued."
#         else:
#             message = "Booking cancelled. No refund as per policy."

#         return Response({"detail": message})



class CancelBookingAPIView(APIView):
    def post(self, request):
        serializer = CancelBookingSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        booking_id = serializer.validated_data['booking_id']
        booking = get_object_or_404(Booking, id=booking_id)

        rome_tz = pytz_timezone('Europe/Rome')
        start_time = booking.start_time

        # Remove timezone info (make it naive)
        start_time_naive = start_time.replace(tzinfo=None)

        # Localize naive datetime as Rome time WITHOUT changing the time
        start_time_rome = rome_tz.localize(start_time_naive)

        now = timezone.now().astimezone(rome_tz)
        
        if now >= start_time_rome:
            return Response({"detail": "Cannot cancel a booking that has already started."}, status=status.HTTP_400_BAD_REQUEST)
        
        time_until_start = start_time - now

        # Determine refund policy
        if time_until_start > timedelta(hours=96):
            refund_percentage = Decimal('1.0')
        elif timedelta(hours=48) < time_until_start <= timedelta(hours=96):
            refund_percentage = Decimal('0.5')
        else:
            refund_percentage = Decimal('0.0')

        with transaction.atomic():
            booking.status = Booking.STATUS_CANCELLED
            booking.save()

            try:
                # Get ONLY initial payment for refund calculation
                initial_payment = Payment.objects.filter(
                    booking_id=booking.id,
                    status='succeeded',
                    payment_type='initial'  # Only refund initial payments
                ).order_by('-created_at').first()

                if not initial_payment:
                    return Response({"detail": "No successful initial payment found for booking."}, status=status.HTTP_400_BAD_REQUEST)

                # Check if payment intent is shared by other bookings
                if Payment.objects.filter(
                    stripe_payment_intent_id=initial_payment.stripe_payment_intent_id
                ).exclude(booking_id=booking.id).exists():
                    return Response({"detail": "Payment intent is shared by other bookings; aborting refund."}, status=status.HTTP_400_BAD_REQUEST)

                # Refund logic for initial payment only
                if refund_percentage > 0:
                    refund_amount_cents = int(initial_payment.amount * refund_percentage * 100)
                    stripe.Refund.create(
                        payment_intent=initial_payment.stripe_payment_intent_id,
                        amount=refund_amount_cents,
                        reason='requested_by_customer'
                    )
                    initial_payment.status = 'refunded'
                    initial_payment.save()

                # Mark extension payments as cancelled (but don't refund them)
                extension_payments = Payment.objects.filter(
                    booking_id=booking.id,
                    status='succeeded',
                    payment_type='extension'
                )
                
                for ext_payment in extension_payments:
                    ext_payment.status = 'cancelled'
                    ext_payment.save()

                # Notifications
                email_service = Email()
                metadata = serializer.validated_data.get("metadata", {})
                email_service.send_booking_cancellation_email(metadata)
                email_service.send_hotel_notification_on_booking_cancellation_email(metadata)
                email_service.send_admin_booking_cancellation_email(metadata)

            except stripe.error.StripeError as e:
                return Response({"detail": f"Stripe error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            except Exception as e:
                return Response({"detail": f"Unexpected error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        if refund_percentage == Decimal('1.0'):
            message = "Booking cancelled. Full refund issued for initial payment."
        elif refund_percentage == Decimal('0.5'):
            message = "Booking cancelled. 50% refund issued for initial payment."
        else:
            message = "Booking cancelled. No refund as per policy."

        return Response({"detail": message})