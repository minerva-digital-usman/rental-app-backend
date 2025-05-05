from io import BytesIO
import uuid
from django.http import JsonResponse
from rest_framework import viewsets
from api.guest.models import Guest
from api.guest.serializers import GuestSerializer
from django.views.decorators.csrf import csrf_exempt
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from rest_framework.response import Response

from api.guest.utils import is_driver_license_easyocr


class GuestViewSet(viewsets.ModelViewSet):
    queryset = Guest.objects.all()
    serializer_class = GuestSerializer
@csrf_exempt
def upload_driver_license_temp(request):
    if request.method == 'POST' and request.FILES.get('temp_driver_license'):
        image = request.FILES['temp_driver_license']

        # Validate file extension
        ext = image.name.split('.')[-1].lower()
        if ext not in ['jpg', 'jpeg', 'png', 'gif']:
            return JsonResponse({
                'is_valid': False,
                'error': 'Invalid file type. Only JPG, JPEG, PNG, and GIF are allowed.'
            }, status=200)

        try:
            # Read the image into memory once
            image_bytes = image.read()
            image_stream = BytesIO(image_bytes)

            # OCR check
            if not is_driver_license_easyocr(image_stream):
                return JsonResponse({
                    'is_valid': False,
                    'error': 'The uploaded image does not appear to be a valid driver\'s license'
                }, status=200)

            # Reset stream for saving
            image_stream.seek(0)
            filename = f"temp_driver_licenses/{uuid.uuid4()}.{ext}"
            path = default_storage.save(filename, ContentFile(image_stream.read()))
            temp_url = default_storage.url(path)

            return JsonResponse({
                'is_valid': True,
                'Temp_path': temp_url
            })
        except Exception as e:
            return JsonResponse({
                'is_valid': False,
                'error': str(e)
            }, status=500)

    return JsonResponse({
        'is_valid': False,
        'error': 'No image provided'
    }, status=400)