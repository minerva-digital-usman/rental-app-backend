# api/hotel/views.py

from django.http import JsonResponse
from rest_framework import viewsets

from api.booking.models import Booking
from api.linkCarandHotel.models import CarHotelLink
from .models import Hotel
from .serializers import HotelSerializer
from rest_framework.permissions import IsAuthenticatedOrReadOnly  # Optional
from django.utils.dateparse import parse_datetime

class HotelViewSet(viewsets.ModelViewSet):
    queryset = Hotel.objects.all()
    serializer_class = HotelSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]  # Or adjust as needed

    
    
    
def nearby_hotels_view(request):
    lat = request.GET.get('lat')
    lon = request.GET.get('lon')
    radius = float(request.GET.get('radius', 10))  # default 10 km
    start_time_str = request.GET.get('start_time')
    end_time_str = request.GET.get('end_time')

    if not lat or not lon or not start_time_str or not end_time_str:
        return JsonResponse({'error': 'Latitude, longitude, start_time, and end_time are required'}, status=400)

    try:
        start_time = parse_datetime(start_time_str)
        end_time = parse_datetime(end_time_str)
        if not start_time or not end_time:
            raise ValueError("Invalid datetime format")

        if start_time >= end_time:
            return JsonResponse({'error': 'start_time must be before end_time'}, status=400)

        nearby = Hotel.objects.nearby_hotels(lat, lon, radius)

        results = []

        for item in nearby:
            hotel = item['hotel']
            linked_cars = CarHotelLink.objects.filter(hotel=hotel).select_related('car')
            
            available_cars = []
            for link in linked_cars:
                car = link.car
                has_conflict = Booking.objects.filter(
                    vehicle=car,
                    status__in=[Booking.STATUS_ACTIVE],
                    end_time__gt=start_time,
                    start_time__lt=end_time
                ).exists()
                if not has_conflict:
                    available_cars.append({
                        'id': str(car.id),
                        'model': car.model,
                        'plate_number': car.plate_number,
                        'status': car.status,
                        'price_per_hour': car.price_per_hour,
                        'passengers': car.passengers,
                        'transmission': car.transmission,
                        'fuel_type': car.fuel_type,
                    })

            results.append({
                'id': str(hotel.id),
                'name': hotel.name,
                'distance_km': round(item['distance_km'], 2),
                'location': hotel.location,
                'latitude': float(hotel.latitude),
                'longitude': float(hotel.longitude),
                'phone': hotel.phone,
                'qr_code_url': hotel.qr_code.url if hotel.qr_code else None,
                'available_linked_cars': available_cars,
            })

        return JsonResponse({'results': results})

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)