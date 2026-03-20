from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from .models import Movie, Screen, Show, Theater
from .views import get_embed_url


class MovieCatalogTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        theater = Theater.objects.create(name='Central', location='City')
        screen = Screen.objects.create(theater=theater, screen_number=1, total_seats=50)

        self.action_en = Movie.objects.create(
            title='Alpha Mission',
            description='Action title',
            genre='Action',
            language='English',
            duration=120,
            release_date=timezone.now().date(),
            trailer_url='https://www.youtube.com/watch?v=dQw4w9WgXcQ',
            rating=9.1,
        )
        self.action_hi = Movie.objects.create(
            title='Beta Strike',
            description='Hindi action',
            genre='Action',
            language='Hindi',
            duration=110,
            release_date=timezone.now().date(),
            trailer_url='https://youtu.be/dQw4w9WgXcQ',
            rating=8.4,
        )
        self.drama_en = Movie.objects.create(
            title='Calm Story',
            description='English drama',
            genre='Drama',
            language='English',
            duration=100,
            release_date=timezone.now().date(),
            trailer_url='https://www.youtube.com/embed/dQw4w9WgXcQ',
            rating=7.9,
        )

        Show.objects.create(
            movie=self.action_en,
            screen=screen,
            show_time=timezone.now() + timedelta(days=1),
            price=250,
        )

    def test_movie_filters_keep_faceted_counts(self):
        response = self.client.get('/api/movies/', {'language': ['English']})
        self.assertEqual(response.status_code, 200)
        payload = response.json()

        self.assertEqual(payload['total_movies'], 2)
        genre_counts = {item['genre']: item['count'] for item in payload['available_filters']['genres']}
        language_counts = {item['language']: item['count'] for item in payload['available_filters']['languages']}

        self.assertEqual(genre_counts['Action'], 1)
        self.assertEqual(genre_counts['Drama'], 1)
        self.assertEqual(language_counts['English'], 2)
        self.assertEqual(language_counts['Hindi'], 1)

    def test_get_embed_url_accepts_only_safe_youtube_urls(self):
        self.assertEqual(
            get_embed_url('https://www.youtube.com/watch?v=dQw4w9WgXcQ'),
            'https://www.youtube.com/embed/dQw4w9WgXcQ?rel=0&modestbranding=1',
        )
        self.assertIsNone(get_embed_url('https://evil.example.com/watch?v=dQw4w9WgXcQ'))
