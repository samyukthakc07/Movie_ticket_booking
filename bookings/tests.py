from datetime import timedelta

from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase, override_settings
from django.utils import timezone

from movies.models import Movie, Screen, Show, Theater

from .models import Booking, Seat, SeatReservation
from .services import queue_booking_confirmation_email, release_expired_locks, send_due_email_deliveries


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

        queue_booking_confirmation_email(booking)
        result = send_due_email_deliveries()
        booking.refresh_from_db()

        self.assertEqual(result['sent'], 1)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Queue Ready', mail.outbox[0].subject)
