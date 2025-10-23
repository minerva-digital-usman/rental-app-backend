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


            



def _calculate_extension_with_original(self, car, original_start, original_end, new_end):
    """
    Calculate extension price considering hours already used in original booking,
    respecting the daily (calendar-day) maximum rate.
    """
    total_extension_price = Decimal('0.0')
    current_time = original_end
    daily_totals = {}

    # Pre-fill already charged amounts per day from original booking
    temp_time = original_start
    while temp_time < original_end:
        day = temp_time.date()
        day_end = datetime.combine(day, datetime.max.time()).replace(tzinfo=temp_time.tzinfo)
        block_end = min(day_end, original_end)
        hours_in_day = Decimal((block_end - temp_time).total_seconds()) / Decimal(3600)
        charge = min(hours_in_day * Decimal(car.price_per_hour), Decimal(car.max_price_per_day))
        daily_totals[day] = min(daily_totals.get(day, Decimal('0.0')) + charge, Decimal(car.max_price_per_day))
        temp_time = block_end

    # Now calculate extension price day by day
    while current_time < new_end:
        day = current_time.date()
        day_end = datetime.combine(day, datetime.max.time()).replace(tzinfo=current_time.tzinfo)
        block_end_time = min(day_end, new_end)
        hours_in_block = Decimal((block_end_time - current_time).total_seconds()) / Decimal(3600)
        block_price = hours_in_block * Decimal(car.price_per_hour)

        already_paid_today = daily_totals.get(day, Decimal('0.0'))
        remaining_cap = max(Decimal(car.max_price_per_day) - already_paid_today, Decimal('0.0'))
        charge_today = min(block_price, remaining_cap)
        
        total_extension_price += charge_today
        daily_totals[day] = already_paid_today + charge_today
        current_time = block_end_time

    return total_extension_price




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
        start_time_naive = start_time.replace(tzinfo=None)
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
                # Get all succeeded payments (initial + extensions) - THIS IS CORRECT
                payments = Payment.objects.filter(
                    booking_id=booking.id,
                    status='succeeded',
                    payment_type__in=['initial', 'extension']  # This includes both!
                )

                if not payments.exists():
                    return Response({"detail": "No successful payments found for booking."}, status=status.HTTP_400_BAD_REQUEST)

                # Check all payment intents for shared use
                for p in payments:
                    if Payment.objects.filter(
                        stripe_payment_intent_id=p.stripe_payment_intent_id
                    ).exclude(booking_id=booking.id).exists():
                        return Response({"detail": "Payment intent shared by other bookings; aborting refund."}, status=status.HTTP_400_BAD_REQUEST)

                # Process refunds for ALL payments - THIS IS CORRECT
                total_refunded = 0
                if refund_percentage > 0:
                    for p in payments:
                        refund_amount_cents = int(p.amount * refund_percentage * 100)
                        stripe.Refund.create(
                            payment_intent=p.stripe_payment_intent_id,
                            amount=refund_amount_cents,
                            reason='requested_by_customer'
                        )
                        p.status = 'refunded'
                        p.save()
                        total_refunded += p.amount * refund_percentage
                else:
                    # Mark all as cancelled (no refund)
                    for p in payments:
                        p.status = 'cancelled'
                        p.save()

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

        # Enhanced response message
        payment_count = payments.count()
        if refund_percentage == Decimal('1.0'):
            message = f"Booking cancelled. Full refund issued for {payment_count} payment(s) (initial + extensions)."
        elif refund_percentage == Decimal('0.5'):
            message = f"Booking cancelled. 50% refund issued for {payment_count} payment(s) (initial + extensions)."
        else:
            message = f"Booking cancelled. No refund as per policy for {payment_count} payment(s)."

        return Response({"detail": message})