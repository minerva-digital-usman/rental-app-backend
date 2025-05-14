from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.urls import reverse
from api.hotel.models import Hotel
from api.booking.email_service import Email
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.models import User
def booking_page(request, hotel_id):
    # Get the hotel object using the provided hotel_id
    hotel = get_object_or_404(Hotel, id=hotel_id)
    
    # For now, we'll just return the hotel name as a simple test
    return HttpResponse(f"Booking Page for Hotel: {hotel.name}")

