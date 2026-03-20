import hashlib
import hmac
import json
import logging

import razorpay
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view

from bookings.models import Booking, Payment, PaymentWebhookEvent
from bookings.services import LOCK_WINDOW, mark_booking_confirmed, release_expired_locks
from django.db import transaction

logger = logging.getLogger(__name__)

client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))


def _booking_expired(booking):
    return booking.created_at <= timezone.now() - LOCK_WINDOW


def _sync_payment_record(booking, provider_payment_id, status):
    Payment.objects.update_or_create(
        booking=booking,
        defaults={
            'stripe_charge_id': provider_payment_id,
            'amount': booking.total_amount,
            'status': status,
        },
    )


@api_view(['POST'])
def create_razorpay_order(request):
    """
    Create a Razorpay order for a pending booking, reusing an existing order id when present.
    """
    booking_id = request.data.get('booking_id')
    try:
        release_expired_locks()
        booking = Booking.objects.select_related('show__movie', 'user').get(id=booking_id, booking_status='pending')

        if _booking_expired(booking):
            booking.booking_status = 'expired'
            booking.save(update_fields=['booking_status'])
            return JsonResponse({'error': 'Booking session expired. Please select seats again.'}, status=400)

        if booking.payment_id:
            return JsonResponse({
                'order_id': booking.payment_id,
                'amount': int(booking.total_amount * 100),
                'currency': 'INR',
                'key_id': settings.RAZORPAY_KEY_ID,
                'name': "Movie Magic" if not booking.payment_id.startswith('order_mock_') else "Movie Magic (MOCK)",
                'description': f"Tickets for {booking.show.movie.title}",
                'booking_id': booking.id,
                'user_email': booking.user.email,
                'user_name': booking.user.username,
                'mock': booking.payment_id.startswith('order_mock_'),
            })

        if settings.RAZORPAY_KEY_ID == "rzp_test_sample":
            mock_order_id = f"order_mock_{booking.id}"
            booking.payment_id = mock_order_id
            booking.save(update_fields=['payment_id'])

            return JsonResponse({
                'order_id': mock_order_id,
                'amount': int(booking.total_amount * 100),
                'currency': 'INR',
                'key_id': settings.RAZORPAY_KEY_ID,
                'name': "Movie Magic (MOCK)",
                'description': f"Tickets for {booking.show.movie.title}",
                'booking_id': booking.id,
                'user_email': booking.user.email,
                'user_name': booking.user.username,
                'mock': True,
            })

        order_data = {
            'amount': int(booking.total_amount * 100),
            'currency': 'INR',
            'receipt': f'receipt_{booking.id}',
            'payment_capture': 1,
            'notes': {'booking_id': str(booking.id)},
        }
        razorpay_order = client.order.create(data=order_data)
        booking.payment_id = razorpay_order['id']
        booking.save(update_fields=['payment_id'])

        return JsonResponse({
            'order_id': razorpay_order['id'],
            'amount': order_data['amount'],
            'currency': order_data['currency'],
            'key_id': settings.RAZORPAY_KEY_ID,
            'name': "Movie Magic",
            'description': f"Tickets for {booking.show.movie.title}",
            'booking_id': booking.id,
            'user_email': booking.user.email,
            'user_name': booking.user.username,
        })
    except Booking.DoesNotExist:
        return JsonResponse({'error': 'Pending booking not found.'}, status=404)
    except Exception as exc:
        logger.exception("Error creating Razorpay order")
        return JsonResponse({'error': str(exc)}, status=400)


@csrf_exempt
@api_view(['POST'])
def razorpay_webhook(request):
    """
    Verify webhook signature, deduplicate events, and confirm the booking atomically.
    """
    payload = request.body.decode('utf-8')
    signature = request.META.get('HTTP_X_RAZORPAY_SIGNATURE', '')
    if not signature:
        return HttpResponse("Signature missing", status=400)

    expected_signature = hmac.new(
        settings.RAZORPAY_WEBHOOK_SECRET.encode('utf-8'),
        payload.encode('utf-8'),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected_signature, signature):
        logger.warning("Invalid Razorpay webhook signature")
        return HttpResponse("Invalid signature", status=400)

    try:
        data = json.loads(payload)
        event_type = data.get('event', '')
        order_id = data.get('payload', {}).get('order', {}).get('entity', {}).get('id', '')
        payment_id = data.get('payload', {}).get('payment', {}).get('entity', {}).get('id', '')
        event_key = f"{event_type}:{order_id}:{payment_id}"

        with transaction.atomic():
            event, created = PaymentWebhookEvent.objects.select_for_update().get_or_create(
                provider='razorpay',
                event_key=event_key,
                defaults={
                    'event_type': event_type,
                    'signature': signature,
                    'payload': data,
                    'status': 'received',
                },
            )
            if not created and event.status == 'processed':
                return HttpResponse("Already processed", status=200)

            if event_type != 'order.paid':
                event.status = 'ignored'
                event.payload = data
                event.signature = signature
                event.save(update_fields=['status', 'payload', 'signature'])
                return HttpResponse("Event ignored", status=200)

            booking = Booking.objects.select_for_update().prefetch_related('seats').get(payment_id=order_id)
            if booking.booking_status in ['cancelled', 'expired']:
                event.status = 'failed'
                event.error_message = f"Booking {booking.id} is {booking.booking_status}"
                event.save(update_fields=['status', 'error_message'])
                return HttpResponse("Booking no longer payable", status=409)

            mark_booking_confirmed(booking, payment_id)
            _sync_payment_record(booking, payment_id, 'captured')

            event.status = 'processed'
            event.payload = data
            event.signature = signature
            event.processed_at = timezone.now()
            event.error_message = ''
            event.save(update_fields=['status', 'payload', 'signature', 'processed_at', 'error_message'])

        return HttpResponse("Success", status=200)
    except Booking.DoesNotExist:
        logger.warning("Booking not found for webhook")
        return HttpResponse("Booking not found", status=404)
    except Exception as exc:
        logger.exception("Webhook error")
        return HttpResponse(str(exc), status=500)


@api_view(['POST'])
def verify_payment(request):
    """
    Client-side verification as a backup path. Signature verification is still enforced server-side.
    """
    razorpay_order_id = request.data.get('razorpay_order_id')
    razorpay_payment_id = request.data.get('razorpay_payment_id')
    razorpay_signature = request.data.get('razorpay_signature')

    if not all([razorpay_order_id, razorpay_payment_id, razorpay_signature]):
        return JsonResponse({'status': 'failure', 'error': 'Missing payment verification fields.'}, status=400)

    params_dict = {
        'razorpay_order_id': razorpay_order_id,
        'razorpay_payment_id': razorpay_payment_id,
        'razorpay_signature': razorpay_signature,
    }

    try:
        if not razorpay_order_id.startswith('order_mock_'):
            client.utility.verify_payment_signature(params_dict)

        with transaction.atomic():
            booking = Booking.objects.select_for_update().prefetch_related('seats').get(payment_id=razorpay_order_id)
            if booking.booking_status in ['cancelled', 'expired']:
                return JsonResponse({'status': 'failure', 'error': 'Booking can no longer be confirmed.'}, status=409)

            mark_booking_confirmed(booking, razorpay_payment_id)
            _sync_payment_record(booking, razorpay_payment_id, 'captured')

        return JsonResponse({'status': 'success'})
    except Booking.DoesNotExist:
        return JsonResponse({'status': 'failure', 'error': 'Booking not found.'}, status=404)
    except Exception as exc:
        logger.exception("Payment verification failed")
        return JsonResponse({'status': 'failure', 'error': str(exc)}, status=400)
