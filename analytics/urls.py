from django.urls import path
from .views import dashboard_stats, admin_dashboard

urlpatterns = [
    path('data/', dashboard_stats),
    path('', admin_dashboard),
]