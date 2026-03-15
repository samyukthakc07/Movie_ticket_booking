from django.db import models


class Movie(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    genre = models.CharField(max_length=100, db_index=True)
    language = models.CharField(max_length=50, db_index=True)
    duration = models.IntegerField(help_text="Duration in minutes")
    release_date = models.DateField(db_index=True)
    trailer_url = models.URLField()
    poster_url = models.URLField(blank=True, null=True)
    rating = models.FloatField(default=0, db_index=True)

    def __str__(self):
        return self.title


class Theater(models.Model):
    name = models.CharField(max_length=200)
    location = models.CharField(max_length=200)

    def __str__(self):
        return self.name


class Screen(models.Model):
    theater = models.ForeignKey(Theater, on_delete=models.CASCADE)
    screen_number = models.IntegerField()
    total_seats = models.IntegerField()

    def __str__(self):
        return f"{self.theater.name} - Screen {self.screen_number}"


class Show(models.Model):
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE)
    screen = models.ForeignKey(Screen, on_delete=models.CASCADE)
    show_time = models.DateTimeField(db_index=True)
    price = models.DecimalField(max_digits=6, decimal_places=2)

    class Meta:
        indexes = [
            models.Index(fields=['movie', 'show_time']),
        ]

    def __str__(self):
        return f"{self.movie.title} - {self.show_time}"