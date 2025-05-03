import json
import os
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, JsonResponse
import requests
import stripe
from django.core.mail import send_mail

from api.booking.models import Booking
from payments.models import CustomerPaymentMethod, Payment
from middleware_platform import settings

stripe.api_key = settings.STRIPE_SECRET_KEY
STRIPE_WEBHOOK_SECRET = settings.STRIPE_WEBHOOK_SECRET


@csrf_exempt
def create_checkout_session(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            required_fields = [
                'hotel_name', 'hotel_id', 'pickup_date', 'pickup_time',
                'vehicle_id', 'guest_first_name', 'guest_last_name',
                'guest_email', 'guest_phone', 'guest_fiscal_code',
                'guest_driver_license', 'amount', 'return_date', 'return_time'
            ]
            for field in required_fields:
                if field not in data:
                    return JsonResponse({'error': f'Missing required field: {field}'}, status=400)

            unit_amount = int(float(data['amount']) * 100)
            description = (
                f"Name: {data['guest_first_name']} {data['guest_last_name']}, "
                f"Pickup: {data['pickup_date']} {data['pickup_time']}, "
                f"Return: {data['return_date']} {data['return_time']}"
                f"url:  {data['guest_driver_license']}"
            )

            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': 'eur',
                        'product_data': {
                            'name': f'Hotel Name: {data["hotel_name"]}',
                            'description': description,
                        },
                        'unit_amount': unit_amount,
                    },
                    'quantity': 1,
                }],
                mode='payment',
                success_url=f'{settings.BASE_URL_FRONTEND}/booking-success?session_id={{CHECKOUT_SESSION_ID}}',
                cancel_url=f'{settings.BASE_URL_FRONTEND}/cancel',
                customer_email=data['guest_email'],
                metadata={
                    'hotel_id': data['hotel_id'],
                    'vehicle_id': data['vehicle_id'],
                    'guest_first_name': data['guest_first_name'],
                    'guest_last_name': data['guest_last_name'],
                    'guest_email': data['guest_email'],
                    'guest_phone': data['guest_phone'],
                    'guest_fiscal_code': data['guest_fiscal_code'],
                    'guest_driver_license' : data['guest_driver_license'],
                    'pickup_date': data['pickup_date'],
                    'pickup_time': data['pickup_time'],
                    'return_date': data['return_date'],
                    'return_time': data['return_time'],
                    'amount': data['amount']
                }
            )
            return JsonResponse({'id': session.id})
        except Exception as e:
            print("Stripe error:", str(e))
            return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
def create_extension_checkout_session(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            required_fields = [
                'booking_id', 'hotel_name', 'hotel_id', 'pickup_date', 'pickup_time',
                'vehicle_id', 'guest_first_name', 'guest_last_name',
                'guest_email', 'guest_phone', 'guest_fiscal_code',
                'amount', 'return_date', 'return_time'
            ]
            for field in required_fields:
                if field not in data:
                    return JsonResponse({'error': f'Missing required field: {field}'}, status=400)

            unit_amount = int(float(data['amount']) * 100)
            description = (
                f"Extension for Booking ID: {data['booking_id']}, "
                f"Name: {data['guest_first_name']} {data['guest_last_name']}, "
                f"New Return: {data['return_date']} {data['return_time']}"
            )

            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': 'eur',
                        'product_data': {
                            'name': f'Hotel Name: {data["hotel_name"]}',
                            'description': description,
                        },
                        'unit_amount': unit_amount,
                    },
                    'quantity': 1,
                }],
                mode='payment',
                success_url=f'{settings.BASE_URL_FRONTEND}/booking-extended?session_id={{CHECKOUT_SESSION_ID}}',
                cancel_url=f'{settings.BASE_URL_FRONTEND}/cancel',
                customer_email=data['guest_email'],
                metadata={
                    'booking_id': str(data['booking_id']),
                    'hotel_id': data['hotel_id'],
                    'vehicle_id': data['vehicle_id'],
                    'guest_first_name': data['guest_first_name'],
                    'guest_last_name': data['guest_last_name'],
                    'guest_email': data['guest_email'],
                    'guest_phone': data['guest_phone'],
                    'guest_fiscal_code': data['guest_fiscal_code'],
                    'pickup_date': data['pickup_date'],
                    'pickup_time': data['pickup_time'],
                    'return_date': data['return_date'],
                    'return_time': data['return_time'],
                    'amount': data['amount']
                }
            )
            return JsonResponse({'id': session.id})
        except Exception as e:
            print("Stripe error:", str(e))
            return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
def create_fine_checkout_session(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            required_fields = [
                'booking_id', 'amount', 'reason', 
                'fine_details', 'guest_email'
            ]
            for field in required_fields:
                if field not in data:
                    return JsonResponse({'error': f'Missing required field: {field}'}, status=400)

            # Get booking details
            try:
                booking = Booking.objects.get(id=data['booking_id'])
            except Booking.DoesNotExist:
                return JsonResponse({'error': 'Booking not found'}, status=404)

            unit_amount = int(float(data['amount']) * 100)
            description = (
                f"Traffic fine for Booking ID: {data['booking_id']}\n"
                f"Reason: {data['reason']}\n"
                f"Details: {data['fine_details']}"
            )

            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': 'eur',
                        'product_data': {
                            'name': 'Traffic Fine',
                            'description': description,
                        },
                        'unit_amount': unit_amount,
                    },
                    'quantity': 1,
                }],
                mode='payment',
                success_url=f'{settings.BASE_URL_FRONTEND}/fine-paid?session_id={{CHECKOUT_SESSION_ID}}',
                cancel_url=f'{settings.BASE_URL_FRONTEND}/fine-cancel',
                customer_email=data['guest_email'],
                metadata={
                    'booking_id': str(data['booking_id']),
                    'amount': data['amount'],
                    'reason': data['reason'],
                    'fine_details': data['fine_details'],
                    'payment_type': 'fine'
                }
            )
            return JsonResponse({'id': session.id})
        except Exception as e:
            print("Stripe error:", str(e))
            return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    event = None

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        # Invalid payload
        print(f"⚠️  Webhook error while parsing basic request. {str(e)}")
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        print(f"⚠️  Webhook signature verification failed. {str(e)}")
        return HttpResponse(status=400)
    except Exception as e:
        print(f"⚠️  Webhook error. {str(e)}")
        return HttpResponse(status=400)

    # Handle the event
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        metadata = session.get('metadata', {})
        
        try:
            if 'booking_id' in metadata:
                # Handle extension payment
                handle_extension_payment(session, metadata)
            elif 'payment_type' in metadata and metadata['payment_type'] == 'fine':
                # Handle fine payment through checkout
                handle_fine_payment(session, metadata)
            else:
                # Handle initial booking payment
                handle_initial_booking_payment(session, metadata)
        except Exception as e:
            print(f"⚠️  Error processing checkout.session.completed: {str(e)}")
            return HttpResponse(status=500)

    elif event['type'] == 'setup_intent.succeeded':
        setup_intent = event['data']['object']
        metadata = setup_intent.get('metadata', {})
        
        try:
            if 'booking_id' in metadata and setup_intent.payment_method:
                handle_saved_payment_method(setup_intent, metadata)
        except Exception as e:
            print(f"⚠️  Error processing setup_intent.succeeded: {str(e)}")
            return HttpResponse(status=500)

    elif event['type'] == 'payment_intent.succeeded':
        payment_intent = event['data']['object']
        metadata = payment_intent.get('metadata', {})
        
        try:
            if 'payment_type' in metadata:
                if metadata['payment_type'] == 'fine':
                    handle_off_session_fine_payment(payment_intent, metadata)
        except Exception as e:
            print(f"⚠️  Error processing payment_intent.succeeded: {str(e)}")
            return HttpResponse(status=500)

    elif event['type'] == 'payment_intent.payment_failed':
        payment_intent = event['data']['object']
        metadata = payment_intent.get('metadata', {})
        
        try:
            if 'payment_type' in metadata and metadata['payment_type'] == 'fine':
                handle_failed_fine_payment(payment_intent, metadata)
        except Exception as e:
            print(f"⚠️  Error processing payment_intent.payment_failed: {str(e)}")
            return HttpResponse(status=500)

    elif event['type'] == 'charge.succeeded':
        charge = event['data']['object']
        # You might want to log successful charges here

    elif event['type'] == 'charge.failed':
        charge = event['data']['object']
        # Handle failed charges here

    else:
        # Unexpected event type
        print(f"Unhandled event type {event['type']}")

    return HttpResponse(status=200)


# Helper functions for each payment type

import os
import uuid
import requests
import stripe

from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.conf import settings


def handle_initial_booking_payment(session, metadata):
    """Process initial booking payment after successful checkout"""

    # ✅ Move driver license image from temp to permanent folder
    if 'guest_driver_license' in metadata:
        temp_path = metadata['guest_driver_license'].replace(settings.MEDIA_URL, '')
        if default_storage.exists(temp_path):
            ext = os.path.splitext(temp_path)[-1]
            new_filename = f"driver_licenses/{uuid.uuid4()}{ext}"
            file_content = default_storage.open(temp_path).read()
            default_storage.save(new_filename, ContentFile(file_content))
            default_storage.delete(temp_path)
            # ✅ Update metadata with new permanent URL
            metadata['guest_driver_license'] = default_storage.url(new_filename)

    # ✅ Build booking data using updated metadata
    start_time = f"{metadata['pickup_date']} {metadata['pickup_time']}:00"
    end_time = f"{metadata['return_date']} {metadata['return_time']}:00"

    booking_data = {
        "vehicle_id": metadata['vehicle_id'],
        "hotel_id": metadata['hotel_id'],
        "start_time": start_time,
        "end_time": end_time,
        "guest": {
            "first_name": metadata['guest_first_name'],
            "last_name": metadata['guest_last_name'],
            "email": metadata['guest_email'],
            "phone": metadata['guest_phone'],
            "fiscal_code": metadata['guest_fiscal_code'],
            "driver_license": metadata['guest_driver_license']
        }
    }

    try:
        # 1. Create the booking
        response = requests.post(
            f'{settings.BASE_URL_BACKEND}/api/bookings/',
            json=booking_data,
            headers={'Content-Type': 'application/json'}
        )
        response.raise_for_status()
        booking_id = response.json()['id']
        booking = Booking.objects.get(id=booking_id)
        metadata['booking_id'] = booking_id

        # 2. Create payment record
        payment = Payment.objects.create(
            booking=booking,
            stripe_session_id=session['id'],
            amount=float(metadata['amount']),
            status='succeeded',
            payment_type='initial'
        )

        # 3. Retrieve the payment method used in this session
        payment_intent = stripe.PaymentIntent.retrieve(session.payment_intent)
        if payment_intent.payment_method:
            payment_method = stripe.PaymentMethod.retrieve(payment_intent.payment_method)

            # 4. Save the payment method for future use
            CustomerPaymentMethod.objects.create(
                booking=booking,
                stripe_payment_method_id=payment_method.id,
                card_brand=payment_method.card.brand,
                card_last4=payment_method.card.last4,
                is_default=True
            )

            # 5. Update payment with method info
            payment.stripe_payment_method_id = payment_method.id
            payment.save()

        # 6. Send confirmation email
        send_booking_confirmation(metadata)

    except Exception as e:
        print(f"Booking creation failed: {e}")
        raise


def handle_extension_payment(session, metadata):
    """Process booking extension payment after successful checkout"""
    booking_id = metadata['booking_id']
    return_date = metadata['return_date']
    return_time = metadata['return_time']
    new_end_time = f"{return_date} {return_time}:00"
    
    try:
        # 1. Update booking extension
        response = requests.patch(
            f'{settings.BASE_URL_BACKEND}/api/booking/{booking_id}/extend/',
            json={"new_end_time": new_end_time},
            headers={'Content-Type': 'application/json'}
        )
        response.raise_for_status()
        
        booking = Booking.objects.get(id=booking_id)
        
        # 2. Create payment record
        payment = Payment.objects.create(
            booking=booking,
            stripe_session_id=session['id'],
            amount=float(metadata['amount']),
            status='succeeded',
            payment_type='extension'
        )

        # 3. Retrieve and save the payment method if a new card was used
        payment_intent = stripe.PaymentIntent.retrieve(session.payment_intent)
        if payment_intent.payment_method:
            payment_method = stripe.PaymentMethod.retrieve(payment_intent.payment_method)
            
            # Check if this payment method is already saved
            if not CustomerPaymentMethod.objects.filter(
                booking=booking,
                stripe_payment_method_id=payment_method.id
            ).exists():
                # Save the new payment method
                CustomerPaymentMethod.objects.create(
                    booking=booking,
                    stripe_payment_method_id=payment_method.id,
                    card_brand=payment_method.card.brand,
                    card_last4=payment_method.card.last4,
                    is_default=True  # Set as default for future payments
                )
            
            # Update payment record with payment method info
            payment.stripe_payment_method_id = payment_method.id
            payment.save()

        # 4. Send extension confirmation email
        send_extension_confirmation(booking, metadata)
        
    except Exception as e:
        print(f"Error processing extension for booking {booking_id}: {e}")
        raise

def handle_fine_payment(session, metadata):
    """Process fine payment after successful checkout"""
    booking_id = metadata['booking_id']
    
    try:
        booking = Booking.objects.get(id=booking_id)
        
        Payment.objects.create(
            booking=booking,
            stripe_session_id=session['id'],
            amount=float(metadata['amount']),
            status='succeeded',
            payment_type='fine',
            fine_reason=metadata.get('reason'),
            fine_details=metadata.get('fine_details')
        )
        
        # Update booking with fine payment status
        booking.fine_paid = True
        booking.save()
        
        # Send fine payment confirmation
        send_fine_payment_confirmation(booking, metadata)
        
    except Exception as e:
        print(f"Error processing fine payment for booking {booking_id}: {e}")
        raise

def handle_saved_payment_method(setup_intent, metadata):
    """Save customer's payment method for future use"""
    booking_id = metadata['booking_id']
    payment_method_id = setup_intent.payment_method
    
    try:
        booking = Booking.objects.get(id=booking_id)
        payment_method = stripe.PaymentMethod.retrieve(payment_method_id)
        
        if payment_method.type == 'card':
            # Set all other payment methods for this booking as non-default
            CustomerPaymentMethod.objects.filter(booking=booking).update(is_default=False)
            
            # Create new payment method record
            CustomerPaymentMethod.objects.create(
                booking=booking,
                stripe_payment_method_id=payment_method.id,
                card_brand=payment_method.card.brand,
                card_last4=payment_method.card.last4,
                is_default=True
            )
            
            # Send confirmation that card was saved
            send_payment_method_confirmation(booking, payment_method)
            
    except Exception as e:
        print(f"Error saving payment method for booking {booking_id}: {e}")
        raise

def handle_off_session_fine_payment(payment_intent, metadata):
    """Process successful fine payment using saved card"""
    booking_id = metadata['booking_id']
    
    try:
        booking = Booking.objects.get(id=booking_id)
        
        Payment.objects.create(
            booking=booking,
            stripe_payment_intent_id=payment_intent['id'],
            amount=float(payment_intent['amount'] / 100),
            status='succeeded',
            payment_type='fine',
            fine_reason=metadata.get('reason'),
            fine_details=metadata.get('fine_details')
        )
        
        # Update booking with fine payment status
        booking.fine_paid = True
        booking.save()
        
        # Send fine payment confirmation
        send_fine_payment_confirmation(booking, metadata)
        
    except Exception as e:
        print(f"Error processing off-session fine payment for booking {booking_id}: {e}")
        raise


def handle_failed_fine_payment(payment_intent, metadata):
    """Handle failed fine payment attempt using saved card"""
    booking_id = metadata['booking_id']
    last_payment_error = payment_intent.get('last_payment_error', {})
    
    try:
        booking = Booking.objects.get(id=booking_id)
        guest = booking.guest  # assuming booking.guest exists

        # Delete the driver's license image file (if stored locally)
        if guest.driver_license:
            file_path = os.path.join(settings.MEDIA_ROOT, guest.driver_license)
            if os.path.isfile(file_path):
                os.remove(file_path)
                print(f"Deleted driver's license image: {file_path}")
            guest.driver_license = ""  # Clear the driver's license field
            guest.save()

        # Log the failed payment attempt
        Payment.objects.create(
            booking=booking,
            stripe_payment_intent_id=payment_intent['id'],
            amount=float(payment_intent['amount'] / 100),
            status='failed',
            payment_type='fine',
            failure_reason=last_payment_error.get('message'),
            failure_code=last_payment_error.get('code')
        )
        
        # Notify admin and customer about the failed payment
        notify_failed_fine_payment(booking, metadata, last_payment_error)
        
    except Exception as e:
        print(f"Error processing failed fine payment for booking {booking_id}: {e}")
        raise

# Email notification functions (implement these according to your email service)

def send_booking_confirmation(metadata):
    """Send an elegant booking confirmation email using Stripe metadata"""
    
    subject = f"Booking Confirmation: {metadata.get('company_name', 'Our Car Rental Service')} - Reference #{metadata.get('booking_id', '')}"

    message = f"""
    Dear {metadata.get('guest_first_name', 'Valued Customer')} {metadata.get('guest_last_name', '')},

    We are delighted to confirm your reservation with {metadata.get('company_name', 'Our Premium Car Rental Service')}. 
    Your booking has been successfully processed, and we look forward to serving you.

    Booking Summary:
    ============================================
    - Booking Reference: {metadata.get('booking_id', 'N/A')}
    - Vehicle Pickup: {metadata.get('pickup_date', '')} at {metadata.get('pickup_time', '')}
    - Vehicle Return: {metadata.get('return_date', '')} at {metadata.get('return_time', '')}
    - Total Amount: €{metadata.get('amount', 'N/A')}
    ============================================

    
    We appreciate your trust in our services and wish you pleasant travels.

    With warm regards,
    {metadata.get('company_name', 'The Car Rental Service')} Team

   
    """

    recipient = metadata.get('guest_email')

    if recipient:
        send_mail(
            subject,
            message.strip(),
            settings.DEFAULT_FROM_EMAIL,
            [recipient],
            fail_silently=False,
        )

def send_extension_confirmation(booking, metadata):
    """Send booking extension confirmation email"""

    subject = f"Booking Extension Confirmation: {metadata.get('company_name', 'Our Car Rental Service')} - Reference #{metadata.get('booking_id', '')}"

    message = f"""
    Dear {metadata.get('guest_first_name', 'Valued Customer')} {metadata.get('guest_last_name', '')},

    We are pleased to confirm that your booking extension has been successfully processed with {metadata.get('company_name', 'Our Premium Car Rental Service')}. 
    We are happy to continue providing you with our services.

    Extended Booking Summary:
    ============================================
    - Booking Reference: {metadata.get('booking_id', 'N/A')}
    - New Vehicle Return: {metadata.get('return_date', '')} at {metadata.get('return_time', '')}
    - Total Amount: €{metadata.get('amount', 'N/A')}
    ============================================

   

    We thank you for your continued trust in our services and wish you safe travels.

    With warm regards,
    {metadata.get('company_name', 'The Car Rental Service')} Team
    """

    recipient = metadata.get('guest_email')

    if recipient:
        send_mail(
            subject,
            message.strip(),
            settings.DEFAULT_FROM_EMAIL,
            [recipient],
            fail_silently=False,
        )


def send_fine_payment_confirmation(booking, metadata):
    """Send fine payment confirmation email"""
    pass

def send_payment_method_confirmation(booking, payment_method):
    """Send confirmation that payment method was saved"""
    pass

def notify_failed_fine_payment(booking, metadata, error):
    """Notify about failed fine payment"""
    pass


@csrf_exempt
def stripe_session_detail(request, session_id):
    try:
        session = stripe.checkout.Session.retrieve(session_id)
        return JsonResponse({
            'id': session.id,
            'metadata': session.metadata
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)
# api/payment/views.py

@csrf_exempt
def create_setup_intent(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            if 'booking_id' not in data:
                return JsonResponse({'error': 'Missing booking_id'}, status=400)

            # Create a SetupIntent
            setup_intent = stripe.SetupIntent.create(
                payment_method_types=['card'],
                metadata={
                    'booking_id': data['booking_id']
                }
            )
            
            return JsonResponse({
                'client_secret': setup_intent.client_secret,
                'setup_intent_id': setup_intent.id
            })
        except Exception as e:
            print("Stripe error:", str(e))
            return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
def save_payment_method(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            required_fields = ['setup_intent_id', 'booking_id']
            for field in required_fields:
                if field not in data:
                    return JsonResponse({'error': f'Missing required field: {field}'}, status=400)

            # Retrieve the SetupIntent
            setup_intent = stripe.SetupIntent.retrieve(data['setup_intent_id'])
            
            if not setup_intent.payment_method:
                return JsonResponse({'error': 'No payment method attached'}, status=400)

            # Get payment method details
            payment_method = stripe.PaymentMethod.retrieve(setup_intent.payment_method)
            
            if payment_method.type != 'card':
                return JsonResponse({'error': 'Only card payments are supported'}, status=400)

            # Save to database
            booking = Booking.objects.get(id=data['booking_id'])
            CustomerPaymentMethod.objects.create(
                booking=booking,
                stripe_payment_method_id=payment_method.id,
                card_brand=payment_method.card.brand,
                card_last4=payment_method.card.last4
            )
            
            return JsonResponse({'success': True})
        except Exception as e:
            print("Stripe error:", str(e))
            return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
def charge_saved_card(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            required_fields = ['booking_id', 'amount', 'reason', 'fine_details']
            for field in required_fields:
                if field not in data:
                    return JsonResponse({'error': f'Missing required field: {field}'}, status=400)

            # Get the booking and payment method
            booking = Booking.objects.get(id=data['booking_id'])
            payment_method = CustomerPaymentMethod.objects.filter(booking=booking).first()
            
            if not payment_method:
                return JsonResponse({'error': 'No saved payment method found'}, status=400)

            amount = int(float(data['amount']) * 100)
            
            # Create payment intent
            payment_intent = stripe.PaymentIntent.create(
                amount=amount,
                currency='eur',
                payment_method=payment_method.stripe_payment_method_id,
                confirm=True,
                off_session=True,
                metadata={
                    'booking_id': str(data['booking_id']),
                    'reason': data['reason'],
                    'fine_details': data['fine_details'],
                    'payment_type': 'fine'
                }
            )
            
            # Create payment record
            Payment.objects.create(
                booking=booking,
                stripe_payment_intent_id=payment_intent.id,
                amount=float(data['amount']),
                status='succeeded',
                payment_type='fine'
            )
            
            return JsonResponse({'success': True, 'payment_intent_id': payment_intent.id})
        except stripe.error.CardError as e:
            # Handle specific card errors
            err = e.error
            return JsonResponse({
                'error': err.message,
                'code': err.code,
                'decline_code': err.decline_code if hasattr(err, 'decline_code') else None
            }, status=400)
        except Exception as e:
            print("Stripe error:", str(e))
            return JsonResponse({'error': str(e)}, status=500)