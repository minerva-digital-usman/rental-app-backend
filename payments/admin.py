from django.contrib import admin

from payments.models import CustomerPaymentMethod

class CustomerPaymentMethodAdmin(admin.ModelAdmin):
    list_display = ('booking', 'stripe_payment_method_id', 'card_brand', 'card_last4', 'is_default', 'created_at')
    list_filter = ('card_brand', 'is_default')
    search_fields = ('stripe_payment_method_id', 'card_last4', 'booking__id')
    ordering = ('-created_at',)

admin.site.register(CustomerPaymentMethod, CustomerPaymentMethodAdmin)