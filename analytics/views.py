from django.shortcuts import render
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from django.db.models import Sum, Count, Q
from django.db.models.functions import ExtractHour
from django.core.cache import cache
from bookings.models import Booking
from movies.models import Movie, Theater

@api_view(['GET'])
@permission_classes([IsAdminUser])
def dashboard_stats(request):
    """
    Consolidated dashboard stats with caching.
    Optimized for large datasets using database-level aggregation.
    """
    stats = cache.get('admin_dashboard_stats')
    if stats:
        return Response(stats)

    # 1. Revenue Stats
    revenue = Booking.objects.filter(booking_status="confirmed").aggregate(
        total=Sum("total_amount")
    )

    # 2. Movie Popularity
    popular_movies = Movie.objects.annotate(
        bookings_count=Count('show__booking', filter=Q(show__booking__booking_status='confirmed'))
    ).order_by('-bookings_count')[:10]

    # 3. Peak Booking Hours
    peak_hours = Booking.objects.annotate(
        hour=ExtractHour('created_at')
    ).values('hour').annotate(
        total=Count('id')
    ).order_by('-total')

    # 4. Cancellation Rates
    total_bookings = Booking.objects.count()
    cancelled_bookings = Booking.objects.filter(booking_status='cancelled').count()
    cancellation_rate = (cancelled_bookings / total_bookings * 100) if total_bookings > 0 else 0

    # 5. Theatre Occupancy
    theatres = Theater.objects.annotate(
        occupancy=Count('screen__show__booking', filter=Q(screen__show__booking__booking_status='confirmed'))
    ).order_by('-occupancy')

    stats = {
        "total_revenue": revenue["total"] or 0,
        "popular_movies": [{"movie": m.title, "count": m.bookings_count} for m in popular_movies],
        "peak_hours": list(peak_hours),
        "cancellation_rate": round(cancellation_rate, 2),
        "theatre_performance": [{"theatre": t.name, "bookings": t.occupancy} for t in theatres]
    }

    cache.set('admin_dashboard_stats', stats, 600)
    return Response(stats)

def admin_dashboard(request):
    """
    Renders the HTML admin dashboard.
    """
    from django.contrib.admin.views.decorators import staff_member_required
    @staff_member_required
    def inner(req):
        return render(req, 'admin_dashboard.html')
    return inner(request)