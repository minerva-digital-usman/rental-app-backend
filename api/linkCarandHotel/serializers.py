from rest_framework import serializers
from .models import CarHotelLink
from api.hotel.models import Hotel
from api.garage.models import Car

class CarHotelLinkSerializer(serializers.ModelSerializer):
    car = serializers.PrimaryKeyRelatedField(queryset=Car.objects.all())
    hotel = serializers.PrimaryKeyRelatedField(queryset=Hotel.objects.all())
    qr_code_url = serializers.SerializerMethodField()
    in_car_extension_url = serializers.URLField(read_only=True)
    car_details = serializers.SerializerMethodField()
    hotel_details = serializers.SerializerMethodField()

    class Meta:
        model = CarHotelLink
        fields = [
            'id', 
            'car',
            'car_details',
            'hotel',
            'hotel_details',
            'in_car_extension_url',
            'qr_code_url',
            'created_at', 
            'updated_at'
        ]
        read_only_fields = ['in_car_extension_url', 'qr_code_url', 'car_details', 'hotel_details']

    def get_qr_code_url(self, obj):
        if obj.qr_code:
            return self.context['request'].build_absolute_uri(obj.qr_code.url)
        return None

    def get_car_details(self, obj):
        return {
            'model': obj.car.model,
            'plate_number': obj.car.plate_number,
            'vehicle_type': obj.car.vehicle_type
        }

    def get_hotel_details(self, obj):
        return {
            'name': obj.hotel.name,
            'address': obj.hotel.address
        }

    def validate(self, data):
        if CarHotelLink.objects.filter(car=data['car']).exclude(id=self.instance.id if self.instance else None).exists():
            raise serializers.ValidationError(
                {'car': 'This car is already linked to another hotel.'}
            )
        return data