from rest_framework import serializers
from .models import RentalCompany

class RentalCompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = RentalCompany
        fields = '__all__'

    def validate(self, data):
        # Check if it's a new instance being created (self.instance is None for creation)
        if self.instance is None:
            # Check if there is already a rental company in the database
            if RentalCompany.objects.exists():
                raise serializers.ValidationError("Only one RentalCompany is allowed.")
        return data
