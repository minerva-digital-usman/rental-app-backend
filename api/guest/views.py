from io import BytesIO
import uuid
from django.http import JsonResponse
from rest_framework import viewsets
from api.guest.models import Guest
from api.guest.serializers import GuestSerializer
from django.views.decorators.csrf import csrf_exempt
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

from api.guest.utils import is_driver_license_paddleocr


class GuestViewSet(viewsets.ModelViewSet):
    queryset = Guest.objects.all()
    serializer_class = GuestSerializer


@csrf_exempt
def upload_driver_license_temp(request):
    if request.method == 'POST' and request.FILES.get('temp_driver_license'):
        image = request.FILES['temp_driver_license']

        # Validate file extension
        ext = image.name.split('.')[-1].lower()
        if ext not in ['jpg', 'jpeg', 'png']:
            return JsonResponse({
                'is_valid': False,
                'error': 'Invalid file type. Only JPG, JPEG, and PNG are allowed.'
            }, status=200)

        try:
            # Read image into memory
            image_bytes = image.read()
            image_stream = BytesIO(image_bytes)

            # OCR validation
            is_valid, expiry_date, is_expired = is_driver_license_paddleocr(image_stream)

            if not is_valid:
                return JsonResponse({
                    'is_valid': False,
                    'error': "The uploaded image does not appear to be a valid driver's license."
                }, status=200)

            # Save temp file
            image_stream.seek(0)
            filename = f"temp_driver_licenses/{uuid.uuid4()}.{ext}"
            path = default_storage.save(filename, ContentFile(image_stream.read()))
            temp_url = default_storage.url(path)

            return JsonResponse({
                'is_valid': True,
                'Temp_path': temp_url,
                'expiry_date': expiry_date if expiry_date else 'Expiry date not found',
                'is_expired': is_expired if expiry_date else None
            })

        except Exception as e:
            return JsonResponse({
                'is_valid': False,
                'error': f'Processing error: {str(e)}'
            }, status=500)

    return JsonResponse({
        'is_valid': False,
        'error': 'No image provided'
    }, status=400)
