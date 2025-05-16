from rest_framework import viewsets
from django.core.mail import send_mail

from .models import RentalCompany
from .serializers import RentalCompanySerializer

class RentalCompanyViewSet(viewsets.ModelViewSet):
    queryset = RentalCompany.objects.all()
    serializer_class = RentalCompanySerializer
