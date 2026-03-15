from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.core.paginator import Paginator
from .models import Movie
from .serializers import MovieSerializer
from django.shortcuts import render
from django.db.models import Count, Exists, OuterRef, Q
from django.utils import timezone
from .models import Movie, Show, Theater



@api_view(['GET'])
def movie_list_api(request):
    """
    TASK 1: Scalable Genre and Language Filtering.
    - Optimized for large catalogs using database indexing.
    - Dynamic counts based on filtered queryset.
    """
    genres_filter = request.GET.getlist('genre')
    languages_filter = request.GET.getlist('language')
    sort_by = request.GET.get('sort', '-rating')
    page_number = request.GET.get('page', 1)
    page_size = request.GET.get('page_size', 12)

    search_query = request.GET.get('q', '')
    queryset = Movie.objects.all().annotate(
        has_shows=Exists(Show.objects.filter(movie=OuterRef('pk'), show_time__gt=timezone.now()))
    )
    
    if search_query:
        queryset = queryset.filter(
            Q(title__icontains=search_query) | 
            Q(description__icontains=search_query)
        )
        
    if genres_filter:
        queryset = queryset.filter(genre__in=genres_filter)
    if languages_filter:
        queryset = queryset.filter(language__in=languages_filter)

    allowed_sort = ['title', '-rating', 'release_date', '-release_date', '-has_shows']
    if sort_by not in allowed_sort:
        sort_by = '-rating'
    
    # Always prioritize movies with shows, then secondary sort
    movies_ordered = queryset.order_by('-has_shows', sort_by)
    genre_counts = queryset.values('genre').annotate(count=Count('id')).order_by('-count')
    language_counts = queryset.values('language').annotate(count=Count('id')).order_by('-count')

    paginator = Paginator(movies_ordered, page_size)
    page_obj = paginator.get_page(page_number)
    serializer = MovieSerializer(page_obj, many=True)

    return Response({
        "total_movies": paginator.count,
        "total_pages": paginator.num_pages,
        "current_page": int(page_number),
        "available_filters": {
            "genres": list(genre_counts),
            "languages": list(language_counts)
        },
        "movies": serializer.data
    })

def movie_list_page(request):
    return render(request, "movie_list.html")

def home(request):
    return render(request, "home.html")

def movie_detail(request, movie_id):
    from movies.models import Show
    from django.utils import timezone
    movie = Movie.objects.get(id=movie_id)
    shows = Show.objects.filter(movie=movie, show_time__gt=timezone.now()).order_by('show_time')

    trailer_embed = get_embed_url(movie.trailer_url)

    return render(request, "movie_detail.html", {
        "movie": movie,
        "shows": shows,
        "trailer_embed": trailer_embed
    })

def get_embed_url(url):
    """
    Safely converts YouTube URLs to embed format.
    Ensures performance and security compliance.
    """
    if not url:
        return None

@api_view(['GET'])
def theater_list_api(request):
    """
    Fetches all available theaters.
    """
    theaters = Theater.objects.all()
    # Adding a mockup image for design consistency
    data = [{
        "id": t.id, 
        "name": t.name, 
        "location": t.location,
        "image": "https://images.unsplash.com/photo-1517604401157-538e9663ec1d?auto=format&fit=crop&q=80&w=800"
    } for t in theaters]
    return Response(data)

def theater_detail_page(request, theater_id):
    """
    Shows movies and showtimes for a specific theater.
    """
    theater = Theater.objects.get(id=theater_id)
    shows = Show.objects.filter(
        screen__theater=theater, 
        show_time__gt=timezone.now()
    ).select_related('movie', 'screen').order_by('show_time')
    
    # Group shows by movie for a better UI experience
    movie_shows = {}
    for show in shows:
        if show.movie.id not in movie_shows:
            movie_shows[show.movie.id] = {
                "movie": show.movie,
                "shows": []
            }
        movie_shows[show.movie.id]["shows"].append(show)
        
    return render(request, "theater_detail.html", {
        "theater": theater,
        "movie_shows": movie_shows.values()
    })
    
    video_id = None
    if "watch?v=" in url:
        video_id = url.split("watch?v=")[1].split("&")[0]
    elif "youtu.be/" in url:
        video_id = url.split("youtu.be/")[1].split("?")[0]
    elif "embed/" in url:
        video_id = url.split("embed/")[1].split("?")[0]

    if video_id:
        # Validate video_id format (alphanumeric, -, _)
        import re
        if re.match(r'^[a-zA-Z0-9_-]{11}$', video_id):
            return f"https://www.youtube.com/embed/{video_id}?rel=0&modestbranding=1"
    
    return None