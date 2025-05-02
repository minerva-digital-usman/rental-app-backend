from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from api.hotel.models import Hotel

def booking_page(request, hotel_id):
    # Get the hotel object using the provided hotel_id
    hotel = get_object_or_404(Hotel, id=hotel_id)
    
    # For now, we'll just return the hotel name as a simple test
    return HttpResponse(f"Booking Page for Hotel: {hotel.name}")
