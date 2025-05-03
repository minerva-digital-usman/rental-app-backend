import uuid
from django.http import JsonResponse
from rest_framework import viewsets
from api.guest.models import Guest
from api.guest.serializers import GuestSerializer
from django.views.decorators.csrf import csrf_exempt
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

class GuestViewSet(viewsets.ModelViewSet):
    queryset = Guest.objects.all()
    serializer_class = GuestSerializer

@csrf_exempt
def upload_driver_license_temp(request):
    if request.method == 'POST' and request.FILES.get('temp_driver_license'):
        image = request.FILES['temp_driver_license']
        
        # Validate file extension
        ext = image.name.split('.')[-1].lower()
        if ext not in ['jpg', 'jpeg', 'png', 'gif']:  # Add/remove allowed extensions as needed
            return JsonResponse({'error': 'Invalid file type'}, status=400)
        
        # Create a more organized filename/path
        filename = f"temp_driver_licenses/{uuid.uuid4()}.{ext}"
        
        # Save the file permanently
        try:
            path = default_storage.save(filename, ContentFile(image.read()))
            temp_url = default_storage.url(path)
            

            
            return JsonResponse({'Temp_path': temp_url})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'No image provided'}, status=400)