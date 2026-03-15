from django.core.management.base import BaseCommand
from movies.models import Movie
import random
from datetime import date

class Command(BaseCommand):
    help = "Generate sample movies"

    def handle(self, *args, **kwargs):

        genres = ["Action", "Comedy", "Drama", "Sci-Fi", "Romance"]
        languages = ["Tamil", "English", "Hindi"]

        for i in range(100):
            Movie.objects.create(
                title=f"Movie {i}",
                description="Sample movie description",
                genre=random.choice(genres),
                language=random.choice(languages),
                duration=random.randint(90,180),
                release_date=date(2023,1,1),
                trailer_url="https://youtube.com/watch?v=example",
                rating=random.uniform(5,9)
            )

        self.stdout.write(self.style.SUCCESS("Movies generated successfully"))