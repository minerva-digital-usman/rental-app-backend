# api/hotel/views.py

from rest_framework import viewsets
from .models import Hotel
from .serializers import HotelSerializer
from rest_framework.permissions import IsAuthenticatedOrReadOnly  # Optional

class HotelViewSet(viewsets.ModelViewSet):
    queryset = Hotel.objects.all()
    serializer_class = HotelSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]  # Or adjust as needed
