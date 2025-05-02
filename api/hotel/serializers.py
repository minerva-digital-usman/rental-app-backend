# api/hotel/serializers.py

from rest_framework import serializers
from .models import Hotel

class HotelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Hotel
        fields = '__all__'
        read_only_fields = ['id', 'guest_booking_url', 'qr_code']

    def create(self, validated_data):
        hotel = Hotel(**validated_data)
        hotel.save()
        return hotel

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance
