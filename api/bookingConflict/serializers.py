from rest_framework import serializers
from bookingConflict.models import BookingConflict
class BookingConflictSerializer(serializers.ModelSerializer):
    class Meta:
        model = BookingConflict
        fields = '__all__'
