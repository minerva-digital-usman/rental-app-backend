from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.decorators import action
from api.vehicle.models import Vehicle
from api.vehicle.serializers import VehicleSerializer
from api.hotel.models import Hotel


class VehicleViewSet(viewsets.ModelViewSet):
    """
    A viewset for listing, retrieving, creating, updating, and deleting vehicles.
    """
    queryset = Vehicle.objects.all()
    serializer_class = VehicleSerializer
    
    
    def get_queryset(self):
        """
        Optionally filters the queryset by hotel_id if provided in the query parameters.
        """
        queryset = super().get_queryset()
        hotel_id = self.request.query_params.get('hotel_id')
        if hotel_id:
            queryset = queryset.filter(hotel_id=hotel_id)
        return queryset

    @action(detail=True, methods=['get'])
    def qr_code(self, request, pk=None):
        """
        Endpoint to retrieve a vehicle's QR code.
        URL: /api/vehicles/{id}/qr_code/
        """
        vehicle = self.get_object()
        if vehicle.qr_code:
            return Response({"qr_code_url": vehicle.qr_code.url}, status=status.HTTP_200_OK)
        return Response({"error": "QR Code not available for this vehicle."}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['get'])
    def extension_url(self, request, pk=None):
        """
        Endpoint to get the vehicle's extension URL.
        URL: /api/vehicles/{id}/extension_url/
        """
        vehicle = self.get_object()
        return Response({"in_car_extension_url": vehicle.in_car_extension_url}, status=status.HTTP_200_OK)

  

    def perform_create(self, serializer):
        # Ensure you retrieve the hotel by UUID and pass it to the serializer
        hotel_id = self.request.data.get("hotel_id")  # Assuming hotel_id is passed as UUID string
        hotel = Hotel.objects.get(id=hotel_id)  # Retrieve the hotel using the UUID
        
        # Pass the hotel object into the serializer
        serializer.save(hotel=hotel)