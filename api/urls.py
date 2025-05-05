# api/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from api.rental_company.views import RentalCompanyViewSet
from api.booking.views import BookingViewSet, ExtendBookingView
from api.guest.views import GuestViewSet
from api.hotel.views import HotelViewSet
from api.garage.views import CarViewSet
from api.linkCarandHotel.views import CarHotelLinkViewSet

router = DefaultRouter()
router.register(r'rental-company', RentalCompanyViewSet)
router.register(r'hotels', HotelViewSet)
router.register(r'guests', GuestViewSet)
router.register(r'bookings', BookingViewSet)
# router.register(r'vehicles', VehicleViewSet)
router.register(r'cars', CarViewSet)  # 'cars' will be the endpoint for this viewset
router.register(r'carhotellink', CarHotelLinkViewSet, basename='carhotellink')


urlpatterns = [
    path('', include(router.urls)),  # Include the router URLs
   


    
  
]
