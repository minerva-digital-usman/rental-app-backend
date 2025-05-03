from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views

from api.booking.views import ExtendBookingView
from api.guest.views import  upload_driver_license_temp
from auth.forms import StrictAdminPasswordResetForm
from payments import views


urlpatterns = [
    path('api/', include('api.urls')),
    path('api/upload-driver-license-temp/', upload_driver_license_temp, name='driver-license-upload-temp'),
    path('api/', include('payments.urls')),
    path('api/booking/extend/<uuid:hotel_id>/<uuid:car_id>/', ExtendBookingView.as_view(), name='extend-booking'),
    path('api/booking/<uuid:booking_id>/extend/', ExtendBookingView.as_view(), name='extend-booking'),
    path(
        'admin/password_reset/',
        auth_views.PasswordResetView.as_view(
            form_class=StrictAdminPasswordResetForm,
            success_url='/admin/password_reset/done/'
        ),
        name='admin_password_reset'
    ),
    path('admin/password_reset/done/', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    path(
        'reset/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(
            success_url='/admin/login/'  # Force admin redirect
        ),
        name='password_reset_confirm'
    ),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),
    path('admin/', admin.site.urls),  # Keep this last
    
]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Serve media files during development
# if settings.DEBUG:
#     urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
