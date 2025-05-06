from django.urls import path


from . import views

urlpatterns = [
    path('stripe/webhook/', views.stripe_webhook, name='stripe_webhook'),
    path('stripe-session/<str:session_id>/', views.stripe_session_detail),
    path('create-checkout-session/', views.create_checkout_session, name='create_checkout_session'),
    path('create-extension-checkout-session/', views.create_extension_checkout_session, name='create_extension_checkout_session'),
    path('charge-fine/<uuid:booking_id>/', views.charge_fine, name='charge_fine'),
    
    # path('create-setup-intent/', views.create_setup_intent, name='create_setup_intent'),
    # path('save-payment-method/', views.save_payment_method, name='save_payment_method'),
    # path('charge-saved-card/', views.charge_saved_card, name='charge_saved_card'),



]
