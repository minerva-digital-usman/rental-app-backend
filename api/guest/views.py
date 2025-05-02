from rest_framework import viewsets
from api.guest.models import Guest
from api.guest.serializers import GuestSerializer

class GuestViewSet(viewsets.ModelViewSet):
    queryset = Guest.objects.all()
    serializer_class = GuestSerializer

