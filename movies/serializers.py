from rest_framework import serializers
from .models import Movie

class MovieSerializer(serializers.ModelSerializer):
    has_shows = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Movie
        fields = ['id', 'title', 'genre', 'language', 'duration', 'rating', 'poster_url', 'release_date', 'has_shows']