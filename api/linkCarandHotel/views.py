from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import CarHotelLink
from .serializers import CarHotelLinkSerializer
from api.garage.models import Car
from api.hotel.models import Hotel

class CarHotelLinkViewSet(viewsets.ModelViewSet):
    queryset = CarHotelLink.objects.select_related('car', 'hotel').all()
    serializer_class = CarHotelLinkSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        car_id = self.request.query_params.get('car_id')
        hotel_id = self.request.query_params.get('hotel_id')
        
        if car_id:
            queryset = queryset.filter(car_id=car_id)
        if hotel_id:
            queryset = queryset.filter(hotel_id=hotel_id)
            
        return queryset
    
    @action(detail=False, methods=['get'], url_path='car/(?P<car_id>[^/.]+)')
    def get_hotel_for_car(self, request, car_id=None):
        try:
            link = CarHotelLink.objects.select_related('hotel').get(car_id=car_id)
            serializer = self.get_serializer(link)
            return Response(serializer.data)
        except CarHotelLink.DoesNotExist:
            return Response(
                {'detail': 'No hotel linked to this car.'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['get'], url_path='hotel/(?P<hotel_id>[^/.]+)/cars')
    def get_cars_for_hotel(self, request, hotel_id=None):
        links = CarHotelLink.objects.select_related('car').filter(hotel_id=hotel_id)
        serializer = self.get_serializer(links, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'], url_path='qr-code')
    def get_qr_code(self, request, pk=None):
        link = self.get_object()
        if not link.qr_code:
            link.generate_qr_code()
            link.save()
        qr_code_url = request.build_absolute_uri(link.qr_code.url)
        return Response({'qr_code_url': qr_code_url})