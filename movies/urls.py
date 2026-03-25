from django.urls import path
from .views import movie_list_api, movie_list_page, movie_detail, theater_list_api, theater_detail_page, debug_populate

urlpatterns = [
    path('movies/', movie_list_api),
    path('explore/', movie_list_page, name='movie_list'),
    path('movie/<int:movie_id>/', movie_detail),
    path('theaters/', theater_list_api),
    path('theater/<int:theater_id>/', theater_detail_page),
    path('debug-populate/', debug_populate),
]