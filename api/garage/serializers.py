# api/cars/serializers.py
from rest_framework import serializers

from api.linkCarandHotel.models import CarHotelLink
from .models import Car
from api.hotel.models import Hotel

class CarSerializer(serializers.ModelSerializer):
    linked_hotels = serializers.SerializerMethodField()

    class Meta:
        model = Car
        fields = '__all__'

    def get_linked_hotels(self, obj):
        # Get all hotels linked to this car
        hotel_links = CarHotelLink.objects.filter(car=obj)
        return [link.hotel.id for link in hotel_links]