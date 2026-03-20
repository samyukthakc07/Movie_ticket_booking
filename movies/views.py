from urllib.parse import parse_qs, urlparse

from django.core.paginator import Paginator
from django.db.models import Count, Exists, OuterRef
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Movie, Show, Theater
from .serializers import MovieSerializer

ALLOWED_SORTS = {
    'title': 'title',
    '-rating': '-rating',
    'release_date': 'release_date',
    '-release_date': '-release_date',
}


def _base_movie_queryset(search_query):
    queryset = Movie.objects.annotate(
        has_shows=Exists(
            Show.objects.filter(movie=OuterRef('pk'), show_time__gt=timezone.now())
        )
    )

    if search_query:
        # Prefix title search preserves the index on large catalogs better than icontains.
        queryset = queryset.filter(title__istartswith=search_query.strip())

    return queryset


def _build_facets(queryset, genres_filter, languages_filter):
    genre_queryset = queryset
    if languages_filter:
        genre_queryset = genre_queryset.filter(language__in=languages_filter)

    language_queryset = queryset
    if genres_filter:
        language_queryset = language_queryset.filter(genre__in=genres_filter)

    genre_counts = genre_queryset.values('genre').annotate(count=Count('id')).order_by('-count', 'genre')
    language_counts = language_queryset.values('language').annotate(count=Count('id')).order_by('-count', 'language')
    return genre_counts, language_counts


@api_view(['GET'])
def movie_list_api(request):
    """
    Scalable server-side filtering with faceted counts and indexed sorting.
    """
    genres_filter = sorted(set(request.GET.getlist('genre')))
    languages_filter = sorted(set(request.GET.getlist('language')))
    sort_by = ALLOWED_SORTS.get(request.GET.get('sort', '-rating'), '-rating')
    search_query = request.GET.get('q', '')

    try:
        page_number = max(int(request.GET.get('page', 1)), 1)
    except (TypeError, ValueError):
        page_number = 1

    try:
        page_size = min(max(int(request.GET.get('page_size', 12)), 1), 48)
    except (TypeError, ValueError):
        page_size = 12

    base_queryset = _base_movie_queryset(search_query)
    filtered_queryset = base_queryset

    if genres_filter:
        filtered_queryset = filtered_queryset.filter(genre__in=genres_filter)
    if languages_filter:
        filtered_queryset = filtered_queryset.filter(language__in=languages_filter)

    movies_ordered = filtered_queryset.order_by('-has_shows', sort_by, 'id')
    genre_counts, language_counts = _build_facets(base_queryset, genres_filter, languages_filter)

    paginator = Paginator(movies_ordered, page_size)
    page_obj = paginator.get_page(page_number)

    return Response({
        "total_movies": paginator.count,
        "total_pages": paginator.num_pages,
        "current_page": page_obj.number,
        "available_filters": {
            "genres": list(genre_counts),
            "languages": list(language_counts),
        },
        "movies": MovieSerializer(page_obj, many=True).data,
    })


def movie_list_page(request):
    return render(request, "movie_list.html")


def home(request):
    return render(request, "home.html")


def movie_detail(request, movie_id):
    movie = get_object_or_404(Movie, id=movie_id)
    shows = Show.objects.filter(
        movie=movie,
        show_time__gt=timezone.now(),
    ).select_related('screen__theater').order_by('show_time')

    return render(request, "movie_detail.html", {
        "movie": movie,
        "shows": shows,
        "trailer_embed": get_embed_url(movie.trailer_url),
    })


def get_embed_url(url):
    """
    Convert only valid YouTube URLs into a safe embed URL.
    """
    if not url:
        return None

    parsed = urlparse(url)
    host = parsed.netloc.lower().replace('www.', '')
    video_id = None

    if host in {'youtube.com', 'm.youtube.com'}:
        if parsed.path == '/watch':
            video_id = parse_qs(parsed.query).get('v', [None])[0]
        elif parsed.path.startswith('/embed/'):
            video_id = parsed.path.split('/embed/', 1)[1].split('/')[0]
        elif parsed.path.startswith('/shorts/'):
            video_id = parsed.path.split('/shorts/', 1)[1].split('/')[0]
    elif host == 'youtu.be':
        video_id = parsed.path.strip('/').split('/')[0]

    if not video_id:
        return None

    allowed_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-")
    if len(video_id) != 11 or any(char not in allowed_chars for char in video_id):
        return None

    return f"https://www.youtube.com/embed/{video_id}?rel=0&modestbranding=1"


@api_view(['GET'])
def theater_list_api(request):
    theaters = Theater.objects.all()
    data = [{
        "id": theater.id,
        "name": theater.name,
        "location": theater.location,
        "image": "https://images.unsplash.com/photo-1517604401157-538e9663ec1d?auto=format&fit=crop&q=80&w=800",
    } for theater in theaters]
    return Response(data)


def theater_detail_page(request, theater_id):
    theater = get_object_or_404(Theater, id=theater_id)
    shows = Show.objects.filter(
        screen__theater=theater,
        show_time__gt=timezone.now(),
    ).select_related('movie', 'screen').order_by('show_time')

    movie_shows = {}
    for show in shows:
        if show.movie_id not in movie_shows:
            movie_shows[show.movie_id] = {"movie": show.movie, "shows": []}
        movie_shows[show.movie_id]["shows"].append(show)

    return render(request, "theater_detail.html", {
        "theater": theater,
        "movie_shows": movie_shows.values(),
    })
