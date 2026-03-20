import logging
from datetime import timedelta

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db import transaction
from django.db.models import Q
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.html import strip_tags

from .models import Booking, EmailDelivery, SeatReservation

logger = logging.getLogger(__name__)

LOCK_WINDOW = timedelta(minutes=2)
EMAIL_MAX_ATTEMPTS = 3


def release_expired_locks():
    now = timezone.now()
    expired_count = SeatReservation.objects.filter(
        status='locked',
        locked_until__lte=now,
    ).update(status='expired')

    expired_booking_count = Booking.objects.filter(
        booking_status='pending',
        created_at__lte=now - LOCK_WINDOW,
    ).update(booking_status='expired')

    return {
        'expired_locks': expired_count,
        'expired_bookings': expired_booking_count,
    }


def mark_booking_confirmed(booking, provider_payment_id):
    if booking.booking_status == 'confirmed':
        return booking

    booking.booking_status = 'confirmed'
    booking.idempotency_key = provider_payment_id
    booking.save(update_fields=['booking_status', 'idempotency_key'])

    SeatReservation.objects.filter(
        show=booking.show,
        seat__in=booking.seats.all(),
        status='locked',
    ).update(status='booked')

    queue_booking_confirmation_email(booking)
    return booking


def queue_booking_confirmation_email(booking):
    if not booking.user.email:
        logger.warning("Skipping booking confirmation email for booking %s: missing user email", booking.id)
        return None

    delivery, created = EmailDelivery.objects.get_or_create(
        booking=booking,
        recipient_email=booking.user.email,
        template_name='emails/booking_confirmation.html',
        defaults={
            'subject': f"Booking Confirmed: {booking.show.movie.title}",
            'status': 'pending',
            'next_retry_at': timezone.now(),
        },
    )

    if not created and delivery.status == 'sent':
        return delivery

    if not created:
        delivery.subject = f"Booking Confirmed: {booking.show.movie.title}"
        delivery.status = 'pending'
        delivery.next_retry_at = timezone.now()
        delivery.last_error = ''
        delivery.save(update_fields=['subject', 'status', 'next_retry_at', 'last_error', 'updated_at'])

    return delivery


def send_due_email_deliveries(batch_size=25):
    now = timezone.now()
    due_ids = list(
        EmailDelivery.objects.filter(
            Q(status='pending') | Q(status='failed', next_retry_at__lte=now)
        ).order_by('created_at').values_list('id', flat=True)[:batch_size]
    )

    results = {'sent': 0, 'failed': 0}
    for delivery_id in due_ids:
        outcome = _process_single_email_delivery(delivery_id)
        if outcome in results:
            results[outcome] += 1
    return results


def _process_single_email_delivery(delivery_id):
    with transaction.atomic():
        try:
            delivery = EmailDelivery.objects.select_for_update().select_related(
                'booking__user',
                'booking__show__movie',
                'booking__show__screen__theater',
            ).get(id=delivery_id)
        except EmailDelivery.DoesNotExist:
            return None

        if delivery.status == 'sent':
            return None

        if delivery.status == 'failed' and delivery.next_retry_at and delivery.next_retry_at > timezone.now():
            return None

        delivery.status = 'processing'
        delivery.attempts += 1
        delivery.save(update_fields=['status', 'attempts', 'updated_at'])

    booking = delivery.booking
    seats_list = ", ".join(booking.seats.order_by('seat_number').values_list('seat_number', flat=True))
    context = {
        'user': booking.user,
        'movie': booking.show.movie,
        'show': booking.show,
        'booking': booking,
        'seats_list': seats_list,
    }

    try:
        html_content = render_to_string(delivery.template_name, context)
        text_content = strip_tags(html_content)

        email = EmailMultiAlternatives(
            subject=delivery.subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[delivery.recipient_email],
        )
        email.attach_alternative(html_content, "text/html")
        email.send(fail_silently=False)

        delivery.status = 'sent'
        delivery.sent_at = timezone.now()
        delivery.next_retry_at = None
        delivery.last_error = ''
        delivery.save(update_fields=['status', 'sent_at', 'next_retry_at', 'last_error', 'updated_at'])
        logger.info("Email delivery %s sent successfully", delivery.id)
        return 'sent'
    except Exception as exc:
        delay_minutes = min(2 ** delivery.attempts, 30)
        delivery.status = 'failed'
        delivery.last_error = str(exc)
        if delivery.attempts < EMAIL_MAX_ATTEMPTS:
            delivery.next_retry_at = timezone.now() + timedelta(minutes=delay_minutes)
        else:
            delivery.next_retry_at = None
        delivery.save(update_fields=['status', 'last_error', 'next_retry_at', 'updated_at'])
        logger.exception("Email delivery %s failed", delivery.id)
        return 'failed'
