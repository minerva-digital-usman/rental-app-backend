from django import forms
from django.contrib import admin
from django.contrib import messages
from django.utils.html import format_html
from django.db.models import Sum
from django.contrib.auth.models import Group
from django.apps import apps

# Import all your models
from api.rental_company.models import RentalCompany
from api.hotel.models import Hotel
from api.guest.models import Guest
from api.booking.models import Booking
from api.garage.models import Car
from api.linkCarandHotel.models import CarHotelLink
from payments.admin import CustomerPaymentMethodAdmin
from payments.models import CustomerPaymentMethod, Payment

# Custom Admin Site with Jazmin-compatible groupings
class CustomAdminSite(admin.AdminSite):
    site_header = "Booking Management System"
    site_title = "Admin Portal"
    index_title = "Dashboard"
    
    def get_app_list(self, request):
        # Build the default app dictionary
        app_dict = self._build_app_dict(request)
        
        # Create our custom groupings
        custom_groups = [
            {
                'name': 'Setup',
                'app_label': 'Management',
                'models': self._get_models_for_group(app_dict, ['Car', 'CarHotelLink', 'Hotel'])
            },
            {
                'name': 'Management',
                'app_label': 'booking_system',
                'models': self._get_models_for_group(app_dict, ['Booking', 'Payment', 'CustomerPaymentMethod','RentalCompany', 'Guest'])
            },
            
        ]
        
        # Filter out empty groups and ensure Jazmin compatibility
        return [group for group in custom_groups if group['models']]
    
    def _get_models_for_group(self, app_dict, model_names):
        """Helper method to get models from app_dict by name"""
        models = []
        
        # Check both 'api' and 'payments' apps
        for app_name in ['api', 'payments']:
            if app_name in app_dict:
                for model in app_dict[app_name]['models']:
                    if model['object_name'] in model_names:
                        # Ensure all required fields exist for Jazmin
                        model.setdefault('admin_url', '#')
                        model.setdefault('add_url', '#')
                        model.setdefault('perms', {'add': True, 'change': True, 'delete': True})
                        models.append(model)
        
        return models

# Replace the default admin site
admin.site = CustomAdminSite(name='admin')

# --- Form Definitions ---
class BookingForm(forms.ModelForm):
    class Meta:
        model = Booking
        fields = '__all__'

    start_time = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={
            'type': 'datetime-local',
            'step': '900'  # 15 minutes
        })
    )
    end_time = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={
            'type': 'datetime-local',
            'step': '900'
        })
    )

# --- ModelAdmin Classes ---
class RentalCompanyAdmin(admin.ModelAdmin):
    list_display = ('name', 'address', 'email', 'phone_number')
    search_fields = ('name', 'address', 'email')
    
    def has_add_permission(self, request):
        return not RentalCompany.objects.exists()

class CarAdmin(admin.ModelAdmin):
    list_display = ('model', 'plate_number', 'status', 'price_per_hour', 'max_price_per_day')
    list_filter = ('status', 'model')
    search_fields = ('model', 'plate_number')

    def save_model(self, request, obj, form, change):
        # Assume the hotel is being passed in form.cleaned_data via a custom field
        hotel = form.cleaned_data.get('hotel')  # You must ensure this field is in the form

        if not change and hotel:
            linked_cars = CarHotelLink.objects.filter(hotel=hotel).count()
            if linked_cars >= 2:
                messages.warning(request, "This hotel already has 2 vehicles.")
                return

        super().save_model(request, obj, form, change)

class GuestAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'email', 'phone', 'fiscal_code', 'driver_license_image')
    search_fields = ('first_name', 'last_name', 'email','fiscal_code')
    
    def driver_license_image(self, obj):
        if obj.driver_license:
            # Construct the full URL if needed, ensuring the /media/ part is included
            full_url = obj.driver_license if obj.driver_license.startswith('/media/') else f"/media/{obj.driver_license}"

            return format_html(
                '''
                <div style="position: relative; display: inline-block;">
                    <img src="{}" width="100" height="100" style="display: block;" />
                    <a href="{}" download style="
                        position: absolute;
                        top: 0;
                        left: 0;
                        width: 100%;
                        height: 100%;
                        background: rgba(0, 0, 0, 0.5);
                        color: white;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        text-decoration: none;
                        opacity: 0;
                        transition: opacity 0.3s;
                    " onmouseover="this.style.opacity=1" onmouseout="this.style.opacity=0">
                        ⬇ Download
                    </a>
                </div>
                ''',
                full_url,
                full_url
            )
        return "No Image"




class BookingAdmin(admin.ModelAdmin):
    form = BookingForm
    list_display = ('id','guest_full_name', 'vehicle', 'hotel', 'start_time', 'end_time', 'buffer_time')
    list_filter = ('hotel', 'vehicle')
    search_fields = ('guest__first_name', 'guest__last_name')

    def guest_full_name(self, obj):
        return f"{obj.guest.first_name} {obj.guest.last_name}"
    guest_full_name.short_description = 'Guest'

class PaymentAdmin(admin.ModelAdmin):
    list_display = ('id', 'guest_name', 'amount', 'currency', 'status', 'created_at', 'hotel_name', 'hotel_id')
    search_fields = ('booking__guest__first_name', 'booking__guest__last_name', 'stripe_session_id')
    list_filter = ('status', 'currency', 'created_at')
    ordering = ('-created_at',)

    def guest_name(self, obj):
        return f"{obj.booking.guest.first_name} {obj.booking.guest.last_name}"
    guest_name.short_description = 'Guest'

    def hotel_name(self, obj):
        return obj.booking.hotel.name if obj.booking and obj.booking.hotel else '-'
    hotel_name.short_description = 'Hotel Name'

    def hotel_id(self, obj):
        return obj.booking.hotel.id if obj.booking and obj.booking.hotel else '-'
    hotel_id.short_description = 'Hotel ID'

class HotelAdmin(admin.ModelAdmin):
    list_display = ('name', 'location', 'phone', 'email', 'qr_code_preview', 'total_earnings')
    search_fields = ('name', 'location', 'phone', 'email')
    list_filter = ('rental_company', 'location')
    list_editable = ('phone', 'email')
    list_per_page = 20
    autocomplete_fields = ['rental_company']  # This now works with RentalCompanyAdmin
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'location', 'rental_company')
        }),
        ('Contact Information', {
            'fields': ('phone', 'email')
        }),
        ('QR Code Settings', {
            'fields': ('guest_booking_url', 'qr_code')
        }),
    )
    
    readonly_fields = ('qr_code_preview',)
    
    def qr_code_preview(self, obj):
        if obj.qr_code:
            return format_html('''
                <div style="position: relative; display: inline-block;">
                    <img src="{}" width="100" height="100" style="display: block;" />
                    <a href="{}" download style="
                        position: absolute;
                        top: 0;
                        left: 0;
                        width: 100%;
                        height: 100%;
                        background: rgba(0, 0, 0, 0.5);
                        color: white;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        text-decoration: none;
                        opacity: 0;
                        transition: opacity 0.3s;
                    " onmouseover="this.style.opacity=1" onmouseout="this.style.opacity=0">
                        ⬇ Download
                    </a>
                </div>
            ''', obj.qr_code.url, obj.qr_code.url)
        return "-"
    qr_code_preview.short_description = 'QR Code'

    
    def total_earnings(self, obj):
        # Aggregate payments based on the hotel ID
        total = Payment.objects.filter(booking__hotel=obj).aggregate(Sum('amount'))['amount__sum']
        return f"€{total:.2f}" if total else '€0.00'
    total_earnings.short_description = 'Total Earnings'

    def save_model(self, request, obj, form, change):
        if not obj.guest_booking_url:
            obj.guest_booking_url = obj.generate_guest_booking_url()
        if change and ('name' in form.changed_data or not obj.qr_code):
            obj.generate_qr_code()
        super().save_model(request, obj, form, change)

class CarHotelLinkAdmin(admin.ModelAdmin):
    list_display = ('car_link', 'hotel_link', 'qr_code_image')
    
    def car_link(self, obj):
        return format_html("<a href='/admin/api/car/{}/'>{}</a>", obj.car.id, obj.car)
    car_link.short_description = 'Car'
    
    def hotel_link(self, obj):
        return format_html("<a href='/admin/api/hotel/{}/'>{}</a>", obj.hotel.id, obj.hotel)
    hotel_link.short_description = 'Hotel'
    
    def qr_code_image(self, obj):
        if obj.qr_code:
            return format_html('''
                <div style="position: relative; display: inline-block;">
                    <img src="{}" style="height: 100px; display: block;" />
                    <a href="{}" download style="
                        position: absolute;
                        top: 0;
                        left: 0;
                        width: 100%;
                        height: 100%;
                        background: rgba(0, 0, 0, 0.5);
                        color: white;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        text-decoration: none;
                        opacity: 0;
                        transition: opacity 0.3s;
                    " onmouseover="this.style.opacity=1" onmouseout="this.style.opacity=0">
                        ⬇ Download
                    </a>
                </div>
            ''', obj.qr_code.url, obj.qr_code.url)
        return "-"
    qr_code_image.short_description = "QR Code"


# --- Registration ---
# Unregister default Group model
try:
    admin.site.unregister(Group)
except admin.sites.NotRegistered:
    pass

# Register all models with their custom admins
models_to_register = [
    (RentalCompany, RentalCompanyAdmin),
    (Guest, GuestAdmin),
    (Booking, BookingAdmin),
    (Payment, PaymentAdmin),
    (Hotel, HotelAdmin),
    (Car, CarAdmin),  # No custom admin
    (CarHotelLink, CarHotelLinkAdmin),
    (CustomerPaymentMethod, CustomerPaymentMethodAdmin)
]

for model, admin_class in models_to_register:
    try:
        admin.site.unregister(model)
    except admin.sites.NotRegistered:
        pass
    if admin_class:
        admin.site.register(model, admin_class)
    else:
        admin.site.register(model)