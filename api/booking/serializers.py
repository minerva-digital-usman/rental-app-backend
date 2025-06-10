from datetime import timedelta
from rest_framework import serializers
from api.booking.models import Booking
from api.guest.models import Guest
from api.guest.serializers import GuestSerializer
from api.hotel.models import Hotel
from api.garage.models import Car


class BookingSerializer(serializers.ModelSerializer):
    vehicle_id = serializers.UUIDField(write_only=True)  # This field will refer to the Car model now
    hotel_id = serializers.UUIDField(write_only=True)
    guest = GuestSerializer(write_only=True)
    guest_id = serializers.UUIDField(read_only=True)

    vehicle = serializers.UUIDField(source='vehicle.id', read_only=True)
    hotel = serializers.UUIDField(source='hotel.id', read_only=True)

    class Meta:
        model = Booking
        fields = [
            'id',
            'vehicle_id',
            'hotel_id',
            'vehicle',
            'hotel',
            'guest',
            'guest_id',
            'start_time',
            'end_time',
            'buffer_time',
            'status', 

        ]

    def create(self, validated_data):
        vehicle_id = validated_data.pop('vehicle_id')
        hotel_id = validated_data.pop('hotel_id')
        guest_data = validated_data.pop('guest')

        # Get vehicle and hotel
        vehicle = Car.objects.get(id=vehicle_id)
        hotel = Hotel.objects.get(id=hotel_id)

        # Find or create guest - no validation on phone/email
        guest, created = Guest.objects.get_or_create(
            email=guest_data['email'],
            defaults=guest_data
        )
        
        # If guest exists, update their information with any new data
        if not created:
            for field, value in guest_data.items():
                setattr(guest, field, value)
            guest.save()

        # Create the booking
        booking = Booking.objects.create(
            vehicle=vehicle,
            hotel=hotel,
            guest=guest,
            **validated_data
        )
        return booking


def validate(self, data):
    start_time = data.get('start_time')
    end_time = data.get('end_time')
    vehicle_id = data.get('vehicle_id')
    buffer_minutes = data.get('buffer_time', 15)  # Default buffer time if not provided

    # Ensure start time is before end time
    if start_time >= end_time:
        raise serializers.ValidationError("End time must be after start time.")

    if vehicle_id:
        # Adjusted to use Car model
        car = Car.objects.get(id=vehicle_id)
        existing_bookings = Booking.objects.filter(vehicle=car)

        for booking in existing_bookings:
            # Add buffer time to the end of the existing booking to create a "blocked period"
            blocked_start = booking.start_time - timedelta(minutes=buffer_minutes)
            blocked_end = booking.end_time + timedelta(minutes=buffer_minutes)

            # Check if the requested time overlaps with the blocked period
            if start_time < blocked_end and end_time > blocked_start:
                # This means there is a conflict
                raise serializers.ValidationError({
                    "booking": (
                        f"This car is already booked or has a buffer period conflict "
                        f"between {booking.start_time.strftime('%H:%M')} and {booking.end_time.strftime('%H:%M')}."
                    )
                })

            # Allow booking if the requested time starts right after the buffer ends
            # Condition for no overlap:
            if end_time <= booking.start_time and start_time >= booking.end_time + timedelta(minutes=buffer_minutes):
                continue

    return data


import uuid

class CancelBookingSerializer(serializers.Serializer):
    booking_id = serializers.UUIDField()
    metadata = serializers.DictField(required=False)
    
    def validate_booking_id(self, value):
        try:
            return uuid.UUID(str(value))
        except ValueError:
            raise serializers.ValidationError("Invalid booking ID format")
    
class ExtendBookingSerializer(serializers.ModelSerializer):
    new_end_time = serializers.DateTimeField(required=True)

    class Meta:
        model = Booking
        fields = ['new_end_time']

    def validate_new_end_time(self, value):
        booking = self.instance
        actual_end_time = booking.end_time - timedelta(minutes=booking.buffer_time)

        if value <= actual_end_time:
            raise serializers.ValidationError(
                "New end time must be after current end time"
            )
        return value

    def update(self, instance, validated_data):
        instance.end_time = validated_data['new_end_time']
        instance.save()
        return instance
class PriceCalculationSerializer(serializers.Serializer):
    vehicle = serializers.UUIDField()  # car ID
    start_time = serializers.DateTimeField()
    end_time = serializers.DateTimeField()

    def validate(self, data):
        # Ensure end time is after start time
        if data['start_time'] >= data['end_time']:
            raise serializers.ValidationError("End time must be after start time.")
        return data