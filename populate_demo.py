import os
import django
import random
from datetime import datetime, timedelta
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'movie_booking_system.settings')
django.setup()

from movies.models import Movie, Theater, Screen, Show
from bookings.models import Seat

def populate():
    print("Starting demo data population...")
    
    # Create initial movies if none exist
    if not Movie.objects.exists():
        print("Creating sample movies...")
        sample_movies = [
            {
                "title": "Interstellar",
                "genre": "Sci-Fi",
                "language": "English",
                "duration": 169,
                "rating": 8.6,
                "release_date": "2014-11-07",
                "description": "A team of explorers travel through a wormhole in space in an attempt to ensure humanity's survival.",
                "poster_url": "https://images.unsplash.com/photo-1446776811953-b23d57bd21aa?auto=format&fit=crop&q=80&w=1000",
                "trailer_url": "https://www.youtube.com/watch?v=zSWdZVtXT7E"
            },
            {
                "title": "The Dark Knight",
                "genre": "Action",
                "language": "English",
                "duration": 152,
                "rating": 9.0,
                "release_date": "2008-07-18",
                "description": "When the menace known as the Joker wreaks havoc and chaos on the people of Gotham.",
                "poster_url": "https://images.unsplash.com/photo-1478720568477-152d9b164e26?auto=format&fit=crop&q=80&w=1000",
                "trailer_url": "https://www.youtube.com/watch?v=EXeTwQWrcwY"
            },
            {
                "title": "Parasite",
                "genre": "Drama",
                "language": "Korean",
                "duration": 132,
                "rating": 8.5,
                "release_date": "2019-05-30",
                "description": "Greed and class discrimination threaten the newly formed symbiotic relationship between the wealthy Park family and the destitute Kim clan.",
                "poster_url": "https://images.unsplash.com/photo-1536440136628-849c177e76a1?auto=format&fit=crop&q=80&w=1000",
                "trailer_url": "https://www.youtube.com/watch?v=5xH0HfJHsaY"
            }
        ]
        for m_data in sample_movies:
            Movie.objects.create(**m_data)

    movies = Movie.objects.all()

    # Create Theaters
    theaters_data = [
        {"name": "Starlight Cinema", "location": "Downtown Metro"},
        {"name": "Grand Premiere", "location": "Silicon Valley"},
        {"name": "The Royal Playhouse", "location": "Old Town"},
        {"name": "Midnight Screenings", "location": "North Port"}
    ]
    
    for t_data in theaters_data:
        theater, created = Theater.objects.get_or_create(name=t_data["name"], defaults={"location": t_data["location"]})
        if created:
            print(f"Created Theater: {theater.name}")
            # Create Screens for each theater
            for i in range(1, 3):
                screen = Screen.objects.create(theater=theater, screen_number=i, total_seats=100)
                print(f"  Created Screen {i} for {theater.name}")
                # Create Seats for screen
                seats = []
                for row in ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J']:
                    for num in range(1, 11):
                        seats.append(Seat(screen=screen, seat_number=f"{row}{num}"))
                Seat.objects.bulk_create(seats)
                print(f"    Created 100 seats for Screen {i}")

    # Create Shows for next 3 days
    all_screens = Screen.objects.all()
    if not all_screens.exists():
        print("No screens found!")
        return

    for screen in all_screens:
        # Create 3 shows per screen per day
        for day in range(3):
            base_time = timezone.now() + timedelta(days=day)
            times = [
                base_time.replace(hour=14, minute=0, second=0, microsecond=0),
                base_time.replace(hour=18, minute=30, second=0, microsecond=0),
                base_time.replace(hour=21, minute=45, second=0, microsecond=0),
            ]
            for t in times:
                movie = random.choice(movies)
                Show.objects.get_or_create(
                    movie=movie,
                    screen=screen,
                    show_time=t,
                    defaults={'price': random.choice([12.00, 15.00, 18.00])}
                )
    
    print("Demo data population complete!")

if __name__ == "__main__":
    populate()
