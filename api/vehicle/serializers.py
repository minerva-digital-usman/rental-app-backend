from rest_framework import serializers
from api.vehicle.models import Vehicle
from api.hotel.models import Hotel
from api.rental_company.models import RentalCompany

class VehicleSerializer(serializers.ModelSerializer):
    rental_company_id = serializers.UUIDField(source='rental_company.id', read_only=True)
    hotel_id = serializers.UUIDField(source='hotel.id', read_only=True)  # Change to read_only
    qr_code_url = serializers.SerializerMethodField()

    class Meta:
        model = Vehicle
        fields = [
            'id',
            'vehicle_type',
            'model',
            'plate_number',
            'description',
            'status',
            'price_per_hour',
            'max_price_per_day',
            'passengers',
            'doors',
            'luggage',
            'transmission',
            'air_conditioning',
            'fuel_type',
            'qr_code',
            'qr_code_url',
            'in_car_extension_url',
            'rental_company_id',
            'hotel_id',  # hotel_id will now be included in the response
        ]

    def get_qr_code_url(self, obj):
        """
        Custom method to get the URL of the generated QR code image.
        """
        if obj.qr_code:
            return obj.qr_code.url
        return None

    def create(self, validated_data):
        hotel_data = validated_data.pop('hotel_id')  # Get hotel_id as UUID
        hotel = Hotel.objects.get(id=hotel_data)  # Retrieve the Hotel instance by UUID
        
        # Get the rental company
        rental_company = self.context['request'].user.rentalcompany  # Adjust if needed
        
        # Create the vehicle with the correct hotel and rental company
        vehicle = Vehicle.objects.create(
            hotel=hotel,
            rental_company=rental_company,
            **validated_data
        )
        return vehicle

    def validate(self, data):
        # Handle both create and update cases
        hotel_id = data.get('hotel_id')  # Get hotel_id from validated data
        
        if hotel_id:
            hotel = Hotel.objects.get(id=hotel_id)
            
            # Check the number of vehicles in this hotel
            vehicles = Vehicle.objects.filter(hotel=hotel)
            
            # If updating, exclude the current vehicle from the count
            if self.instance:
                vehicles = vehicles.exclude(pk=self.instance.pk)
            
            if vehicles.count() >= 2:
                raise serializers.ValidationError("Each hotel can only have up to 2 vehicles.")
        
        return data
