from django.utils.timezone import localtime
from django import forms
from django.contrib import admin
from django.contrib import messages
from django.utils.html import format_html
from django.db.models import Sum
from django.db import transaction
from django.contrib.auth.models import Group
from django.apps import apps
from django.core.mail import send_mail
from django.conf import settings
import requests
import stripe
from api.rental_company.models import RentalCompany
from api.hotel.models import Hotel
from api.guest.models import Guest
from api.booking.models import Booking
from api.garage.models import Car
from api.linkCarandHotel.models import CarHotelLink
from api.bookingConflict.models import BookingConflict
from api.booking.email_service import Email
from payments.challan.models import TrafficFine
from payments.models import  Payment

class CustomAdminSite(admin.AdminSite):
    site_header = "Booking Management System"
    site_title = "Admin Portal"
    index_title = "Dashboard"

    def get_app_list(self, request, app_label=None):
        # Build the default app dictionary
        app_dict = self._build_app_dict(request)
        
        # Create our custom groupings
        custom_groups = [
            {
                'name': 'Setup',
                'app_label': 'Management',
                'models': self._get_models_for_group(app_dict, ['Car', 'CarHotelLink', 'Hotel', 'BookingConflict'])
            },
            {
                'name': 'Management',
                'app_label': 'booking_system',
                'models': self._get_models_for_group(app_dict, ['Booking', 'Payment', 'RentalCompany', 'Guest', 'TrafficFine'])
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

@admin.register(TrafficFine, site=admin.site)
class TrafficFineAdmin(admin.ModelAdmin):
    list_display = ('booking', 'amount', 'reason', 'created_at', 'charged_payment')
    readonly_fields = ('charged_payment',)
    search_fields = (
        'booking__guest__first_name', 
        'booking__guest__last_name',
    )
    list_filter = ('created_at',)
    raw_id_fields = ('booking',)  # Removed 'car' from raw_id_fields

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('booking', 'booking__guest')  # Removed 'car' from select_related

    def save_model(self, request, obj, form, change):
        # Only attempt to charge if it hasn't been charged and was just saved
        super().save_model(request, obj, form, change)

        if not obj.charged_payment:
            try:
                obj.charge_fine()
                self.message_user(request, f"Successfully charged fine for booking {obj.booking.id}", messages.SUCCESS)
            except Exception as e:
                self.message_user(request, f"Error charging fine: {e}", messages.ERROR)

    def charge_selected_fines(self, request, queryset):
        for fine in queryset:
            if fine.charged_payment:
                self.message_user(request, f"Fine for booking {fine.booking.id} already charged.", messages.WARNING)
                continue
            try:
                fine.charge_fine()
                self.message_user(request, f"Successfully charged fine for booking {fine.booking.id}", messages.SUCCESS)
            except Exception as e:
                self.message_user(request, f"Error charging fine for booking {fine.booking.id}: {e}", messages.ERROR)

    charge_selected_fines.short_description = "Charge selected traffic fines"

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
    
    

class BookingConflictForm(forms.ModelForm):
    hotel_car_choice = forms.ChoiceField(
        choices=[],
        required=False,
        label="Available Hotels & Cars",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    class Meta:
        model = BookingConflict
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['hotel_car_choice'].choices = self.get_available_options()

    def get_available_options(self):
        choices = [("", "--- Select a hotel and car ---")]
        instance = self.instance

        if instance and instance.conflicting_booking:
            booking = instance.conflicting_booking
            hotel = booking.hotel
            lat = getattr(hotel, 'latitude', None)
            lon = getattr(hotel, 'longitude', None)

            if not lat or not lon:
                return choices

            try:
                url = self.build_nearby_hotels_url(lat, lon, booking.start_time, booking.end_time)
                response = requests.get(url)
                response.raise_for_status()
                choices.extend(self.parse_api_response(response.json()))
            except requests.RequestException as e:
                print(f"Error fetching hotel data: {e}")
            except Exception as e:
                print(f"Unexpected error: {e}")

        return choices

    def build_nearby_hotels_url(self, lat, lon, start_time, end_time):
        return (
            f'http://localhost:8000/hotels/nearby/?lat={lat}&lon={lon}'
            f'&radius=2&start_time={start_time.strftime("%Y-%m-%dT%H:%M:%SZ")}'
            f'&end_time={end_time.strftime("%Y-%m-%dT%H:%M:%SZ")}'
        )

    def parse_api_response(self, data):
        options = []
        for hotel in data.get('results', []):
            if not hotel.get('available_linked_cars'):
                continue
                
            for car in hotel.get('available_linked_cars', []):
                if car.get('status') != 'available':
                    continue
                    
                option_value = f"{hotel['id']}|{car['id']}"
                option_label = (
                    f"{hotel['name']} ({hotel.get('distance_km', 0):.2f} km) - "
                    f"{car['model']} ({car.get('plate_number', 'N/A')}) - "
                    f"{hotel.get('location', 'N/A')}"
                )
                options.append((option_value, option_label))
        return options



@admin.register(BookingConflict)
class BookingConflictAdmin(admin.ModelAdmin):
    list_display = (
        'original_booking_display',
        'conflicting_booking_display',
        'status',
        'created_at',
    )
    search_fields = (
        'original_booking__id',
        'original_booking__guest__first_name',
        'conflicting_booking__id',
        'conflicting_booking__guest__first_name',
    )
    list_filter = ('status', 'created_at')
    raw_id_fields = ('original_booking', 'conflicting_booking')
    actions = ['mark_as_cancelled']
    form = BookingConflictForm  # Use the custom form here

    def original_booking_display(self, obj):
        booking = obj.original_booking
        guest = booking.guest
        return f"{booking.id} - {guest.first_name} {guest.last_name} ({guest.phone})"
    original_booking_display.short_description = 'Original Booking'

    def conflicting_booking_display(self, obj):
        booking = obj.conflicting_booking
        guest = booking.guest
        return f"{booking.id} - {guest.first_name} {guest.last_name} ({guest.phone})"
    conflicting_booking_display.short_description = 'Conflicting Booking'

    def save_model(self, request, obj, form, change):

        with transaction.atomic():
            if change and 'status' in form.changed_data:
                if obj.status == BookingConflict.STATUS_CANCELLED:
                    if obj.conflicting_booking.status == Booking.STATUS_PENDING_CONFLICT:
                        # Update booking status
                        Booking.objects.filter(id=obj.conflicting_booking.id).update(
                            status=Booking.STATUS_CANCELLED
                        )
                        # Process refund
                        self._process_refund(request, obj.conflicting_booking)
                        self._send_cancellation_email(request, obj.conflicting_booking)

                    if obj.original_booking.status == Booking.STATUS_PENDING_CONFLICT:
                        Booking.objects.filter(id=obj.original_booking.id).update(
                            status=Booking.STATUS_CONFIRMED
                        )

                elif change and obj.status == BookingConflict.STATUS_RESOLVED:
                    selected_option = form.cleaned_data.get("hotel_car_choice")
                    if selected_option:
                        try:
                            
                            hotel_id, car_id = selected_option.split('|')
                            print(f"Selected hotel ID: {hotel_id}, car ID: {car_id}")
                            obj.conflicting_booking.hotel_id = hotel_id
                            obj.conflicting_booking.vehicle_id = car_id  # ✅ correct field
                            obj.conflicting_booking.status = 'active'
                            obj.conflicting_booking.save()
                            email_service = Email()
                            email_service.send_conflict_resolved_email(obj.conflicting_booking)
                        except ValueError:
                            self.message_user(request, "Invalid selection format", level='error')
        
        super().save_model(request, obj, form, change)

    def mark_as_cancelled(self, request, queryset):
        with transaction.atomic():
            updated_count = 0
            for conflict in queryset:
                if conflict.status == BookingConflict.STATUS_PENDING:
                    BookingConflict.objects.filter(id=conflict.id).update(
                        status=BookingConflict.STATUS_CANCELLED
                    )
                    if conflict.conflicting_booking.status == Booking.STATUS_PENDING_CONFLICT:
                        Booking.objects.filter(id=conflict.conflicting_booking.id).update(
                            status=Booking.STATUS_CANCELLED
                        )
                        self._process_refund(request, conflict.conflicting_booking)
                        self._send_cancellation_email(request, conflict.conflicting_booking)
                        updated_count += 1

                    if conflict.original_booking.status == Booking.STATUS_PENDING_CONFLICT:
                        Booking.objects.filter(id=conflict.original_booking.id).update(
                            status=Booking.STATUS_CONFIRMED
                        )

            self.message_user(request, f"Successfully cancelled {updated_count} conflict(s) and affected pending bookings.")

    def _process_refund(self, request, booking):
        """Process Stripe refund for the cancelled booking (conflicting only)"""
        try:
            # Double check we are refunding only the conflicting booking
            booking.refresh_from_db()
            if booking.status != Booking.STATUS_CANCELLED:
                self.message_user(
                    request,
                    f"Booking {booking.id} is not marked as cancelled. Skipping refund.",
                    level=messages.WARNING
                )
                return

            # Get the most recent successful initial payment for THIS booking only
            payment = Payment.objects.filter(
                booking_id=booking.id,
                status='succeeded',
                payment_type='initial'
            ).order_by('-created_at').first()

            if not payment:
                self.message_user(
                    request,
                    f"No successful payment found for booking {booking.id}",
                    level=messages.WARNING
                )
                return

            # Double-check that the payment intent isn't reused across other bookings
            shared_intents = Payment.objects.filter(
                stripe_payment_intent_id=payment.stripe_payment_intent_id
            ).exclude(booking_id=booking.id)

            if shared_intents.exists():
                self.message_user(
                    request,
                    f"⚠️ Warning: Payment intent {payment.stripe_payment_intent_id} is shared by other bookings. Aborting refund to prevent accidental multi-refund.",
                    level=messages.ERROR
                )
                return

            # Process the refund via Stripe
            if payment.stripe_payment_intent_id:
                refund = stripe.Refund.create(
                    payment_intent=payment.stripe_payment_intent_id,
                    reason='requested_by_customer'
                )
                payment.status = 'refunded'
                payment.save()

                self.message_user(
                    request,
                    f"✅ Successfully refunded booking {booking.id}. Refund ID: {refund.id}"
                )
            else:
                self.message_user(
                    request,
                    f"No payment intent found for booking {booking.id}",
                    level=messages.WARNING
                )

        except stripe.error.StripeError as e:
            self.message_user(
                request,
                f"Stripe error during refund of booking {booking.id}: {str(e)}",
                level=messages.ERROR
            )
        except Exception as e:
            self.message_user(
                request,
                f"Unexpected error while refunding booking {booking.id}: {str(e)}",
                level=messages.ERROR
            )



    mark_as_cancelled.short_description = "Mark selected conflicts as cancelled (only if pending, and cancel pending bookings)"

class BookingAdmin(admin.ModelAdmin):
    form = BookingForm
    list_display = ('id', 'guest_full_name', 'vehicle', 'hotel', 'start_time', 'end_time', 'buffer_time', 'status')
    list_filter = ('hotel', 'vehicle', 'status')  # Date filtering
    search_fields = ('guest__first_name', 'guest__last_name','vehicle__plate_number')
    date_hierarchy = 'start_time'  # Optional date drilldown

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
class HotelAdminForm(forms.ModelForm):
    class Meta:
        model = Hotel
        fields = '__all__'

    class Media:
        js = (
            'https://code.jquery.com/jquery-3.6.0.min.js',
            '/static/js/admin_location_autocomplete.js',  # You'll create this
        )
class HotelAdmin(admin.ModelAdmin):
    form = HotelAdminForm

    list_display = (
        'name', 'location', 'phone', 'email', 'qr_code_preview', 
        'total_earnings', 'latitude', 'longitude'
    )
    search_fields = ('name', 'location', 'phone', 'email')
    list_filter = ('rental_company', 'location')
    list_editable = ('phone', 'email')
    list_per_page = 20
    autocomplete_fields = ['rental_company']  # This now works with RentalCompanyAdmin

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'location', 'rental_company', 'latitude', 'longitude')
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

        # Ensure geocoding is done if location is set and latitude/longitude are not present
        if obj.location and not obj.latitude and not obj.longitude:
            obj.geocode_address()

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
    (TrafficFine, TrafficFineAdmin),
    (BookingConflict, BookingConflictAdmin),


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