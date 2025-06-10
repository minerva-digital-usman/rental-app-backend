import datetime as dt
from datetime import datetime
import json
import os
from venv import logger
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, JsonResponse
import requests
import stripe
from django.core.mail import send_mail
import uuid
import requests
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.conf import settings
import stripe
from api.booking.models import Booking
from payments.models import Payment
from middleware_platform import settings
from api.booking.email_service import Email
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status


stripe.api_key = settings.STRIPE_SECRET_KEY
STRIPE_WEBHOOK_SECRET = settings.STRIPE_WEBHOOK_SECRET
class PaymentAmountAPIView(APIView):
    def get(self, request, booking_id):
        payment = Payment.objects.filter(
            booking_id=booking_id,
            status='succeeded',
            payment_type='initial'
        ).order_by('-created_at').first()
        
        if not payment:
            return Response({"detail": "No successful payment found for booking."}, status=status.HTTP_404_NOT_FOUND)
        
        return Response({"amount": str(payment.amount)}, status=status.HTTP_200_OK)
@csrf_exempt
def create_checkout_session(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            required_fields = [
                'hotel_name','hotel_email' ,'hotel_id','hotel_location' ,'pickup_date', 'pickup_time', 'car_model',
                'vehicle_id', 'guest_first_name', 'guest_last_name',
                'guest_email', 'guest_phone', 'guest_street_address','guest_postal_code','guest_city',
                'guest_driver_license', 'amount', 'return_date', 'return_time','company_name', 'company_email', 'company_phone'
            ]
            for field in required_fields:
                if field not in data:
                    return JsonResponse({'error': f'Missing required field: {field}'}, status=400)

            unit_amount = int(float(data['amount']) * 100)
            description = (
                f"Name: {data['guest_first_name']} {data['guest_last_name']}, "
                # f"car: {data['car_model']}, "
                # f"Company: {data['company_name']}, {data['company_email']}, {data['company_phone']}, "
                # f"Hotel: {data['hotel_location']}, "
                f"Pickup: {data['pickup_date']} {data['pickup_time']}, "
                f"Return: {data['return_date']} {data['return_time']}"
            )

            # Create or retrieve customer
            customer_email = data['guest_email']
            customer = stripe.Customer.list(email=customer_email).data
            
            if customer:
                customer = customer[0]  # Use existing customer
            else:
                customer = stripe.Customer.create(
                    email=customer_email,
                    name=f"{data['guest_first_name']} {data['guest_last_name']}",
                    phone=data['guest_phone'],
                    metadata={
                        'street_address': data['guest_street_address'],
                        'postal_code': data['guest_postal_code'],
                        'city': data['guest_city'],
                      }
                )

            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': 'chf',
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
                customer=customer.id,
                payment_intent_data={
                    'setup_future_usage': 'off_session',  # This is the correct way to set it
                },
                metadata={
                    'hotel_id': data['hotel_id'],
                    'hotel_email':data['hotel_email'],
                    'hotel_location': data['hotel_location'],
                    'vehicle_id': data['vehicle_id'],
                    'guest_first_name': data['guest_first_name'],
                    'guest_last_name': data['guest_last_name'],
                    'guest_email': data['guest_email'],
                    'guest_phone': data['guest_phone'],
                    'guest_street_address': data['guest_street_address'],
                    'guest_postal_code': data['guest_postal_code'],
                    'guest_city': data['guest_city'],
                    'guest_driver_license': data['guest_driver_license'],
                    'pickup_date': data['pickup_date'],
                    'pickup_time': data['pickup_time'],
                    'return_date': data['return_date'],
                    'return_time': data['return_time'],
                    'amount': data['amount'],
                    'company_name': data['company_name'],
                    'company_email': data['company_email'],
                    'company_phone': data['company_phone'],
                    'car_model': data['car_model'],
                    'terms_url': 'https://drive.google.com/file/d/1kCTjFnZ-c8OIq4-UTZTSE2wqdQGIJhJC/preview',
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
                'booking_id', 'hotel_name', 'hotel_id','hotelEmail', 'pickup_date', 'pickup_time',
                'vehicle_id', 'guest_first_name', 'guest_last_name', 'guest_street_address','car_model','companyName',
                'companyEmail', 'companyPhone', 'hotelLocation',
                'guest_email', 'guest_phone', 'guest_street_address','guest_postal_code','guest_city',
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
                # f"Car Model: {data['car_model']}, "
                # f"Company: {data['companyName']}, {data['companyEmail']}, {data['companyPhone']}, "
                # f"Hotel: {data['hotelLocation']}, "
                # f"original return: {data['original_return_time']}"
                
                
            )

            # Get the booking to retrieve the customer ID
            try:
                booking_id = data['booking_id']
                payment = Payment.objects.filter(
                    booking_id=booking_id,
                    stripe_customer_id__isnull=False
                ).order_by('-created_at').first()
                customer_id = payment.stripe_customer_id if payment else None
            except Exception as e:
                customer_id = None


            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': 'chf',
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
                customer=customer_id if customer_id else None,
                customer_email=data['guest_email'] if not customer_id else None,
                metadata={
                    'booking_id': str(data['booking_id']),
                    'hotel_id': data['hotel_id'],
                    'hotel_name': data['hotel_name'],
                     'hotel_email':data['hotelEmail'],
                     'company_name': data['companyName'],
                    'company_email': data['companyEmail'],
                    'company_phone': data['companyPhone'],
                    'car_model': data['car_model'],
                    'hotel_location': data['hotelLocation'],
                    'vehicle_id': data['vehicle_id'],
                    'guest_first_name': data['guest_first_name'],
                    'guest_last_name': data['guest_last_name'],
                    'guest_email': data['guest_email'],
                    'guest_phone': data['guest_phone'],
                    'guest_street_address': data['guest_street_address'],
                    'guest_postal_code': data['guest_postal_code'],
                    'guest_city': data['guest_city'],
                    'pickup_date': data['pickup_date'],
                    'pickup_time': data['pickup_time'],
                    'return_date': data['return_date'],
                    'original_return_time': data.get('original_return_time', ''),  # Optional field
                    'original_return_date': data.get('original_return_date', ''),  # Optional field
                    'return_time': data['return_time'],
                    'amount': data['amount'],
                    'terms_url': 'https://drive.google.com/file/d/1kCTjFnZ-c8OIq4-UTZTSE2wqdQGIJhJC/preview',

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
        print(f"⚠️  Webhook error while parsing basic request. {str(e)}")
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        print(f"⚠️  Webhook signature verification failed. {str(e)}")
        return HttpResponse(status=400)
    except Exception as e:
        print(f"⚠️  Webhook error. {str(e)}")
        return HttpResponse(status=400)

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        metadata = session.get('metadata', {})
        
        try:
            if 'booking_id' in metadata:
                handle_extension_payment(session, metadata)
            else:
                handle_initial_booking_payment(session, metadata)
        except Exception as e:
            print(f"⚠️  Error processing checkout.session.completed: {str(e)}")
            return HttpResponse(status=500)

    return HttpResponse(status=200)


def handle_initial_booking_payment(session, metadata):
    """Process initial booking payment after successful checkout"""
    # Move driver license image from temp to permanent folder
    if 'guest_driver_license' in metadata:
        temp_path = metadata['guest_driver_license'].replace(settings.MEDIA_URL, '')
        if default_storage.exists(temp_path):
            ext = os.path.splitext(temp_path)[-1]
            new_filename = f"driver_licenses/{uuid.uuid4()}{ext}"
            file_content = default_storage.open(temp_path).read()
            default_storage.save(new_filename, ContentFile(file_content))
            default_storage.delete(temp_path)
            metadata['guest_driver_license'] = new_filename

    # Build booking data
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
            "street_address": metadata['guest_street_address'],
            "postal_code": metadata['guest_postal_code'],
            "city": metadata['guest_city'],
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
        
        # Save Stripe customer ID to the booking
        # Check if the customer ID exists in the session
        if session.get('customer'):
            # 1. Create payment record with stripe customer ID
            payment = Payment.objects.create(
                booking=booking,
                stripe_session_id=session['id'],
                stripe_customer_id=session['customer'],  # Storing the customer ID here
                amount=float(metadata['amount']),
                status='succeeded',
                payment_type='initial'
            )
            print(f"Successfully saved Stripe Customer ID: {session['customer']} for payment {payment.id}")
        else:
            print("Warning: No customer ID found in session")


        # 3. Check if the session has a SetupIntent or PaymentIntent
        if session.get('setup_intent'):
            setup_intent = stripe.SetupIntent.retrieve(session['setup_intent'])
            payment.stripe_setup_intent_id = setup_intent.id
            payment_intent = None
        else:
            payment_intent = stripe.PaymentIntent.retrieve(session['payment_intent'])
            payment.stripe_payment_intent_id = payment_intent.id
            setup_intent = None

        # 4. If we have a PaymentMethod, process it
        payment_method = None
        if (payment_intent and payment_intent.payment_method) or (setup_intent and setup_intent.payment_method):
            payment_method_id = payment_intent.payment_method if payment_intent else setup_intent.payment_method
            payment_method = stripe.PaymentMethod.retrieve(payment_method_id)
            
            payment.stripe_payment_method_id = payment_method.id
            payment.payment_method_type = payment_method.type
            if payment_method.type == 'card':
                payment.payment_method_brand = payment_method.card.brand
                payment.payment_method_last4 = payment_method.card.last4

        payment.save()
        extension_link = f"{settings.BASE_URL_FRONTEND}/extend-booking-email/{booking_id}"
        metadata['extension_link'] = extension_link

        # 5. Send confirmation email
        email_client = Email()
        email_client.send_booking_confirmation_email(metadata)
        email_client.send_booking_confirmation_email_to_hotel(metadata)
        email_client.send_booking_notification_to_admin(metadata)

    except Exception as e:
        print(f"Booking creation failed: {e}")
        raise


def handle_extension_payment(session, metadata):
    """Process booking extension payment after successful checkout"""
    booking_id = metadata['booking_id']
    return_date = metadata['return_date']
    return_time = metadata['return_time']
    new_end_time = f"{return_date} {return_time}:00"  # e.g., "2025-06-09 15:30:00"

# Convert to datetime object
    try:
        raw_new_end_time = datetime.strptime(new_end_time, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        logger.error("Invalid date/time format: %s", new_end_time)
        return Response({"detail": "Invalid date/time format."}, status=400)
        
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
        if session.payment_intent:
            payment_intent = stripe.PaymentIntent.retrieve(session.payment_intent)
            payment.stripe_payment_intent_id = payment_intent.id
            
            if payment_intent.payment_method:
                payment_method = stripe.PaymentMethod.retrieve(payment_intent.payment_method)
                payment.stripe_payment_method_id = payment_method.id
                payment.payment_method_type = payment_method.type
                if payment_method.type == 'card':
                    payment.payment_method_brand = payment_method.card.brand
                    payment.payment_method_last4 = payment_method.card.last4

        payment.save()
        extension_link = f"{settings.BASE_URL_FRONTEND}/extend-booking-email/{booking_id}"
        metadata['extension_link'] = extension_link

        # 4. Send extension confirmation email
        # send_extension_confirmation(booking, metadata)
        email_service = Email()
        email_service.send_extension_email(metadata, raw_new_end_time)
        email_service.send_extension_email_to_hotel(metadata, raw_new_end_time)
        email_service.send_extension_email_to_admin(metadata, raw_new_end_time)        
        
    except Exception as e:
        print(f"Error processing extension for booking {booking_id}: {e}")
        raise




@csrf_exempt
def stripe_session_detail(request, session_id):
    try:
        session = stripe.checkout.Session.retrieve(session_id)
        return JsonResponse({
            'id': session.id,
            'metadata': session.metadata,
            'customer': session.customer if hasattr(session, 'customer') else None
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)