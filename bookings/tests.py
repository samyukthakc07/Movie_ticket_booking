from datetime import timedelta
import json
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from movies.models import Movie, Screen, Show, Theater

from .models import Booking, Seat, SeatReservation
from .services import queue_booking_confirmation_email, release_expired_locks


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class BookingServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='alice', password='secret', email='alice@example.com')
        theater = Theater.objects.create(name='Cinema One', location='Downtown')
        screen = Screen.objects.create(theater=theater, screen_number=1, total_seats=20)
        self.movie = Movie.objects.create(
            title='Queue Ready',
            description='Test movie',
            genre='Drama',
            language='English',
            duration=90,
            release_date=timezone.now().date(),
            trailer_url='https://www.youtube.com/watch?v=dQw4w9WgXcQ',
            rating=8.1,
        )
        self.show = Show.objects.create(
            movie=self.movie,
            screen=screen,
            show_time=timezone.now() + timedelta(hours=4),
            price=150,
        )
        self.seat = Seat.objects.create(screen=screen, seat_number='A1')

    def test_release_expired_locks_marks_rows_expired(self):
        reservation = SeatReservation.objects.create(
            seat=self.seat,
            show=self.show,
            user=self.user,
            status='locked',
            locked_until=timezone.now() - timedelta(minutes=1),
        )

        release_expired_locks()
        reservation.refresh_from_db()
        self.assertEqual(reservation.status, 'expired')

    def test_email_queue_sends_confirmation(self):
        booking = Booking.objects.create(
            user=self.user,
            show=self.show,
            total_amount=150,
            booking_status='confirmed',
            payment_id='order_123',
        )
        booking.seats.add(self.seat)

        with patch('bookings.services.threading.Thread') as mocked_thread:
            delivery = queue_booking_confirmation_email(booking)

        mocked_thread.assert_not_called()
        delivery.refresh_from_db()
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(delivery.status, 'sent')
        self.assertIn('Queue Ready', mail.outbox[0].subject)


class BookingGuestFlowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='bob', password='secret', email='bob@example.com')
        theater = Theater.objects.create(name='Cinema Two', location='Midtown')
        screen = Screen.objects.create(theater=theater, screen_number=2, total_seats=20)
        movie = Movie.objects.create(
            title='Auth Check',
            description='Auth flow test movie',
            genre='Thriller',
            language='English',
            duration=110,
            release_date=timezone.now().date(),
            trailer_url='https://www.youtube.com/watch?v=dQw4w9WgXcQ',
            rating=7.4,
        )
        self.show = Show.objects.create(
            movie=movie,
            screen=screen,
            show_time=timezone.now() + timedelta(hours=6),
            price=200,
        )
        self.seat = Seat.objects.create(screen=screen, seat_number='B1')

    def test_guest_reserve_seat_api_requires_sign_in(self):
        response = self.client.post(
            '/api/reserve-seat/',
            data=json.dumps({
                'seat_id': self.seat.id,
                'show_id': self.show.id,
                'user_id': self.user.id,
            }),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()['status'], 'auth_required')
        self.assertFalse(SeatReservation.objects.exists())

    def test_guest_create_booking_api_requires_sign_in(self):
        response = self.client.post(
            '/api/create-booking/',
            data=json.dumps({
                'show_id': self.show.id,
                'seat_ids': [self.seat.id],
                'user_id': self.user.id,
            }),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()['status'], 'auth_required')
        self.assertFalse(Booking.objects.exists())

    def test_guest_seat_selection_page_prompts_sign_in_on_continue(self):
        response = self.client.get(f'/seats/?show_id={self.show.id}')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Sign in is required before we hold seats.')
        self.assertContains(response, 'Pick your seats first. When you continue,')
        self.assertContains(response, 'place those seats into My Bookings for confirmation.')
        self.assertContains(response, 'Sign In to Reserve')

    def test_login_with_booking_request_creates_pending_booking_and_redirects_to_my_bookings(self):
        response = self.client.post(
            reverse('login'),
            data={
                'username': 'bob',
                'password': 'secret',
                'booking_required': '1',
                'show_id': str(self.show.id),
                'seat_ids': str(self.seat.id),
                'next': f'/seats/?show_id={self.show.id}',
            },
            follow=False,
        )

        self.assertRedirects(response, reverse('my_bookings'), fetch_redirect_response=False)

        booking = Booking.objects.get(user=self.user, booking_status='pending')
        self.assertEqual(list(booking.seats.values_list('id', flat=True)), [self.seat.id])

        reservation = SeatReservation.objects.get(user=self.user, show=self.show, seat=self.seat)
        self.assertEqual(reservation.status, 'locked')
