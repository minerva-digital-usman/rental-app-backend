from api.rental_company.models import RentalCompany
from django.core.mail import send_mail


def get_admin_email():
    company = RentalCompany.objects.first()
    return company.email if company else 'zeeshan6910@gmail.com'

