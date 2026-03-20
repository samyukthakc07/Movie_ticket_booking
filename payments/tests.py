import hashlib
import hmac
import json
from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from bookings.models import Booking, PaymentWebhookEvent, Seat
from movies.models import Movie, Screen, Show, Theater


@override_settings(RAZORPAY_WEBHOOK_SECRET='test_webhook_secret')
class RazorpayWebhookTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='bob', password='secret', email='bob@example.com')
        theater = Theater.objects.create(name='Razorplex', location='Metro')
        screen = Screen.objects.create(theater=theater, screen_number=1, total_seats=20)
        movie = Movie.objects.create(
            title='Webhook Safe',
            description='Payment movie',
            genre='Action',
            language='English',
            duration=100,
            release_date=timezone.now().date(),
            trailer_url='https://www.youtube.com/watch?v=dQw4w9WgXcQ',
            rating=8.8,
        )
        show = Show.objects.create(
            movie=movie,
            screen=screen,
            show_time=timezone.now() + timedelta(hours=6),
            price=220,
        )
        seat = Seat.objects.create(screen=screen, seat_number='B2')
        self.booking = Booking.objects.create(
            user=self.user,
            show=show,
            total_amount=220,
            booking_status='pending',
            payment_id='order_test_123',
        )
        self.booking.seats.add(seat)

    def _payload(self):
        return {
            'event': 'order.paid',
            'payload': {
                'order': {'entity': {'id': 'order_test_123'}},
                'payment': {'entity': {'id': 'pay_test_456'}},
            },
        }

    def test_webhook_requires_valid_signature_and_is_idempotent(self):
        payload = json.dumps(self._payload())
        signature = hmac.new(
            b'test_webhook_secret',
            payload.encode('utf-8'),
            hashlib.sha256,
        ).hexdigest()

        response = self.client.post(
            '/api/webhook/',
            data=payload,
            content_type='application/json',
            HTTP_X_RAZORPAY_SIGNATURE=signature,
        )
        self.assertEqual(response.status_code, 200)

        duplicate = self.client.post(
            '/api/webhook/',
            data=payload,
            content_type='application/json',
            HTTP_X_RAZORPAY_SIGNATURE=signature,
        )
        self.assertEqual(duplicate.status_code, 200)

        self.booking.refresh_from_db()
        self.assertEqual(self.booking.booking_status, 'confirmed')
        self.assertEqual(PaymentWebhookEvent.objects.count(), 1)
