# api/cars/views.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from api.linkCarandHotel.models import CarHotelLink
from .models import Car
from .serializers import CarSerializer


class CarViewSet(viewsets.ModelViewSet):
    queryset = Car.objects.all()
    serializer_class = CarSerializer

    @action(detail=False, methods=['get'], url_path='by-hotel/(?P<hotel_id>[^/.]+)')
    def by_hotel(self, request, hotel_id=None):
        try:
            # Get all car links for this hotel
            car_links = CarHotelLink.objects.filter(hotel=hotel_id)
            car_ids = [link.car.id for link in car_links]
            cars = Car.objects.filter(id__in=car_ids)
            serializer = self.get_serializer(cars, many=True)
            return Response(serializer.data)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
