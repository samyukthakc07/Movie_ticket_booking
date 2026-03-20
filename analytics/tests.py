from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from bookings.models import Booking, Seat
from movies.models import Movie, Screen, Show, Theater


class AnalyticsDashboardTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin_user = User.objects.create_user(
            username='admin',
            password='secret',
            is_staff=True,
            is_superuser=True,
        )
        regular_user = User.objects.create_user(username='viewer', password='secret')

        theater = Theater.objects.create(name='Insight Cinema', location='Center')
        screen = Screen.objects.create(theater=theater, screen_number=1, total_seats=40)
        movie = Movie.objects.create(
            title='Metrics',
            description='Analytics movie',
            genre='Drama',
            language='English',
            duration=95,
            release_date=timezone.now().date(),
            trailer_url='https://www.youtube.com/watch?v=dQw4w9WgXcQ',
            rating=8.0,
        )
        show = Show.objects.create(
            movie=movie,
            screen=screen,
            show_time=timezone.now() + timedelta(days=1),
            price=300,
        )
        seat = Seat.objects.create(screen=screen, seat_number='C3')
        booking = Booking.objects.create(
            user=regular_user,
            show=show,
            total_amount=300,
            booking_status='confirmed',
        )
        booking.seats.add(seat)

    def test_dashboard_requires_admin(self):
        response = self.client.get('/analytics-dashboard/data/')
        self.assertEqual(response.status_code, 403)

    def test_dashboard_returns_revenue_breakdown_for_admin(self):
        self.client.force_authenticate(self.admin_user)
        response = self.client.get('/analytics-dashboard/data/')
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn('revenue_breakdown', payload)
        self.assertIn('daily', payload['revenue_breakdown'])
        self.assertIn('average_occupancy', payload)
