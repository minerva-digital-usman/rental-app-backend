from rest_framework import serializers
from api.guest.models import Guest

class GuestSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(read_only=True)
 

    class Meta:
        model = Guest
        fields = [
            'id',
            'first_name',
            'last_name',
            'email',
            'phone',
            'fiscal_code',
            'driver_license',
        ]
