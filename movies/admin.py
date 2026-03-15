from django.contrib import admin
from .models import Movie, Theater, Screen, Show

admin.site.register(Movie)
admin.site.register(Theater)
admin.site.register(Screen)
admin.site.register(Show)